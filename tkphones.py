#!/usr/bin/env python3
import streamlit as st, requests, time, urllib.parse
from groq import Groq
from bs4 import BeautifulSoup

############################  CONFIG  ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("Add groq_key to .streamlit/secrets.toml")
    st.stop()

client = Groq(api_key=GROQ_KEY, timeout=30)
SEARX_URL = "https://searxng-587s.onrender.com/search"
RATE_LIMIT = 3
LAST = 0
MODEL = "llama-3.1-8b-instant"
#####################################################################


# ---------- POLITE SEARX ----------
def searx_raw(phone: str, pages: int = 2) -> list:
    """Polite SearXNG wrapper with simple paging."""
    global LAST
    elapsed = time.time() - LAST
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    LAST = time.time()

    out = []
    for p in range(1, pages + 1):
        r = requests.get(
            SEARX_URL,
            params={
                "q": phone,
                "category_general": "1",
                "language": "auto",
                "safesearch": "0",
                "format": "json",
                "pageno": p,
            },
            timeout=25,
        )
        r.raise_for_status()
        out.extend(r.json().get("results", []))
    return out


# ---------- GSMARENA ----------
def gsm_specs(phone: str) -> list[str]:
    """Grab up to 10 spec lines from GSMArena."""
    try:
        search = f"https://www.gsmarena.com/res.php3?sSearchWord={urllib.parse.quote(phone)}"
        soup = BeautifulSoup(requests.get(search, timeout=15).text, "html.parser")
        link = soup.select_one("div.makers a")
        if not link:
            return []
        device = urllib.parse.urljoin("https://www.gsmarena.com/", link["href"])
        soup2 = BeautifulSoup(requests.get(device, timeout=15).text, "html.parser")
        specs = []
        for tr in soup2.select("table.specs tr"):
            tds = tr.find_all("td")
            if len(tds) == 2:
                key = tds[0].get_text(strip=True)
                val = tds[1].get_text(strip=True)
                specs.append(f"{key}: {val}")
                if len(specs) >= 10:
                    break
        return specs
    except Exception:
        return []


