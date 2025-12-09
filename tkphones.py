# phone_finder.py
import streamlit as st, requests, json, urllib.parse, time, random, bs4, re
from groq import Groq
from requests.exceptions import RequestException, Timeout, JSONDecodeError

# ---------- CONFIG ----------
st.set_page_config(page_title="Phone Marketer Suite", layout="wide")
if "groq_key" not in st.secrets:
    st.error("Missing groq_key in .streamlit/secrets.toml"); st.stop()
client = Groq(api_key=st.secrets["groq_key"])

SEARX   = "https://searxng-587s.onrender.com/search"
TIMEOUT = 25
RATE_LIMIT = 5
LAST_SEARX = 0
MODEL = "llama-3.1-8b-instant"   # ← new model

# ---------- UTILS ----------
def rate_limit():
    global LAST_SEARX
    elapsed = time.time() - LAST_SEARX
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    LAST_SEARX = time.time()

def ping_searx():
    try:
        requests.get(SEARX, params={"q": "ping", "format": "json"}, timeout=10)
    except Exception:
        pass

# ---------- GSM ARENA ----------
@st.cache_data(show_spinner=False)
def gsmarena_specs(phone: str) -> dict:
    try:
        search_url = f"https://www.gsmarena.com/res.php3?sSearchWord={urllib.parse.quote(phone)}"
        r = requests.get(search_url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        link_tag = soup.select_one("div.makers a")
        if not link_tag:
            return {}
        device_url = urllib.parse.urljoin("https://www.gsmarena.com/", link_tag["href"])
        r2 = requests.get(device_url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        soup2 = bs4.BeautifulSoup(r2.text, "html.parser")
        specs = {}
        for tr in soup2.select("table.specs tr"):
            td = tr.find_all("td")
            if len(td) == 2:
                specs[td[0].get_text(strip=True)] = td[1].get_text(strip=True)
        return specs
    except Exception:
        return {}

# ---------- DEVICE SPECS JSON ----------
@st.cache_data(show_spinner=False)
def devicespecs_json(phone: str) -> dict:
    try:
        search_url = f"https://www.devicespecifications.com/en/model-search/{urllib.parse.quote(phone)}"
        soup = bs4.BeautifulSoup(requests.get(search_url, timeout=TIMEOUT).text, "html.parser")
        link = soup.select_one("table.model-list a")
        if not link:
            return {}
        slug = link["href"].split("/")[-1]
        json_url = f"https://www.devicespecifications.com/en/model/{slug}?format=json"
        return requests.get(json_url, timeout=TIMEOUT).json()
    except Exception:
        return {}

# ---------- IMAGES ----------
@st.cache_data(show_spinner=False)
def phone_images(phone: str, qty=9) -> list[str]:
    kw = phone.replace(" ", ",").lower()
    images = [f"https://source.unsplash.com/600x400/?{kw},smartphone" for _ in range(qty)]
    try:
        pexels_q = phone.replace(" ", "-").lower()
        url = f"https://www.pexels.com/search/{pexels_q}/"
        soup = bs4.BeautifulSoup(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text, "html.parser")
        img_tag = soup.find("img", {"src": True})
        if img_tag:
            images[0] = img_tag["src"]
    except Exception:
        pass
    random.shuffle(images)
    return images[:qty]

# ---------- GROQ ----------
def correct_name(phone: str) -> str:
    prompt = f'Correct the smartphone name to its official commercial title (max 4 words). Reply name only.\nInput: "{phone}"'
    try:
        out = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0, timeout=TIMEOUT
        )
        return out.choices[0].message.content.strip()
    except Exception:
        return phone  # fallback

def groq_pack(corrected: str, search_json: dict, persona: str, tone: str) -> list:
    hashtag_text = " ".join([r.get("title", "") + " " + r.get("content", "") for r in search_json.get("results", [])])
    prompt = f"""You are a social-media & marketing assistant.
Phone: {corrected}
Persona: {persona}
Tone: {tone}
Hashtag source text: {hashtag_text}

Return ONLY valid JSON list with 3 variants. Each variant has:
- specs: string (concise bullet specs, max 6 lines)
- price_range: string (e.g. "Ksh 65,000 75,000)
- site name from urls in json
- urls: urls from json that lead to the site
- tweet: string (max 280 chars)
- ig_caption: string (max 150 chars, emoji allowed)
- hashtags: string (10 hashtags extracted from the hashtag source text above, space-separated)
- ad_copy: string (short headline for ad, max 8 words)
- banner_ideas: string (2 short creative lines for a poster/banner)
"""
    try:
        out = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.4, timeout=TIMEOUT
        )
        return json.loads(out.choices[0].message.content.strip())
    except Exception:
        return [{}]

