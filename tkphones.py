#!/usr/bin/env python3
import streamlit as st, requests, json, time, urllib.parse, re
from groq import Groq
from bs4 import BeautifulSoup

############################  CONFIG  ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("Add groq_key to .streamlit/secrets.toml"); st.stop()
client = Groq(api_key=GROQ_KEY, timeout=30)
SEARX_URL = "https://searxng-587s.onrender.com/search"
RATE_LIMIT = 3
LAST = 0
MODEL = "llama-3.1-8b-instant"
#####################################################################


# ---------- POLITE SEARX ----------
def searx_raw(phone: str, pages: int = 2) -> list:
    global LAST
    elapsed = time.time() - LAST
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    LAST = time.time()
    out = []
    for p in range(1, pages + 1):
        r = requests.get(
            SEARX_URL,
            params={"q": phone, "category_general": "1", "language": "auto",
                    "safesearch": "0", "format": "json", "pageno": p},
            timeout=25,
        )
        out.extend(r.json().get("results", []))
    return out


# ---------- GSMARENA ----------
def gsm_specs(phone: str) -> dict:
    try:
        search = f"https://www.gsmarena.com/res.php3?sSearchWord={urllib.parse.quote(phone)}"
        soup = BeautifulSoup(requests.get(search, timeout=15).text, "html.parser")
        link = soup.select_one("div.makers a")
        if not link:
            return {}
        device = urllib.parse.urljoin("https://www.gsmarena.com/", link["href"])
        soup2 = BeautifulSoup(requests.get(device, timeout=15).text, "html.parser")
        return {tr.find_all("td")[0].get_text(strip=True): tr.find_all("td")[1].get_text(strip=True)
                for tr in soup2.select("table.specs tr") if len(tr.find_all("td")) == 2}
    except Exception:
        return {}


# ---------- AI AD PACK ----------
def groq_pack(phone: str, raw_json: list, persona: str, tone: str) -> list:
    hashtag_text = " ".join([r.get("title", "") + " " + r.get("content", "") for r in raw_json])
    prompt = f"""You are a Kenyan phone-marketing AI.
Phone: {phone}
Persona: {persona}
Tone: {tone}
Raw text: {hashtag_text}

Return ONLY valid JSON list with 3 variants. Each variant has:
- specs: string (one spec per line, max 6 lines)
- price_range: string (e.g. "KES 65 000 – 75 000")
- urls: list of 3 {"title": "...", "url": "...", "site": "..."} objects
- tweet: string (max 280 chars)
- ig_caption: string (max 150 chars, emoji allowed)
- hashtags: string (10 hashtags, space-separated)
- ad_copy: string (max 8 words)
- banner_ideas: string (2 short lines for poster/banner)
"""
    try:
        out = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.4, timeout=30
        )
        return json.loads(out.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []


############################  UI  ####################################
st.set_page_config(page_title="Phone Ad Cards", layout="wide")
st.title("📱 Phone Ad Cards – Search → Specs → AI Copy")

# ---------- SEARCH BOX ----------
phone = st.text_input("Search phone / keywords", value="samsung a17 price kenya")
if st.button("Generate cards"):
    with st.spinner("Scraping + AI crafting…"):
        raw = searx_raw(phone)
        specs = gsm_specs(phone)
        variants = groq_pack(phone, raw, persona="Budget students", tone="Playful")

    # ---------- GSMARENA CARD ----------
    if specs:
        with st.expander("🔍 GSMArena specs (one per line)"):
            for k, v in list(specs.items())[:6]:
                st.markdown(f"- **{k}**: {v}")

    # ---------- AD CARDS ----------
    if variants:
        st.subheader("AI Ad Variants")
        for idx, v in enumerate(variants):
            with st.container(border=True):
                st.markdown(f"### Variant {idx+1}")
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown("**Specs**")
                    st.text(v.get("specs", "n/a"))
                    st.markdown(f"**Price band**: {v.get('price_range','?')}")
                    st.markdown(f"**Ad headline**: {v.get('ad_copy','?')}")
                    st.markdown(f"**Banner ideas**: {v.get('banner_ideas','?')}")
                with c2:
                    st.markdown("**Tweet**")
                    st.text(v.get("tweet", "n/a"))
                    st.markdown("**IG caption**")
                    st.text(v.get("ig_caption", "n/a"))
                    st.markdown("**Hashtags**")
                    st.text(v.get("hashtags", "#n/a"))
                    if v.get("urls"):
                        st.markdown("**Sample URLs**")
                        for u in v["urls"]:
                            st.markdown(f"- [{u['site']}]({u['url']}) – {u['title']}")

    else:
        st.info("No AI variants returned – try again.")
