#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("❌ Add `groq_key` to `.streamlit/secrets.toml`")
    st.stop()

from groq import Groq
client = Groq(api_key=GROQ_KEY)
SEARX_URL = "https://searxng-587s.onrender.com/search"
MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
LAST_CALL = 0
RATE_LIMIT = 3

# Branding
BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
DEFAULT_TONE = "Playful"
TRIPPLEK_PHONE = "+254700123456"

# Seasonal hook
now = datetime.now()
is_christmas_season = (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 10)
CHRISTMAS_HOOK = "🎄 Christmas Special! Perfect gift with fast delivery & warranty." if is_christmas_season else ""
####################################################################


# --- WAKE UP SEARX ON START ---
@st.cache_resource
def warm_up_searx():
    try:
        requests.get(SEARX_URL, params={"q": "test", "format": "json"}, timeout=10)
    except:
        pass  # Silent fail — not critical


warm_up_searx()  # Runs once on app load


def inject_brand_css():
    st.markdown(f"""
    <style>
    .stButton>button {{
        background-color: {BRAND_MAROON};
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5rem 1rem;
    }}
    .stButton>button:hover {{
        background-color: #5a0000;
        color: white;
    }}
    h1, h2, h3, h4 {{
        color: {BRAND_MAROON} !important;
    }}
    .dataframe thead th {{
        background-color: {BRAND_GREEN} !important;
        color: white !important;
    }}
    .main {{
        background-color: {BACKGROUND_LIGHT};
    }}
    footer {{
        visibility: hidden;
    }}
    @media (max-width: 768px) {{
        .stTextArea > div > div > textarea,
        .stCodeBlock {{
            font-size: 14px !important;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        [data-testid="column"] {{
            width: 100% !important;
            margin-bottom: 1rem;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def extract_retailer_simple(url: str) -> str:
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    return domain.split(".")[0]


def searx_all_results(phone: str) -> list[dict]:
    global LAST_CALL
    max_retries = 3
    retry_wait = 5
    for attempt in range(1, max_retries + 1):
        wait = RATE_LIMIT - (time.time() - LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        LAST_CALL = time.time()

        try:
            r = requests.get(
                SEARX_URL,
                params={"q": f'"{phone}" price Kenya', "format": "json", "language": "en", "safesearch": "0"},
                headers=HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            raw = r.json().get("results", [])
            enriched = []
            for res in raw[:60]:
                title = res.get("title", "")
                content = res.get("content", "")
                url = res.get("url", "")
                full_text = f"{title} {content} {url}".lower()

                price_match = re.search(
                    r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{{3,}}(?:,\d{{3}})*)(?!\s*(?:gb|mb|gbp|usd|eur))',
                    full_text,
                    re.IGNORECASE
                )
                price = f"KSh {price_match.group(1)}" if price_match else None

                stock = "✅ In stock"
                text_lower = (title + " " + content).lower()
                if any(w in text_lower for w in ["out of stock", "sold out", "unavailable"]):
                    stock = "❌ Out of stock"
                elif any(w in text_lower for w in ["limited stock", "few left", "hurry"]):
                    stock = "⚠️ Limited stock"

                enriched.append({
                    "title": title[:180],
                    "url": url,
                    "content": content[:300],
                    "price_ksh": price,
                    "stock": stock,
                })
            return enriched
        except Exception as e:
            if attempt < max_retries:
                st.warning(f"⚠️ Server is starting... (attempt {attempt}/{max_retries}). Retrying in {retry_wait}s.")
                time.sleep(retry_wait)
            else:
                st.error("❌ SearXNG failed after 3 attempts. No live data available.")
                return []
    return []


def build_groq_context(results: list[dict]) -> str:
    lines = []
    for r in results:
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        lines.append(f"Title: {r['title']}{price}\nURL: {r['url']}\nSnippet: {r['content']}\nStock: {r['stock']}\n---")
    return "\n".join(lines) if lines else "No results found."


def parse_groq_response(raw: str):
    parts = raw.split("---PRICE---")
    if len(parts) < 2:
        return ("", "", "", raw)
    _, rest = parts[0], parts[1]
    spec_parts = rest.split("---SPECS---", 1)
    if len(spec_parts) < 2:
        return ("", "", "", rest.strip())
    price_block, rest2 = spec_parts[0].strip(), spec_parts[1].strip()
    insight_parts = rest2.split("---INSIGHTS---", 1)
    if len(insight_parts) < 2:
        return (price_block, rest2, "", "")
    specs_block, rest3 = insight_parts[0].strip(), insight_parts[1].strip()
    copy_parts = rest3.split("---COPY---", 1)
    insights_block = copy_parts[0].strip()
    copy_block = copy_parts[1].strip() if len(copy_parts) > 1 else ""
    return (price_block, specs_block, insights_block, copy_block)


def generate_marketing_with_data(phone: str, web_context: str, persona: str, tone: str) -> tuple:
    prompt = f"""You are the official marketing AI for **Tripple K Communications** (www.tripplek.co.ke).

TRIPLE K VALUE PROPS (ALWAYS MENTION 1–2):
- Accredited distributor of original brands
- Full manufacturer warranty
- Pay on delivery available
- Fast Nairobi delivery

{"🎄 CHRISTMAS SEASON HOOK: Great gift with warranty & fast delivery!" if is_christmas_season else ""}

INPUT:
PHONE: {phone}
PERSONA: {persona}
TONE: {tone}
DATA:
{web_context}

RETURN EXACTLY:
---PRICE---
---SPECS---
---INSIGHTS---
---COPY---

1. PRICE: "Retailer - KSh X,XXX - URL" only from data.

2. SPECS: Up to 10 real specs.

3. INSIGHTS: Short lines. No competitor names. Focus on Tripple K trust.

4. COPY:
   - BANNERS: ≤40 chars
   - TIKTOK: <100 chars, fun, use emojis if Playful
   - IG/FB: Benefit-driven
   - WHATSAPP: Include phone {TRIPPLEK_PHONE}, warranty, pay on delivery
   - HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only.
"""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            timeout=50,
            max_tokens=2400,
        )
        return parse_groq_response(comp.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"🤖 Groq error: {e}")
        return "", "", "", ""


############################ STREAMLIT UI ####################################
inject_brand_css()
st.title("📱 Tripple K Phone Ad Generator")
st.caption("Flyer-Ready Marketing Kits | www.tripplek.co.ke")

phone = st.text_input("🔍 Phone model (e.g., Xiaomi Poco X6 Pro)", value="Xiaomi Poco X6 Pro")
persona = st.selectbox("👤 Buyer Persona", 
                      ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Status execs"], 
                      index=0)
tone = st.selectbox("🎨 Brand Tone", 
                   ["Playful", "Rational", "Luxury", "FOMO"], 
                   index=0)

if st.button("🚀 Generate Tripple K Marketing Kit", type="primary"):
    fetch_date = datetime.now().strftime("%d %b %Y at %H:%M EAT")

    with st.status("🔍 Fetching live Kenyan market data...", expanded=True) as status:
        st.write("🌐 Waking up SearXNG and fetching offers...")
        web_results = searx_all_results(phone)
        searx_success = len(web_results) > 0

        if searx_success:
            web_context = build_groq_context(web_results)
            st.write("🧠 Generating data-backed marketing kit...")
            price_block, specs_block, insights_block, copy_block = generate_marketing_with_data(
                phone, web_context, persona, tone
            )
        else:
            st.write("⚠️ No live data. Showing phone name only.")
            price_block = specs_block = insights_block = ""
            copy_block = ""

        status.update(label="✅ Done!", state="complete", expanded=False)

    # ------- PHONE NAME -------
    st.markdown(f"## {phone}")
    if CHRISTMAS_HOOK:
        st.info(CHRISTMAS_HOOK)

    # ------- PRICE TABLE (ONLY IF DATA) -------
    if searx_success and price_block.strip():
        st.subheader("🛒 Verified Kenyan Prices")
        price_lines = [line.strip() for line in price_block.splitlines() if line.strip()]
        rows = []
        for i, line in enumerate(price_lines):
            parts = line.split(" - ")
            if len(parts) >= 3:
                price_str = parts[1]
                url = " - ".join(parts[2:])
                retailer = extract_retailer_simple(url)
                stock = web_results[i].get("stock", "✅ In stock") if i < len(web_results) else "✅ In stock"
                rows.append({
                    "Price (KSh)": price_str,
                    "Retailer": retailer,
                    "Stock": stock,
                    "Link": url
                })
        def extract_price(row):
            clean = re.sub(r"[^\d]", "", row["Price (KSh)"])
            return int(clean) if clean.isdigit() else 0
        rows.sort(key=extract_price, reverse=True)
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ------- SPECS (ONLY IF DATA) -------
    if searx_success and specs_block.strip():
        st.subheader("📱 Key Specs")
        st.text(specs_block)

    # ------- INSIGHTS (ONLY IF DATA) -------
    if searx_success and insights_block.strip():
        with st.expander("📈 Market Insights"):
            for line in insights_block.splitlines():
                if line.strip():
                    st.markdown(f"- {line.strip()}")

    # ------- COPY (ALWAYS SHOW IF GENERATED) -------
    if copy_block.strip():
        st.subheader("📣 Ready-to-Use Copy")
        lines = [l.strip() for l in copy_block.splitlines() if l.strip()]
        banners = []
        social = {"TikTok": "", "IG": "", "FB": "", "WhatsApp": ""}
        hashtags = ""

        current = None
        for line in lines:
            if line.startswith("BANNERS:"):
                current = "banner"
            elif line.startswith("TikTok:"):
                social["TikTok"] = line.replace("TikTok:", "").strip()
                current = "tiktok"
            elif line.startswith("IG:"):
                social["IG"] = line.replace("IG:", "").strip()
                current = "ig"
            elif line.startswith("FB:"):
                social["FB"] = line.replace("FB:", "").strip()
                current = "fb"
            elif line.startswith("WHATSAPP:"):
                social["WhatsApp"] = line.replace("WHATSAPP:", "").strip()
                current = "whatsapp"
            elif line.startswith("#"):
                hashtags = line
                break
            elif current == "banner" and len(banners) < 2:
                banners.append(line)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🖼️ Banner Text**")
            for b in banners[:2]:
                st.code(b, language="plaintext")
        with c2:
            st.markdown("**📲 Social Posts**")
            st.text_area("TikTok", social["TikTok"], height=60)
            st.text_area("Instagram", social["IG"], height=70)
            st.text_area("Facebook", social["FB"], height=70)
            st.text_area("WhatsApp", social["WhatsApp"], height=100)
            st.text_input("Hashtags", hashtags.strip())

    st.divider()
    st.caption(f"Generated for **Tripple K Communications** | [www.tripplek.co.ke](https://www.tripplek.co.ke) | {fetch_date} EAT")