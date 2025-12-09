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
STORE = "Tripple K Communications"
STORE_URL = "https://www.tripplek.co.ke"
STORE_PHONE = "0715679912"
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
                for tr in soup2.select("table.specs tr") if len(tr.find_all("td")) == 2][:10]
    except Exception:
        return []


# ---------- AI SOCIAL PACK ----------
def ai_social(phone: str, raw_json: list, persona: str, tone: str) -> list[dict]:
    hashtag_text = " ".join([r.get("title", "") + " " + r.get("content", "") for r in raw_json])
    prompt = f"""Kenyan social-media assistant for {STORE}.
Phone: {phone}
Persona: {persona}
Tone: {tone}
Store: {STORE} | {STORE_URL} | {STORE_PHONE}
Raw text: {hashtag_text}

Return ONLY plain text (no JSON/objects) with exactly 3 blocks separated by "-----".

Each block contains:
1. "TWEET:" under-280-chars text + 10 hashtags
2. "IG:" under-150-chars caption + 10 hashtags (emoji OK)
3. "FB:" under-300-chars post + 10 hashtags
4. "BANNERS:" 2 short poster lines
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
        packs = []
        for blk in blocks[:3]:
            lines = [l.strip() for l in blk.splitlines() if l.strip()]
            tweet = [l.replace("TWEET:", "").strip() for l in lines if l.startswith("TWEET:")][0] if any(l.startswith("TWEET:") for l in lines) else ""
            ig    = [l.replace("IG:", "").strip() for l in lines if l.startswith("IG:")][0] if any(l.startswith("IG:") for l in lines) else ""
            fb    = [l.replace("FB:", "").strip() for l in lines if l.startswith("FB:")][0] if any(l.startswith("FB:") for l in lines) else ""
            banners = "\n".join([l.replace("BANNERS:", "").strip() for l in lines if l.startswith("BANNERS:")])
            packs.append({"tweet": tweet, "ig": ig, "fb": fb, "banners": banners})
        return packs
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []


# ---------- IMAGES ----------
def phone_images(phone: str, qty: int = 3) -> list[str]:
    kw = phone.replace(" ", ",").lower()
    return [f"https://source.unsplash.com/400x300/?{kw},smartphone&sig={i}" for i in range(qty)]


############################  UI  ####################################
st.set_page_config(page_title="Copy-to-Post – Tripple K", layout="wide")
st.title("📱 Copy-to-Post – Tripple K Communications")

phone = st.text_input("Search phone / keywords", value="samsung a17 price kenya")
persona = st.selectbox("Buyer persona", ["Any", "Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if st.button("Generate copy-pack"):
    with st.spinner("Scraping + AI crafting…"):
        raw = searx_raw(phone, pages=2)
        specs = gsm_specs(phone)
        packs = ai_social(phone, raw, persona if persona != "Any" else "Budget students", tone)
        images = phone_images(phone, qty=3)

    # ---------- CORRECT NAME + SPECS ----------
    if packs:
        correct = packs[0]["tweet"].split("#")[0].strip()  # quick extract
    else:
        correct = phone
    st.header(correct)

    if specs:
        with st.expander("🔍 Attractive specs (top 10)"):
            for line in specs:
                st.markdown(f"- {line}")

    # ---------- IMAGES ----------
    if images:
        st.image(images, width=200)

    # ---------- COPY-PACK CARDS ----------
    if packs:
        st.subheader("📲 Copy-to-Post Pack")
        for idx, p in enumerate(packs):
            with st.container(border=True):
                st.markdown(f"### Variant {idx+1}")
                # Tweet
                st.markdown("**Tweet** (copy below)")
                tweet_text = p["tweet"]
                st.code(tweet_text, language="text")
                if st.button("Copy Tweet", key=f"t{idx}"):
                    st.write(tweet_text)  # fallback for cloud
                    st.toast("Tweet copied!", icon="✅")

                # IG
                st.markdown("**Instagram** (copy below)")
                ig_text = p["ig"]
                st.code(ig_text, language="text")
                if st.button("Copy IG", key=f"i{idx}"):
                    st.write(ig_text)
                    st.toast("IG caption copied!", icon="✅")

                # FB
                st.markdown("**Facebook** (copy below)")
                fb_text = p["fb"]
                st.code(fb_text, language="text")
                if st.button("Copy FB", key=f"f{idx}"):
                    st.write(fb_text)
                    st.toast("FB post copied!", icon="✅")

                # Banners
                st.markdown("**Banner ideas**")
                st.text(p["banners"])
