#!/usr/bin/env python3
"""
TrippleK Phone-Ad Builder – Kenya-only, mobile-first, zero bloat
pip install streamlit requests groq beautifulsoup4 tenacity pandas
"""

import os, json, re, time, urllib.parse, logging, streamlit as st, pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List

import requests
from groq import Groq
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

# ---------- CONFIG ----------
GROQ_KEY = st.secrets.get("groq_key") or os.getenv("GROQ_KEY")
if not GROQ_KEY:
    st.error("🛑  Add groq_key to .streamlit/secrets.toml or env var GROQ_KEY")
    st.stop()

CLIENT = Groq(api_key=GROQ_KEY, timeout=30)
SEARX_URL = "https://searxng-587s.onrender.com/search"
MODEL = "llama-3.1-8b-instant"

# ---------- CONSTANTS ----------
BRAND = {"primary": "#FF4F33", "dark": "#1E1E1E", "light": "#F9F9F9", "font": "Inter, sans-serif"}
USER_BUCKETS: dict[str, float] = {}
RATE_LIMIT = 1.2


# ---------- UTILS ----------
def _wait(uid: str):
    last = USER_BUCKETS.get(uid, 0)
    elapsed = time.time() - last
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    USER_BUCKETS[uid] = time.time()


def clean_query(q: str) -> str:
    stop = {"kenya", "ke", ".co.ke", "price"}
    words = re.split(r"\s+", q.strip())
    kept = [w for w in words if w.lower() not in stop]
    return " ".join(kept)


# ---------- API CALLS ----------
@st.cache_data(ttl=3600, show_spinner=False)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def searx_raw(raw_query: str) -> List[dict]:
    uid = st.session_state.get("uid", "default")
    _wait(uid)
    q = f"({clean_query(raw_query)}) (kenya | .co.ke)"
    r = requests.get(
        SEARX_URL,
        params={"q": q, "category_general": "1", "language": "auto", "safesearch": "0", "format": "json"},
        timeout=30,
    )
    r.raise_for_status()
    hits = r.json().get("results", [])
    slim = [
        {"title": h.get("title", ""), "url": h.get("url", ""), "content": h.get("content", "")}
        for h in hits
        if "ke" in h.get("url", "").lower()
    ]
    return slim[:12]


@st.cache_data(ttl=3600, show_spinner=False)
def gsm_specs(phone: str) -> List[str]:
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
                specs.append(f"{tds[0].get_text(strip=True)}: {tds[1].get_text(strip=True)}")
                if len(specs) >= 10:
                    break
        return specs
    except Exception as e:
        logging.warning("GSMArena fail: %s", e)
        return []


# ---------- AI ----------
def ai_pack(phone: str, kenya_json: List[dict], persona: str, tone: str) -> dict:
    txt = " ".join((r.get("title") or "") + " " + (r.get("content") or "") for r in kenya_json)[:2500]

    prompt = f"""You are a Kenyan phone-marketing assistant for tripplek.co.ke.

Phone: {phone}
Persona: {persona}
Tone: {tone}
Kenya results: {txt}

Return ONLY the exact block below (no chat):

CLEAN_NAME: <exact model>

PRICES:
KSh XX,XXX - site.co.ke - https://...
...

POST_TITLES:
- FB 5–8 words
- TT 3–6 words

BANNERS:
- Head 1
- Head 2
- Head 3
- Head 4

FLYER_IDEAS:
- Layout 1: desc + benefit
- Layout 2: desc + benefit

FLYER_TEXT:
- Variant 1 (2–3 lines)
- Variant 2 (2–3 lines)

FB:
FB: <3–4 Kenyan sentences, KSh price, spec hint, same-day Nairobi, soft urgency, 3–5 hashtags>

TT:
TT: <1–2 punchy lines, 5–8 hashtags>

WA_BLAST:
WA: <1-line WhatsApp hook + emoji + price + "Reply 1" CTA>

MARKETING_STYLES:
- Tone used by sites: (bullet list)
- Urgency tactics: (bullet list)
- CTA phrases: (bullet list)
"""
    try:
        resp = CLIENT.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.35, max_tokens=1200
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Groq error: {e}")
        return {}

    def grab(section: str) -> List[str]:
        m = re.search(rf"^{section}:\s*(.*?)(?=^[A-Z_]+:|$)", raw, re.MULTILINE | re.DOTALL)
        if not m:
            return []
        return [ln[2:].strip() for ln in m.group(1).splitlines() if ln.startswith("- ")]

    prices = [ln for ln in raw.splitlines() if ln.startswith("KSh ") and " - " in ln]
    return {
        "clean_name": raw.splitlines()[0].replace("CLEAN_NAME:", "").strip(),
        "prices": prices,
        "post_titles": grab("POST_TITLES"),
        "banners": grab("BANNERS"),
        "flyer_ideas": grab("FLYER_IDEAS"),
        "flyer_text": grab("FLYER_TEXT"),
        "fb": raw.split("FB:")[1].split("TT:")[0].strip() if "FB:" in raw else "",
        "tt": raw.split("TT:")[1].split("WA_BLAST:")[0].strip() if "TT:" in raw else "",
        "wa_blast": raw.split("WA_BLAST:")[1].split("MARKETING_STYLES:")[0].strip() if "WA_BLAST:" in raw else "",
        "marketing_styles": grab("MARKETING_STYLES"),
    }