# ---------- SEARX ----------
def searx_json(query: str) -> dict:
    rate_limit()
    params = {"q": query, "category_general": "1", "language": "auto",
              "safesearch": "0", "format": "json"}
    try:
        r = requests.get(SEARX, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Timeout:
        st.error("SearXNG timeout (cold-start). Retry in 20 s.")
        return {"results": []}
    except RequestException as e:
        st.error(f"SearXNG error: {e}")
        return {"results": []}

# ---------- UI ----------
def main():
    st.title("📱 Phone Marketer Suite (Kenya)")

    # default phone
    if "phone_default" not in st.session_state:
        st.session_state.phone_default = "Samsung s25 fe"
    fuzzy = st.text_input("Phone name (fuzzy):", value=st.session_state.phone_default)

    persona = st.selectbox("Buyer persona", ["Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
    tone   = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])
    use_searx = st.checkbox("Use SearXNG (slow cold-start)", value=False)

    if st.button("Generate"):
        corrected = correct_name(fuzzy)
        # always scrape static sources
        with st.spinner("Scraping GSMArena…"):
            gsm = gsmarena_specs(corrected)
        with st.spinner("Grabbing DeviceSpecifications JSON…"):
            ds = devicespecs_json(corrected)
        # SearXNG only if user opted-in
        if use_searx:
            with st.spinner("Warming SearXNG…"):
                ping_searx()
            with st.spinner("Searching specs & prices…"):
                search_data = searx_json(f"{corrected} specs price Kenya")
        else:
            search_data = {"results": []}
        with st.spinner("Creating 3 variants…"):
            variants = groq_pack(corrected, search_data, persona, tone)
        with st.spinner("Collecting images…"):
            images = phone_images(corrected)

        # display
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### Images")
            if images:
                st.image(images, width=180)
            else:
                st.info("No images")

        with col2:
            st.markdown(f"### {corrected}")
            if gsm:
                with st.expander("🔍  GSMArena specs"):
                    for k, v in list(gsm.items())[:10]:
                        st.markdown(f"- **{k}**: {v}")
            if ds:
                with st.expander("🔍  DeviceSpecifications JSON"):
                    st.json(ds)
            if use_searx and search_data["results"]:
                with st.expander("💰  Kenyan prices (SearXNG)"):
                    for hit in search_data["results"][:5]:
                        title = hit.get("title", "No title")
                        url   = hit.get("url", "")
                        site  = urllib.parse.urlparse(url).netloc or "Unknown"
                        st.markdown(f"- **[{site}]({url})** – {title}")

            # variants
            for idx, v in enumerate(variants):
                with st.expander(f"🎨  Variant {idx+1}  ({persona} · {tone})"):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown("**Tweet**") ; c1.write(v.get("tweet", "n/a"))
                    c2.markdown("**IG caption**") ; c2.write(v.get("ig_caption", "n/a"))
                    c3.markdown("**Ad headline**") ; c3.write(v.get("ad_copy", "n/a"))
                    st.markdown("**Hashtags:** " + v.get("hashtags", "#n/a"))
                    st.markdown("**Banner ideas:** " + v.get("banner_ideas", "n/a"))

    else:
        st.info("Fill fields and hit Generate.")

# ---------- boot ----------
if __name__ == "__main__":
    main()