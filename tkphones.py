#!/usr/bin/env python3
import streamlit as st, requests, json, time, urllib.parse, re
from groq import Groq
from bs4 import BeautifulSoup

############################  CONFIG  ################################
GROQ_KEY   = st.secrets.get("groq_key", "")
PEXELS_KEY = st.secrets.get("pexels_api_key", "")
if not GROQ_KEY:
    st.error("Add groq_key to .streamlit/secrets.toml"); st.stop()
client = Groq(api_key=GROQ_KEY, timeout=30)
SEARX_URL  = "https://searxng-587s.onrender.com/search"
RATE_LIMIT = 3
LAST       = 0
MODEL      = "llama-3.1-8b-instant"
STORE_NAME = "Tripple K Communications"
STORE_URL  = "https://www.tripplek.co.ke"
STORE_PHONE= "0715679912"
#####################################################################

# ---------- PEXELS + UNSPLASH ----------
def product_images(phone: str, qty: int = 10) -> list[str]:
    """Pexels product shots + Unsplash fallbacks."""
    pexels_urls = []
    if PEXELS_KEY:
        # product-focused terms
        terms = [f"{phone} product photo", f"{phone} studio shot", f"{phone} back side", "smartphone product"]
        for term in terms:
            url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(term)}&per_page=3"
            try:
                r = requests.get(url, headers={"Authorization": PEXELS_KEY}, timeout=10)
                r.raise_for_status()
                pexels_urls.extend([p["src"]["medium"] for p in r.json()["photos"]])
            except Exception:
                continue
    # Unsplash fallbacks
    words = phone.replace(" ", ",").lower()
    unsplash = [
        f"https://source.unsplash.com/800x800/?{words},smartphone,product&sig={i}" for i in range(4)
    ] + [
        f"https://source.unsplash.com/800x800/?smartphone,studio,white&sig={i}" for i in range(3)
    ]
    return (pexels_urls + unsplash)[:qty]

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

# ---------- AI PACK (5 blocks) ----------
def ai_pack(phone: str, raw_json: list, persona: str, tone: str) -> list[dict]:
    hashtag_text = " ".join([r.get("title", "") + " " + r.get("content", "") for r in raw_json])
    prompt = f"""Kenyan phone-marketing assistant for {STORE_NAME}.
Phone: {phone}
Persona: {persona}
Tone: {tone}
Store: {STORE_NAME} | {STORE_URL} | {STORE_PHONE}
Raw text: {hashtag_text}

Return ONLY plain text with exactly 5 blocks separated by "-----".

Block 0 = CLEAN_NAME: exact phone model only (e.g. "Samsung Galaxy A17")
Block 1 = TOTAL specs list (max 10 lines, one per line, most appealing first)
Block 2 = ALL prices table: one line per "site - price - url" (use real URLs from raw text)
Block 3 = BANNERS: 2 full poster lines
Block 4 = VARIANTS: 3 blocks (/// separated) each containing:
   "FB:" Facebook post under 300 chars + hashtags on new line
   "TT:" TikTok caption under 150 chars + hashtags on new line
   "FLYERS:" 2 flyer ideas

Example:
CLEAN_NAME: Samsung Galaxy A17
-----
6.7" AMOLED Display
5000mAh Battery
50MP Camera
8GB RAM
-----
Jumia - KSh 25,000 - https://...
Kilimall - KSh 24,500 - https://...
-----
25K FLASH SALE!
Order in 5 mins!
-----
FB: Samsung A17 now 25K! 🔥 #SamsungA17
TT: 25K Samsung A17! Limited stock! #PhoneDeals
FLYERS: 25K ONLY! / Same day delivery
///
FB: Pro camera A17 25K!
TT: A17 camera beast! #CameraPhone
FLYERS: 50MP Pro Camera / 25K
"""
    try:
        out = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.4, timeout=30
        )
        raw = out.choices[0].message.content.strip()
        blocks = [b.strip() for b in raw.split("-----") if b.strip()]
        if len(blocks) < 5:
            return []
        
        # Block 0: CLEAN_NAME
        name_line = blocks[0].strip()
        clean_name = phone.strip()
        if "CLEAN_NAME:" in name_line:
            candidate = name_line.split("CLEAN_NAME:", 1)[1].strip()
            if any(b in candidate.lower() for b in ["samsung", "iphone", "tecno", "infinix"]) and any(c.isdigit() for c in candidate):
                clean_name = candidate
        
        # Block 1-4
        total_specs = "
".join([l.strip() for l in blocks[1].splitlines() if l.strip()])
        prices = [l.strip() for l in blocks[2].splitlines() if l.strip() and " - " in l]
        banners = "
