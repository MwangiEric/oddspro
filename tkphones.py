import streamlit as st
import requests
import json
import time
import urllib.parse
import re
import openai
from bs4 import BeautifulSoup

############################ CONFIG ################################
XAI_KEY = st.secrets.get("xai_key", "")
if not XAI_KEY:
    st.error("Add xai_key to .streamlit/secrets.toml"); st.stop()
client = openai.OpenAI(api_key=XAI_KEY, base_url="https://api.x.ai/v1")
SEARX_URL = "https://searxng-587s.onrender.com/search"
RATE_LIMIT = 3
LAST = 0
MODEL = "grok-beta"
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
4. "FLYERS:" 2 full flyer slogan lines
5. "SOCIAL:" 2 ready-to-post texts (FB, TikTok) each on its own line
6. "HASHTAGS:" 10 relevant hashtags, space-separated
-----
<next block>
-----
<next block>
"""
    try:
        out = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        raw = out.choices[0].message.content.strip()
        blocks = [b.strip() for b in raw.split("-----") if b.strip()]
        variants = []
        for blk in blocks[:3]:
            lines = [l.strip() for l in blk.splitlines() if l.strip()]
            correct_name = ""
            specs_lines = []
            prices_lines = []
            flyers_lines = []
            social_lines = []
            hashtags = ""
            current_section = None
            for line in lines:
                if line.startswith("CORRECT_NAME:"):
                    correct_name = line.replace("CORRECT_NAME:", "").strip()
                    current_section = None
                elif line.startswith("ATTRACTIVE_SPECS:"):
                    spec = line.replace("ATTRACTIVE_SPECS:", "").strip()
                    if spec:
                        specs_lines.append(spec)
                    current_section = "specs"
                elif line.startswith("PRICES:"):
                    price = line.replace("PRICES:", "").strip()
                    if price:
                        prices_lines.append(price)
                    current_section = "prices"
                elif line.startswith("FLYERS:"):
                    flyer = line.replace("FLYERS:", "").strip()
                    if flyer:
                        flyers_lines.append(flyer)
                    current_section = "flyers"
                elif line.startswith("SOCIAL:"):
                    soc = line.replace("SOCIAL:", "").strip()
                    if soc:
                        social_lines.append(soc)
                    current_section = "social"
                elif line.startswith("HASHTAGS:"):
                    hashtags = line.replace("HASHTAGS:", "").strip()
                    current_section = None
                else:
                    if current_section == "specs":
                        specs_lines.append(line)
                    elif current_section == "prices":
                        prices_lines.append(line)
                    elif current_section == "flyers":
                        flyers_lines.append(line)
                    elif current_section == "social":
                        social_lines.append(line)
            variants.append({
                "correct_name": correct_name,
                "specs": "\n".join(specs_lines),
                "prices": prices_lines,
                "flyers": "\n".join(flyers_lines),
                "social": "\n".join(social_lines),
                "hashtags": hashtags,
            })
        return variants
    except Exception as e:
        st.error(f"xAI error: {e}")
        return []

############################ UI ####################################
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
    
    # ---------- CORRECT NAME ----------
    if variants:
        correct = variants[0]["correct_name"]
        st.header(correct)
    else:
        correct = phone
        st.header(correct)
    
    # ---------- ATTRACTIVE SPECS ----------
    if variants and variants[0]["specs"]:
        st.subheader("🔍 Attractive Specs")
        for line in variants[0]["specs"].splitlines():
            st.markdown(f"- {line}")
    
    # ---------- TECHNICAL SPECS (OPTIONAL) ----------
    if specs:
        with st.expander("📊 Technical Specs from GSMArena"):
            for line in specs:
                st.markdown(f"- {line}")
    
    # ---------- PRICE TABLE ----------
    if variants and variants[0]["prices"]:
        st.subheader("💰 Price Spots")
        table_md = "| Website | Price | Link |\n|---------|-------|------|\n"
        for line in variants[0]["prices"]:
            parts = line.split(" - ")
            if len(parts) == 3:
                site, price, url = [p.strip() for p in parts]
                table_md += f"| {site} | {price} | [🔗]({url}) |\n"
        st.markdown(table_md)
    
    # ---------- AD COPY SECTION ----------
    if variants:
        st.subheader("📢 Ad Copy")
        for i, v in enumerate(variants, 1):
            st.markdown(f"**Variant {i}**")
            # Flyers
            st.markdown("**Flyer Ideas**")
            st.text(v["flyers"])
            # Social
            social_lines = v["social"].splitlines()
            if len(social_lines) >= 2:
                st.markdown("**FB Post**")
                st.text(social_lines[0])
                st.markdown("**TikTok Caption**")
                st.text(social_lines[1])
            # Hashtags
            st.markdown("**Hashtags**")
            st.text(v["hashtags"])
else:
    st.info("Fill fields and hit Generate cards.")