# ---------- UI ----------
st.set_page_config(
    page_title="TrippleK Ad Builder",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "uid" not in st.session_state:
    st.session_state.uid = datetime.now().isoformat()

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html,body,[class*="css"]{{font-family:{BRAND['font']};background:{BRAND['light']};color:{BRAND['dark']}}}
    .main-header{{background:linear-gradient(90deg,{BRAND['primary']} 0%,#FF6A52 100%);padding:1.2rem 2rem;border-radius:12px;color:white;margin-bottom:2rem}}
    .main-header h1{{margin:0;font-weight:700;font-size:2rem}}
    .main-header p{{margin:0;opacity:.9}}
    .card{{background:white;border-radius:12px;padding:1.5rem;box-shadow:0 2px 6px rgba(0,0,0,.06);margin-bottom:1.5rem}}
    div.stButton > button{{background:{BRAND['primary']};color:white;border:none;border-radius:8px;padding:.5rem 1.8rem;font-weight:600;transition:.2s}}
    div.stButton > button:hover{{background:#E63E2A;transform:translateY(-1px)}}
    .dataframe th{{background:{BRAND['primary']};color:white}}
    @media (max-width:768px){{.main-header{{padding:1rem}}.main-header h1{{font-size:1.6rem}}.card{{padding:1rem}}}}
    </style>",
    unsafe_allow_html=True,
)


def card(title, body):
    st.markdown(f'<div class="card"><h3>{title}</h3>{body}</div>', unsafe_allow_html=True)


st.markdown(
    '<div class="main-header"><h1>📱 TrippleK Ad & Flyer Builder</h1>'
    "<p>Generate ready-to-post Kenyan phone ads in seconds</p></div>",
    unsafe_allow_html=True,
)

with st.form("inputs"):
    c1, c2 = st.columns([3, 1])
    with c1:
        phone = st.text_input("Search phone / keywords", value="samsung a17")
    with c2:
        st.write("")
        submitted = st.form_submit_button("Build pack", use_container_width=True)
    c3, c4 = st.columns(2)
    with c3:
        persona = st.selectbox(
            "Buyer persona",
            ["Budget students", "Tech-savvy pros", "Camera creators", "Status execs"],
        )
    with c4:
        tone = st.selectbox("Brand tone", ["Playful", "Luxury", "Rational", "FOMO"])

if submitted:
    with st.spinner("Crafting Kenya-ready pack…"):
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_searx = ex.submit(searx_raw, phone)
            fut_specs = ex.submit(gsm_specs, phone)
        raw_results = fut_searx.result()
        specs = fut_specs.result()
        pack = ai_pack(phone, raw_results, persona, tone)

    if not pack:
        st.info("No pack returned – try different keywords.")
        st.stop()

    card("🔍 " + pack["clean_name"], "")
    if specs:
        with st.expander("Specs for poster"):
            for l in specs:
                st.markdown("- " + l)

    if pack["prices"]:
        df = pd.DataFrame([p.split(" - ", 2) for p in pack["prices"]], columns=["Price", "Site", "URL"])
        card("💰 Price Table", st.dataframe(df, use_container_width=True, hide_index=True))

    if pack["post_titles"]:
        card("📝 Post titles", f"**Facebook:** {pack['post_titles'][0]}  \n**TikTok:** {pack['post_titles'][1]}")

    col1, col2 = st.columns(2)
    with col1:
        card("📘 Facebook Post", st.code(pack["fb"], language=None))
    with col2:
        card("🎵 TikTok Caption", st.code(pack["tt"], language=None))

    if pack.get("wa_blast"):
        card("📲 WhatsApp Blast", st.code(pack["wa_blast"], language=None))

    # BANNER / FLYER AT BOTTOM
    if pack["banners"]:
        card("📰 Banner / Poster headlines", "".join(f"- {b}  \n" for b in pack["banners"]))

    if pack["flyer_ideas"]:
        card("📐 Flyer layout ideas", "".join(f"- {i}  \n" for i in pack["flyer_ideas"]))

    if pack["flyer_text"]:
        card("📄 Flyer text variants", st.code("\n\n".join(pack["flyer_text"][:2]), language=None))

    if pack.get("marketing_styles"):
        card("📊 Marketing Styles Detected", "".join(f"- {m}  \n" for m in pack["marketing_styles"]))

    st.download_button(
        label="📥 Download full pack",
        data=json.dumps(pack, indent=2, ensure_ascii=False),
        file_name=f"{pack['clean_name'].replace(' ','_')}_pack.txt",
        mime="text/plain",
    )
