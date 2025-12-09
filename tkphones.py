# phone_finder.py
import streamlit as st, requests, json, urllib.parse, time, random, bs4
from groq import Groq
from requests.exceptions import RequestException, Timeout, JSONDecodeError

# ---------- CONFIG ----------
st.set_page_config(page_title="Phone + Social Pack (KE)", layout="wide")
if "groq_key" not in st.secrets:
    st.error("Missing groq_key in .streamlit/secrets.toml"); st.stop()
client = Groq(api_key=st.secrets["groq_key"])

SEARX   = "https://searxng-587s.onrender.com/search"
TIMEOUT = 25               # SearXNG cold-start tolerant
RATE_LIMIT = 5             # seconds between SearXNG calls
LAST_SEARX = 0             # epoch tracker

# ---------- UTILS ----------
def rate_limit():
    global LAST_SEARX
    elapsed = time.time() - LAST_SEARX
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    LAST_SEARX = time.time()

def ping_searx():
    """Wake SearXNG on first load so user doesn't wait."""
    try:
        requests.get(SEARX, params={"q": "ping", "format": "json"}, timeout=10)
    except Exception:
        pass

# ---------- IMAGE SOURCES (no API key) ----------
@st.cache_data(show_spinner=False)
def phone_images(phone: str, qty=9) -> list[str]:
    kw = phone.replace(" ", ",").lower()
    # 1. Unsplash source (random)
    unsplash = f"https://source.unsplash.com/600x400/?{kw},smartphone"
    # 2. Pexels HTML scrape (top result)
    try:
        pexels_q = phone.replace(" ", "-").lower()
        url = f"https://www.pexels.com/search/{pexels_q}/"
        hdr = {"User-Agent": "Mozilla/5.0"}
        soup = bs4.BeautifulSoup(requests.get(url, headers=hdr, timeout=10).text, "html.parser")
        img_tag = soup.find("img", {"src": True})
        pexels_img = img_tag["src"] if img_tag else None
    except Exception:
        pexels_img = None
    # assemble list
    images = [unsplash] * 3          # at least Unsplash duplicates
    if pexels_img:
        images[0] = pexels_img
    random.shuffle(images)
    return images[:qty]

# ---------- GROQ ----------
DEFAULT_MODEL = "llama3-70b-8192"

@st.cache_data(show_spinner=False)
def correct_name(fuzzy: str) -> str:
    prompt = f'Correct the smartphone name to its official commercial title (max 4 words). Reply name only.\nInput: "{fuzzy}"'
    try:
        out = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=TIMEOUT
        )
        return out.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Groq name-correction failed: {e}")
        return fuzzy  # fallback

def groq_pack(corrected: str, search_json: dict) -> dict:
    snippet = json.dumps(search_json.get("results", [])[:12], indent=2)
    prompt = f"""You are a social-media & marketing assistant.
Phone: {corrected}

SEARCH RESULTS (specs + Kenya prices):
{snippet}

Return ONLY valid JSON with these keys:
- specs: string (concise bullet specs, max 8 lines)
- price_range: string (e.g. "KES 65 000 – 75 000")
- urls: list of 3 {"title": "...", "url": "...", "site": "..."} objects
- tweet: string (max 280 chars)
- ig_caption: string (max 150 chars, emoji allowed)
- hashtags: string (5 hashtags, space-separated)
- ad_copy: string (short headline for ad, max 8 words)
- banner_ideas: string (2 short creative lines for a poster/banner)
"""
    try:
        out = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=TIMEOUT
        )
        return json.loads(out.choices[0].message.content.strip())
    except JSONDecodeError:
        st.error("Groq returned invalid JSON; using fallback.")
        return {"specs": "n/a", "price_range": "n/a", "urls": [], "tweet": "n/a",
                "ig_caption": "n/a", "hashtags": "#n/a", "ad_copy": "n/a", "banner_ideas": "n/a"}

# ---------- SEARXNG ----------
def searx_json(query: str, category: str = "general") -> dict:
    rate_limit()
    params = {"q": query, f"category_{category}": "1", "language": "auto",
              "safesearch": "0", "format": "json"}
    try:
        r = requests.get(SEARX, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Timeout:
        st.error("SearXNG is too slow (cold-start). Please retry in ~20 s.")
        return {"results": []}
    except RequestException as e:
        st.error(f"SearXNG error: {e}")
        return {"results": []}

# ---------- UI ----------
def main():
    st.title("📱 Phone + Social Pack (Kenya)")
    fuzzy = st.text_input("Phone name (fuzzy):", placeholder="iPhone 17")

    if st.button("Generate") and fuzzy.strip():
        # progress indicators
        with st.spinner("Waking SearXNG…"):
            ping_searx()
        with st.spinner("Correcting name…"):
            corrected = correct_name(fuzzy)
        with st.spinner("Searching specs & prices…"):
            search_data = searx_json(f"{corrected} specs price Kenya")
        with st.spinner("Creating social pack…"):
            pack = groq_pack(corrected, search_data)
        with st.spinner("Grabbing images…"):
            images = phone_images(corrected)

        # display
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### Images")
            if images:
                st.image(images, width=180)
            else:
                st.info("No images found")

        with col2:
            st.markdown(f"### {corrected}")
            with st.expander("🔍  Key specs"):
                st.markdown(pack["specs"])
            with st.expander("💰  Kenyan prices"):
                st.markdown(f"**Range:** {pack['price_range']}")
                for u in pack["urls"]:
                    st.markdown(f"- **[{u['site']}]({u['url']})** – {u['title']}")
            with st.expander("📣  Social / Ad pack"):
                c1, c2, c3 = st.columns(3)
                c1.markdown("**Tweet**") ; c1.write(pack["tweet"])
                c2.markdown("**IG caption**") ; c2.write(pack["ig_caption"])
                c3.markdown("**Ad headline**") ; c3.write(pack["ad_copy"])
                st.markdown("**Hashtags:** " + pack["hashtags"])
                st.markdown("**Banner ideas:** " + pack["banner_ideas"])

    else:
        st.info("Enter a phone name and hit Generate.")

# ---------- boot ----------
if __name__ == "__main__":
    main()
