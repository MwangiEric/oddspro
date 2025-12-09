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
STORE_NAME = "Tripple K Communications"
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
                for tr in soup2.select("table.specs tr") if len(tr.find_all("td")) == 2][:10]  # max 10
    except Exception:
        return []


# ---------- AI PACK (plain text) ----------
def ai_pack(phone: str, raw_json: list, persona: str, tone: str) -> list[dict]:
    hashtag_text = " ".join([r.get("title", "") + " " + r.get("content", "") for r in raw_json])
    prompt = f"""Kenyan phone-marketing assistant for {STORE_NAME}.
Phone: {phone}
Persona: {persona}
Tone: {tone}
Store: {STORE_NAME} | {STORE_URL} | {STORE_PHONE}
Raw text: {hashtag_text}

Return ONLY plain text (no JSON/objects) with exactly 3 blocks separated by "-----".

Each block contains:
1. "CORRECT_NAME:" official commercial name (max 4 words)
2. "ATTRACTIVE_SPECS:" most appealing specs first (max 10 lines, one per line)
3. "PRICES:" 3 lines: website - raw price - url (use real URLs from raw text)
4. "BANNERS:" 2 full poster lines
5. "SOCIAL:" 3 ready-to-post texts (Tweet, IG, FB) each on its own line
6. "HASHTAGS:" 10 relevant hashtags, space-separated
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
        for blk in blocks[:3]:
            lines = [l.strip() for l in blk.splitlines() if l.strip()]
            # quick split
            correct_name = [l.replace("CORRECT_NAME:", "").strip() for l in lines if l.startswith("CORRECT_NAME:")][0]
            specs        = [l.replace("ATTRACTIVE_SPECS:", "").strip() for l in lines if l.startswith("ATTRACTIVE_SPECS:")]
            prices       = [l.replace("PRICES:", "").strip() for l in lines if l.startswith("PRICES:")]
            banners      = [l.replace("BANNERS:", "").strip() for l in lines if l.startswith("BANNERS:")]
            social       = [l.replace("SOCIAL:", "").strip() for l in lines if l.startswith("SOCIAL:")]
            hashtags     = [l for l in lines if l.startswith("#")][0] if any(l.startswith("#") for l in lines) else "#PhoneDeals"
            variants.append({
                "correct_name": correct_name,
                "specs": "\n".join([l for l in lines if l.startswith("ATTRACTIVE_SPECS:")]),
                "prices": prices,
                "banners": "\n".join(banners),
                "social": "\n".join(social),
                "hashtags": hashtags,
            })
        return variants
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []


############################  UI  ####################################
st.set_page_config(page_title="Phone Ad Cards – Tripple K", layout="wide")
st.title("📱 Phone Ad Cards – Tripple K Communications")

phone = st.text_input("Search phone / keywords", value="samsung a17 price kenya")
persona = st.selectbox("Buyer persona", ["Any", "Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if st.button("Generate cards"):
    with st.spinner("Scraping + AI crafting…"):
        raw = searx_raw(phone, pages=2)
        specs = gsm_specs(phone)
        variants = ai_pack(phone, raw, persona if persona != "Any" else "Budget students", tone)

    # ---------- CORRECT NAME + SPECS ----------
    if variants:
        correct = variants[0]["correct_name"]
        st.header(correct)
    else:
        correct = phone
        st.header(correct)

    if specs:
        with st.expander("🔍 Attractive specs (top 10)"):
            for line in specs:
                st.markdown(f"- {line}")

    # ---------- PRICE TABLE ----------
    if variants and variants[0]["prices"]:
        st.subheader("💰 Price spots")
        for line in variants[0]["prices"]:
            parts = line.split(" - ")
            if len(parts) == 3:
                site, price, url = parts
                site = site.strip()
                price = price.strip()
                url = url.strip()
                col1, col2, col3 = st.columns([1, 1, 3])
                col1.markdown(f"**{site}**")
                col2.markdown(f"`{price}`")
                col3.markdown(f"[🔗 link]({url})")
            else:
                st.text(line)  # fallback

    # ---------- BANNER IDEAS ----------
    if variants:
        st.subheader("🖼️ Banner ideas")
        for v in variants:
            st.text(v["banners"])

    # ---------- SOCIAL PACK ----------
    if variants:
        st.subheader("📲 Social pack")
        for v in variants:
            st.markdown("**Tweet**")
            st.text(v["social"].splitlines()[0])
            st.markdown("**IG caption**")
            st.text(v["social"].splitlines()[1])
            st.markdown("**FB post**")
            st.text(v["social"].splitlines()[2])
            st.markdown("**Hashtags**")
            st.text(v["hashtags"])

else:
    st.info("Fill fields and hit Generate cards.")
