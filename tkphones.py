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
def gsm_specs(phone: str) -> list[str]:
    try:
        search = f"https://www.gsmarena.com/res.php3?sSearchWord={urllib.parse.quote(phone)}"
        soup = BeautifulSoup(requests.get(search, timeout=15).text, "html.parser")
        link = soup.select_one("div.makers a")
        if not link:
            return []
        device = urllib.parse.urljoin("https://www.gsmarena.com/", link["href"])
        soup2 = BeautifulSoup(requests.get(device, timeout=15).text, "html.parser")
        return [f"{tr.find_all('td')[0].get_text(strip=True)}: {tr.find_all('td')[1].get_text(strip=True)}"
                for tr in soup2.select("table.specs tr") if len(tr.find_all("td")) == 2][:8]  # max 8 lines
    except Exception:
        return []


# ---------- AI AD PACK (plain text) ----------
def ai_pack(phone: str, raw_json: list, persona: str, tone: str) -> list[dict]:
    hashtag_text = " ".join([r.get("title", "") + " " + r.get("content", "") for r in raw_json])
    prompt = f"""Kenyan phone-marketing assistant.
Phone: {phone}
Persona: {persona}
Tone: {tone}
Raw text: {hashtag_text}

Return ONLY plain text (no JSON/objects) with exactly 3 blocks separated by "-----".

Each block contains:
1. One spec per line (max 6 lines)
2. "WEBSITES:" followed by 3 lines: "site - price - url" (use real URLs from raw text)
3. "BANNERS:" 2 full poster lines
4. "SOCIAL:" 3 ready-to-post texts (Tweet, IG, FB) each on its own line
10 relevant hashtags at the end (space-separated)

Example block layout:
spec line 1
spec line 2
WEBSITES:
jumia.co.ke - KSh 65,000 - https://...
kilimall.co.ke - KSh 67,500 - https://...
safaricom.co.ke - KSh 69,900 - https://...
BANNERS:
Line 1 poster text
Line 2 poster text
SOCIAL:
Tweet text under 280 chars
IG caption under 150 chars emoji OK
FB post text under 300 chars
#hashtag1 #hashtag2 ... #hashtag10
-----
<next block>
-----
<next block>
"""
    try:
        out = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.4, timeout=30
        )
        raw = out.choices[0].message.content.strip()
        blocks = [b.strip() for b in raw.split("-----") if b.strip()]
        variants = []
        for blk in blocks[:3]:  # max 3
            lines = [l.strip() for l in blk.splitlines() if l.strip()]
            # quick parse
            websites = [l.replace("WEBSITES:", "").strip() for l in lines if l.startswith("WEBSITES:")]
            banners  = [l.replace("BANNERS:", "").strip() for l in lines if l.startswith("BANNERS:")]
            social   = [l.replace("SOCIAL:", "").strip() for l in lines if l.startswith("SOCIAL:")]
            hashtags = [l for l in lines if l.startswith("#")][0] if any(l.startswith("#") for l in lines) else "#phone"
            variants.append({
                "specs": "\n".join([l for l in lines if not l.startswith(("WEBSITES:", "BANNERS:", "SOCIAL:", "#"))]),
                "websites": websites,
                "banners": "\n".join(banners),
                "social": "\n".join(social),
                "hashtags": hashtags,
            })
        return variants
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []


############################  UI  ####################################
st.set_page_config(page_title="Phone Ad Cards", layout="wide")
st.title("📱 Phone Ad Cards – Search → Specs → AI Copy")

# ---------- SEARCH ----------
phone = st.text_input("Search phone / keywords", value="samsung a17 price kenya")
persona = st.selectbox("Buyer persona", ["Any", "Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if st.button("Generate cards"):
    with st.spinner("Scraping + AI crafting…"):
        raw = searx_raw(phone, pages=2)
        specs = gsm_specs(phone)
        variants = ai_pack(phone, raw, persona if persona != "Any" else "Budget students", tone)

    # ---------- GSMARENA CARD ----------
    if specs:
        with st.expander("🔍 GSMArena specs (one per line)"):
            for line in specs:
                st.markdown(f"- {line}")

    # ---------- AD VARIANT CARDS ----------
    if variants:
        st.subheader("AI Ad Variants (plain lists)")
        for idx, v in enumerate(variants):
            with st.container(border=True):
                st.markdown(f"### Variant {idx+1}")
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown("**Specs**")
                    st.text(v["specs"])
                    st.markdown("**Websites**")
                    for w in v["websites"]:
                        st.text(w)
                    st.markdown("**Banner ideas**")
                    st.text(v["banners"])
                with c2:
                    st.markdown("**Social pack**")
                    st.text(v["social"])
                    st.markdown("**Hashtags**")
                    st.text(v["hashtags"])
    else:
        st.info("No AI variants returned – try again.")