".join([l.strip() for l in blocks[3].splitlines() if l.strip()])
        
        variants_raw = [b.strip() for b in blocks[4].split("///") if b.strip()]
        variants = []
        for var in variants_raw[:3]:
            vlines = [l.strip() for l in var.splitlines() if l.strip()]
            fb_lines, tt_lines, fl_lines = [], [], []
            mode = None
            for line in vlines:
                if line.startswith("FB:"):
                    mode = "fb"; fb_lines.append(line.replace("FB:", "").strip()); continue
                if line.startswith("TT:"):
                    mode = "tt"; tt_lines.append(line.replace("TT:", "").strip()); continue
                if line.startswith("FLYERS:"):
                    mode = "fl"; fl_lines.append(line.replace("FLYERS:", "").strip()); continue
                if mode == "fb": fb_lines.append(line)
                elif mode == "tt": tt_lines.append(line)
                elif mode == "fl": fl_lines.append(line)
            variants.append({"fb": "
".join(fb_lines), "tt": "
".join(tt_lines), "flyers": "
".join(fl_lines)})
        
        return [{"clean_name": clean_name, "total_specs": total_specs, "prices": prices, "banners": banners, "variants": variants}]
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []

############################  UI  ####################################
st.set_page_config(page_title="Copy-to-Post – Tripple K", layout="wide")
st.title("📱 Copy-to-Post – Tripple K Communications")

use_searx = st.checkbox("Use SearXNG (slow cold-start)", value=False)
phone = st.text_input("Phone name / keywords", value="samsung a17")
persona = st.selectbox("Buyer persona", ["Any", "Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if st.button("Generate copy-pack"):
    with st.spinner("AI → Scrapers → Copy…"):
        # 1. FIRST AI CALL: get clean_name
        groq_raw = [{"title": phone, "content": ""}]
        name_pack = ai_pack(phone, groq_raw, persona if persona != "Any" else "Budget students", tone)
        
        if not name_pack:
            st.info("AI failed to parse name – try again.")
            st.stop()
            
        clean_name = name_pack[0].get("clean_name", phone).strip()
        
        # 2. SCRAPE EVERYTHING with clean_name
        images = product_images(clean_name, qty=10)
        specs = gsm_specs(clean_name)
        
        if use_searx:
            raw_searx = searx_raw(clean_name, pages=2)
            final_pack = ai_pack(clean_name, raw_searx, persona if persona != "Any" else "Budget students", tone)
        else:
            final_pack = name_pack

        pack = final_pack

    # ---------- HEADER ----------
    st.header(pack[0]["clean_name"] if pack else clean_name)

    # ---------- IMAGES ----------
    if images:
        st.subheader("🖼️ Product Images (copy URL for TRIPPLEK)")
        cols = st.columns(5)
        for i, img in enumerate(images[:10]):
            with cols[i % 5]:
                st.image(img, use_column_width=True)
                st.code(img)

    # ---------- GSMArena ----------
    if specs:
        with st.expander("🔍 GSMArena specs (raw)"):
            for line in specs:
                st.markdown(f"- {line}")

    # ---------- TOTAL SPECS ----------
    if pack and pack[0]["total_specs"]:
        with st.expander("🔍 Total attractive specs"):
            st.text(pack[0]["total_specs"])

    # ---------- ALL PRICES TABLE ----------
    if pack and pack[0]["prices"]:
        st.subheader("💰 All price spots")
        cols = st.columns(3)
        cols[0].markdown("**Website**")
        cols[1].markdown("**Price**")
        cols[2].markdown("**Link**")
        for line in pack[0]["prices"]:
            parts = line.split(" - ")
            if len(parts) == 3:
                site, price, url = parts
                c1, c2, c3 = st.columns(3)
                c1.text(site.strip())
                c2.text(price.strip())
                c3.markdown(f"[🔗]({url.strip()})")
            else:
                st.text(line)

    # ---------- BANNERS ----------
    if pack and pack[0]["banners"]:
        st.subheader("🖼️ Banner ideas (Copy for TRIPPLEK)")
        st.code(pack[0]["banners"], language="text")

    # ---------- 3 VARIANTS ----------
    if pack and pack[0]["variants"]:
        st.subheader("📲 Social pack (FB + TikTok)")
        for idx, v in enumerate(pack[0]["variants"]):
            with st.container(border=True):
                st.markdown(f"**Variant {idx+1}**")

                # Facebook
                st.markdown("**Facebook**")
                fb = v["fb"]
                st.code(fb, language="text")
                if st.button("📋 Copy FB", key=f"fb{idx}"):
                    st.toast("Facebook copied!", icon="✅")

                # TikTok
                st.markdown("**TikTok**")
                tt = v["tt"]
                st.code(tt, language="text")
                if st.button("📋 Copy TT", key=f"tt{idx}"):
                    st.toast("TikTok copied!", icon="✅")

                # Flyers
                st.markdown("**Flyer ideas**")
                st.text(v["flyers"])

else:
    st.info("Fill fields and hit Generate copy-pack.")