import streamlit as st
import requests
import time
import urllib.parse
from groq import Groq
from bs4 import BeautifulSoup
import pandas as pd

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("Add groq_key to .streamlit/secrets.toml")
    st.stop()
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
    for page in range(1, pages + 1):
        try:
            r = requests.get(
                SEARX_URL,
                params={
                    "q": phone, 
                    "category_general": "1", 
                    "language": "auto",
                    "safesearch": "0", 
                    "format": "json", 
                    "pageno": page
                },
                timeout=25,
            )
            r.raise_for_status()  # Raise an error for bad responses
            out.extend(r.json().get("results", []))
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching search results: {e}")
            return []
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
    except Exception as e:
        st.error(f"Error fetching specifications: {e}")
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
3. "PRICES:" website - raw price - url (use real URLs from raw text)
4. "BANNERS:" flyer ideas
5. "SOCIAL:" ready-to-post texts (FB, TikTok) each on its own line
6. "HASHTAGS:" 10 relevant hashtags, space-separated
-----
<next block>
-----
<next block>
"""
    try:
        out = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4, timeout=30
        )
        raw = out.choices[0].message.content.strip()
        blocks = [b.strip() for b in raw.split("-----") if b.strip()]
        variants = []

        for blk in blocks[:3]:
            lines = [l.strip() for l in blk.splitlines() if l.strip()]
            data = {}
            for line in lines:
                if line.startswith("CORRECT_NAME:"):
                    data["correct_name"] = line.replace("CORRECT_NAME:", "").strip()
                elif line.startswith("ATTRACTIVE_SPECS:"):
                    data["specs"] = line.replace("ATTRACTIVE_SPECS:", "").strip()
                elif line.startswith("PRICES:"):
                    data["prices"] = line.replace("PRICES:", "").strip()
                elif line.startswith("BANNERS:"):
                    data["banners"] = line.replace("BANNERS:", "").strip()
                elif line.startswith("SOCIAL:"):
                    data["social"] = line.replace("SOCIAL:", "").strip()
                elif line.startswith("#"):
                    data["hashtags"] = line.strip() if "hashtags" not in data else data["hashtags"] + " " + line.strip()    
            variants.append(data)  # ensure we append the full data dictionary
        return variants
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []

############################ UI ####################################
st.set_page_config(page_title="Phone Ad Cards – Tripple K", layout="wide")
st.title("📱 Phone Ad Cards – Tripple K Communications")

phone = st.text_input("Search phone / keywords", value="samsung a17 price kenya")
persona = st.selectbox("Buyer persona", ["Any", "Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

# User choice for using SearxNG
use_searxng = st.radio("Use SearxNG for additional search?", ["Yes", "No"], index=1)

if st.button("Generate cards"):
    with st.spinner("Scraping + AI crafting…"):
        if use_searxng == "Yes":
            raw = searx_raw(phone, pages=2)
        else:
            raw = []

        # Use Groq with the phone input directly
        variants = ai_pack(phone, raw, persona if persona != "Any" else "Budget students", tone)

        # If no variants from Groq, we can optionally display a message or handle it as needed
        if variants:
            correct_name = variants[0]["correct_name"]
            st.header(correct_name)

            # Display specs
            specs = gsm_specs(correct_name) 
            if specs:
                st.subheader("🔍 Attractive Specs (Top 10)")
                for line in specs:
                    st.markdown(f"- {line}")

            # Display prices in a stylish table
            if variants[0].get("prices"):
                st.subheader("💰 Price Spots")
                price_data = []
                for line in variants[0]["prices"].split('\n'):
                    parts = line.split(" - ")
                    if len(parts) == 3:
                        site, price, url = [p.strip() for p in parts]
                        price_data.append({"Website": site, "Price": price, "URL": url})
                if price_data:
                    price_df = pd.DataFrame(price_data)
                    st.table(price_df)  # Use tables for better readability

            # Generate and display flyer ideas
            if variants[0].get("banners"):
                st.subheader("🖼️ Flyer Ideas")
                st.write(variants[0]["banners"])

            # Social media posts
            if variants[0].get("social"):
                st.subheader("📲 Social Media Posts")
                social_lines = variants[0]["social"].splitlines()
                if len(social_lines) >= 2:
                    st.markdown("**Facebook Post**")
                    st.text(social_lines[0])
                    st.markdown("**TikTok Post**")
                    st.text(social_lines[1])

            # Hashtags
            if variants[0].get("hashtags"):
                st.subheader("🏷️ Hashtags")
                st.text(variants[0]["hashtags"])

else:
    st.info("Fill fields and hit Generate cards.")