# ---------- AI AD PACK ----------
def ai_pack(phone: str, raw_json: list, persona: str, tone: str) -> dict:
    """Use Groq to generate clean_name, prices, titles, banner/flyer ideas, FB + TT."""
    hashtag_text = " ".join(
        (r.get("title", "") or "") + " " + (r.get("content", "") or "") for r in raw_json
    )

    prompt = f"""
You are a Kenyan phone-marketing assistant for an online phone shop (tripplek.co.ke style).

Phone: {phone}
Persona: {persona}
Tone: {tone}
Raw text: {hashtag_text}

Your task: Return ONLY ONE block following the EXACT structure below.
No explanations, no emojis outside the content, no extra lines.
Maintain this structure, labels, spacing, and order.

------------------------------------------------------------
CLEAN_NAME: <exact phone model, one clean line>

PRICES:
# IMPORTANT: always follow this exact simple order → price, site, url
KSh 25,000 - jumia.co.ke - https://jumia.co.ke/...
KSh 24,500 - kilmall.co.ke - https://kilmall.co.ke/...
KSh 27,999 - safaricom.co.ke - https://safaricom.co.ke/...

POST_TITLES:
- Short title for FB post (5–8 words max)
- Short title for TikTok caption (3–6 words)

BANNERS:
- Short headline idea for poster 1 (no prices, no long specs)
- Short headline idea for poster 2
- Short headline idea for flyer 1
- Short headline idea for flyer 2

FLYER_IDEAS:
- Layout idea 1: Describe layout + 1–2 short benefit lines that appear on flyer
- Layout idea 2: Describe layout + 1–2 short benefit lines that appear on flyer

FLYER_TEXT:
- A ready-to-use flyer text block (2–3 short lines, includes phone name, one simple spec hint, and soft CTA)
- A second variant of flyer text (same rules)

FB:
Create a full Facebook post in smooth, natural Kenyan English.
Rules:
- 3–4 sentences only.
- Mention the phone name and a realistic price or price range in KSh.
- Use ONLY smart, simple spec hints (clean camera, big battery, smooth feel). No spec-sheet-style lists.
- Include a light pain-point/solution angle (battery anxiety, blurry photos, slow phones).
- Mention convenience: same-day delivery Nairobi + pay on delivery.
- Use soft urgency (moving fast, limited restock).
- End with 3–5 relevant hashtags.
Start the line with exactly: FB:

TT:
Create a short, hype Kenyan TikTok caption.
Rules:
- 1–2 punchy lines only.
- Light spec hints allowed, no full spec sheet.
- Use polite urgency (grab yours now, don’t miss, moving fast).
- Include 5–8 short, relevant hashtags.
Start the line with exactly: TT:

------------------------------------------------------------
EXAMPLE (Do NOT copy values, only structure):

CLEAN_NAME: Samsung Galaxy A17

PRICES:
KSh 25,000 - jumia.co.ke - https://jumia.co.ke/...
KSh 24,500 - kilmall.co.ke - https://kilmall.co.ke/...
KSh 27,999 - safaricom.co.ke - https://safaricom.co.ke/...

POST_TITLES:
- Fresh Upgrade for Everyday Use
- A17 Deal Alert

BANNERS:
- Upgrade to a cleaner camera and all-day power.
- Smooth feel, easy on your pocket.
- Sharp photos for your everyday hustle.
- Fresh upgrade, zero drama.

FLYER_IDEAS:
- Layout idea 1: Phone on right, bold title left, 1 benefit line below (clean camera / long battery), TrippleK logo bottom corner.
- Layout idea 2: Centered phone, top headline, small detail line under it, CTA strip at bottom.

FLYER_TEXT:
- Samsung Galaxy A17 – clean camera, smooth feel. Order today, same-day delivery Nairobi.
- A17 Upgrade – all-day battery and sharp photos. Grab yours now, pay on delivery.

FB: Samsung Galaxy A17 now landing from around KSh 24K–27K for Kenyan buyers. Enjoy a clean camera, big battery and a smooth everyday feel without breaking your budget. Same-day delivery available in Nairobi and you can pay on delivery for peace of mind. Moving fast and restocks are limited, so lock yours in today. #SamsungA17 #PhoneDeals #KenyaTech #NairobiDelivery

TT: A17 with big battery and clean camera ready for your daily hustle – from about 24K in Kenya. Grab yours now before the next restock disappears. #SamsungA17 #PhoneKenya #BudgetUpgrade #NairobiDeals #TikTokKenya #BigBattery

------------------------------------------------------------

Return exactly ONE block using the structure above and nothing else.
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            timeout=30,
        )
        raw = resp.choices[0].message.content.strip()
        lines = [l.strip() for l in raw.splitlines() if l.strip()]

        clean_name = phone
        prices: list[str] = []
        post_titles: list[str] = []
        banners: list[str] = []
        flyer_ideas: list[str] = []
        flyer_text: list[str] = []
        fb = ""
        tt = ""

        section = None
        for line in lines:
            # section headers
            if line.startswith("CLEAN_NAME:"):
                clean_name = line.split(":", 1)[1].strip()
                section = None
                continue
            if line.startswith("PRICES:"):
                section = "prices"
                continue
            if line.startswith("POST_TITLES:"):
                section = "post_titles"
                continue
            if line.startswith("BANNERS:"):
                section = "banners"
                continue
            if line.startswith("FLYER_IDEAS:"):
                section = "flyer_ideas"
                continue
            if line.startswith("FLYER_TEXT:"):
                section = "flyer_text"
                continue
            if line.startswith("FB:"):
                fb = line[3:].strip()
                section = None
                continue
            if line.startswith("TT:"):
                tt = line[3:].strip()
                section = None
                continue

            # content lines
            if section == "prices":
                if line.startswith("#"):
                    continue
                if " - " in line:
                    prices.append(line)
            elif section == "post_titles" and line.startswith("- "):
                post_titles.append(line[2:].strip())
            elif section == "banners" and line.startswith("- "):
                banners.append(line[2:].strip())
            elif section == "flyer_ideas" and line.startswith("- "):
                flyer_ideas.append(line[2:].strip())
            elif section == "flyer_text" and line.startswith("- "):
                flyer_text.append(line[2:].strip())

        return {
            "clean_name": clean_name,
            "prices": prices,
            "post_titles": post_titles,
            "banners": banners,
            "flyer_ideas": flyer_ideas,
            "flyer_text": flyer_text,
            "fb": fb,
            "tt": tt,
        }
    except Exception as e:
        st.error(f"Groq error: {e}")
        return {}


############################  UI  ####################################
st.set_page_config(page_title="Phone Ad Cards – TrippleK Style", layout="wide")
st.title("📱 Phone Ad & Flyer Builder")

phone = st.text_input("Search phone / keywords", value="samsung a17 price kenya")
persona = st.selectbox(
    "Buyer persona",
    ["Budget students", "Tech-savvy pros", "Camera creators", "Status execs"],
)
tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if st.button("Generate pack"):
    with st.spinner("Scraping + crafting copy…"):
        raw_results = searx_raw(phone, pages=2)
        specs = gsm_specs(phone)
        pack = ai_pack(phone, raw_results, persona, tone)

    if not pack:
        st.info("No AI pack returned – try again.")
    else:
        clean_name = pack.get("clean_name") or phone
        st.header(clean_name)

        # SPECS (for poster, not repeated in social)
        if specs:
            st.subheader("🔍 Specs (for poster only)")
            for line in specs:
                st.markdown(f"- {line}")

        # PRICES TABLE (price, site, url)
        prices = pack.get("prices") or []
        if prices:
            st.subheader("💰 Price Table (price, site, url)")
            st.markdown("| Price | Site | URL |")
            st.markdown("|-------|------|-----|")
            for line in prices:
                parts = line.split(" - ")
                if len(parts) == 3:
                    price_val, site, url = [p.strip() for p in parts]
                    st.markdown(f"| {price_val} | {site} | [{url}]({url}) |")

        # POST TITLES
        post_titles = pack.get("post_titles") or []
        if post_titles:
            st.subheader("📝 Post titles")
            if len(post_titles) > 0:
                st.markdown(f"- **FB title:** {post_titles[0]}")
            if len(post_titles) > 1:
                st.markdown(f"- **TT title:** {post_titles[1]}")

        # BANNERS
        banners = pack.get("banners") or []
        if banners:
            st.subheader("📰 Banner / Poster headlines")
            for b in banners:
                st.markdown(f"- {b}")

        # FLYER IDEAS
        flyer_ideas = pack.get("flyer_ideas") or []
        if flyer_ideas:
            st.subheader("📐 Flyer layout ideas")
            for idea in flyer_ideas:
                st.markdown(f"- {idea}")

        # FLYER TEXT
        flyer_text = pack.get("flyer_text") or []
        if flyer_text:
            st.subheader("📄 Flyer text variants")
            for i, txt in enumerate(flyer_text[:2], start=1):
                st.markdown(f"**Flyer text {i}:**")
                st.code(txt, language=None)

        # FULL SOCIAL COPY
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📘 Facebook Post")
            st.code(pack.get("fb", ""), language=None)
        with col2:
            st.markdown("### 🎵 TikTok Caption")
            st.code(pack.get("tt", ""), language=None)