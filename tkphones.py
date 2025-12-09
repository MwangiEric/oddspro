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


# ---------- PEXELS IMAGES ----------
def pexels_images(phone: str, qty: int = 3) -> list[str]:
    if not PEXELS_KEY:
        return [f"https://source.unsplash.com/400x300/?{phone.replace(' ','')},phone&sig={i}" for i in range(qty)]
    try:
        url = f"https://api.pexels.com/v1/search?query={phone.replace(' ','+')}&per_page={qty}"
        r = requests.get(url, headers={"Authorization": PEXELS_KEY}, timeout=15)
        r.raise_for_status()
        return [p["src"]["medium"] for p in r.json()["photos"]]
    except Exception:
        # fallback
        return [f"https://source.unsplash.com/400x300/?{phone.replace(' ','')},phone&sig={i}" for i in range(qty)]


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
5. "FLYERS:" 2 flyer ideas
6. "FB:" Facebook post under 300 chars + hashtags on new line
7. "TT:" TikTok caption under 150 chars + hashtags on new line
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
            # safe extract
            correct_name = [l.replace("CORRECT_NAME:", "").strip() for l in lines if l.startswith("CORRECT_NAME:")][0] if any(l.startswith("CORRECT_NAME:") for l in lines) else phone
            specs        = [l.replace("ATTRACTIVE_SPECS:", "").strip() for l in lines if l.startswith("ATTRACTIVE_SPECS:")]
            prices       = [l.replace("PRICES:", "").strip() for l in lines if l.startswith("PRICES:")]
            banners      = [l.replace("BANNERS:", "").strip() for l in lines if l.startswith("BANNERS:")]
            flyers       = [l.replace("FLYERS:", "").strip() for l in lines if l.startswith("FLYERS:")]
            fb_full      = "\n".join([l.replace("FB:", "").strip() for l in lines if l.startswith("FB:")])
            tt_full      = "\n".join([l.replace("TT:", "").strip() for l in lines if l.startswith("TT:")])
            variants.append({
                "correct_name": correct_name,
                "specs": "\n".join(specs),
                "prices": prices,
                "banners": "\n".join(banners),
                "flyers": "\n".join(flyers),
                "fb": fb_full,
                "tt": tt_full,
            })
        return variants
    except Exception as e:
        st.error(f"Groq error: {e}")
        return []


############################  UI  ####################################
st.set_page_config(page_title="Copy-to-Post – Tripple K", layout="wide")
st.title("📱 Copy-to-Post – Tripple K Communications")

# ---------- SEARCH ----------
use_searx = st.checkbox("Use SearXNG (slow cold-start)", value=False)
phone = st.text_input("Phone name / keywords", value="samsung a17")
persona = st.selectbox("Buyer persona", ["Any", "Tech-savvy pros", "Budget students", "Camera creators", "Status execs"])
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if st.button("Generate copy-pack"):
    with st.spinner("Crafting…"):
        # 1. Groq first → correct name
        groq_raw = [{"title": phone, "content": ""}]  # dummy for Groq
        groq_pack = ai_pack(phone, groq_raw, persona if persona != "Any" else "Budget students", tone)
        correct_name = groq_pack[0]["correct_name"] if groq_pack else phone

        # 2. GSMarena specs
        specs = gsm_specs(correct_name)

        # 3. Optional SearXNG
        if use_searx:
            raw = searx_raw(correct_name, pages=2)
            variants = ai_pack(correct_name, raw, persona if persona != "Any" else "Budget students", tone)
        else:
            variants = groq_pack

        # 4. Images
        images = pexels_images(correct_name, qty=3)

    # ---------- HEADER ----------
    st.header(correct_name)

    # ---------- IMAGES ----------
    if images:
        st.image(images, width=200)

    # ---------- SPECS ----------
    if specs:
        with st.expander("🔍 Attractive specs (top 10)"):
            for line in specs:
                st.markdown(f"- {line}")

    # ---------- PRICES TABLE ----------
    if variants and variants[0]["prices"]:
        st.subheader("💰 Price spots")
        prices = variants[0]["prices"]
        if prices:
            cols = st.columns(3)
            cols[0].markdown("**Website**")
            cols[1].markdown("**Price**")
            cols[2].markdown("**Link**")
            for line in prices:
                parts = line.split(" - ")
                if len(parts) == 3:
                    site, price, url = parts
                    c1, c2, c3 = st.columns(3)
                    c1.text(site.strip())
                    c2.text(price.strip())
                    c3.markdown(f"[🔗]({url.strip()})")
                else:
                    st.text(line)  # fallback

    # ---------- BANNERS & FLYERS ----------
    if variants:
        st.subheader("🖼️ Banners / Flyers")
        for v in variants:
            st.text(v["banners"])
            st.text(v["flyers"])

    # ---------- SOCIAL PACK (FB + TT only) ----------
    if variants:
        st.subheader("📲 Social pack (FB + TikTok)")
        for idx, v in enumerate(variants):
            with st.container(border=True):
                st.markdown(f"**Variant {idx+1}**")
                # Facebook
                st.markdown("**Facebook**")
                fb = v["fb"]
                st.code(fb, language="text")
                if st.button("Copy FB", key=f"fb{idx}"):
                    st.write(fb)  # fallback for cloud
                    st.toast("Facebook copied!", icon="✅")

                # TikTok
                st.markdown("**TikTok**")
                tt = v["tt"]
                st.code(tt, language="text")
                if st.button("Copy TT", key=f"tt{idx}"):
                    st.write(tt)
                    st.toast("TikTok copied!", icon="✅")

else:
    st.info("Fill fields and hit Generate copy-pack.")