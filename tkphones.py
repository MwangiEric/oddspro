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

# SearXNG instances - add more for redundancy
SEARX_INSTANCES = [
    "https://searx.be/search",
    "https://search.ononoki.org/search",
    "https://searxng.site/search",
]
MODEL = "llama-3.1-8b-instant"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}
LAST_CALL = 0
RATE_LIMIT = 3

# Branding
BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
DEFAULT_TONE = "Playful"

# Tripple K contact (hardcoded, not secret)
TRIPPLEK_PHONE = "+254700123456"

# Seasonal hook
now = datetime.now()
is_christmas_season = (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 10)
CHRISTMAS_HOOK = "🎄 Christmas Special! Perfect gift with fast delivery & warranty." if is_christmas_season else ""


#####################################################################
# --- WAKE UP SEARX ON START ---
@st.cache_resource
def warm_up_searx(url):
    try:
        requests.get(url, params={"q": "test", "format": "json"}, timeout=10)
        return True
    except:
        return False  # Indicate failure to warm up


# --- CSS ---
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
    /* Mobile responsiveness */
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


# --- Helper Functions ---
def extract_retailer_simple(url: str) -> str:
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\\.", "", domain)
    return domain.split(".")[0]


def extract_ksh_prices(results: list[dict]) -> list[int]:
    prices = []
    for r in results:
        if r.get("price_ksh"):
            clean = re.sub(r"[^\\d]", "", r["price_ksh"])
            if clean.isdigit():
                prices.append(int(clean))
    return sorted(prices)


def recommend_price_and_summary(phone: str, results: list[dict]) -> tuple[str, str, dict]:
    prices = extract_ksh_prices(results)
    summary_parts = []
    price_stats = {"min": None, "max": None, "avg": None, "rec": None, "justification": ""}
    if prices:
        price_stats["min"] = min(prices)
        price_stats["max"] = max(prices)
        price_stats["avg"] = round(sum(prices) / len(prices))
        oos_count = sum(1 for r in results if "Out of stock" in r.get("stock", ""))
        if oos_count / len(results) > 0.5:
            rec = price_stats["avg"]
            just = "Market shows frequent stockouts—price at average to ensure competitiveness without underselling."
        else:
            rec = price_stats["max"] - 500 if price_stats["max"] > 5000 else price_stats["max"]
            just = f"Most retailers are in stock. Price just below the market high (KSh {price_stats['max']:,}) to attract value-conscious buyers while maintaining margin."
        price_stats["rec"] = rec
        price_stats["justification"] = just
        low = f"KSh {price_stats['min']:,}"
        high = f"KSh {price_stats['max']:,}"
        stock_note = "Most listings are in stock." if oos_count == 0 else (
            "Several retailers are out of stock." if oos_count > len(results) // 2 else "Stock is generally available.")
        summary_parts.append(f"Kenyan prices for the {phone} range from {low} to {high}. {stock_note}")
    else:
        summary_parts.append(f"No clear pricing data found for {phone} in Kenya yet.")
    if prices:
        avg = price_stats["avg"]
        if avg < 15000:
            persona_rec = "Budget Students"
            tone_rec = "Playful"
        elif avg < 30000:
            persona_rec = "All Kenyan Buyers"
            tone_rec = "FOMO"
        elif avg < 60000:
            persona_rec = "Tech-Savvy Pros"
            tone_rec = "Rational"
        else:
            persona_rec = "Status Execs"
            tone_rec = "Luxury"
        summary_parts.append(f"💡 Tripple K Tip: Best positioned for **{persona_rec}** using a **{tone_rec}** tone.")
    else:
        summary_parts.append("💡 Tripple K Tip: Gather more market data before deciding on audience.")
    return "\n".join(summary_parts), f"**Recommended Price: KSh {price_stats['rec']:,}**" if price_stats["rec"] else "", price_stats


def is_tripplek_url(url: str) -> bool:
    return "tripplek.co.ke" in url.lower()


def extract_slug_from_url(url: str) -> str:
    clean = url.split("?", 1)[0].split("#", 1)[0]
    parts = [p for p in clean.split("/") if p]
    return parts[-1].lower() if parts else ""


def predict_image_url_with_groq(phone: str, url: str) -> str:
    slug = extract_slug_from_url(url)
    prompt = f"""You are an e-commerce expert.
    Phone: {phone}
    Product page: {url}
    Slug: {slug}
    Kenyan sites often use WooCommerce. Likely image paths:
    /wp-content/uploads/YYYY/MM/{slug}.jpg
    /wp-content/uploads/YYYY/MM/{slug}-1024x1024.jpg
    Return ONLY a full, valid image URL or "unknown"."""
    try:
        comp = client.chat.completions.create(model=MODEL,
                                              messages=[{"role": "user", "content": prompt}],
                                              temperature=0.2,
                                              max_tokens=120,
                                              timeout=8, )
        pred = comp.choices[0].message.content.strip()
        if pred != "unknown" and pred.startswith("http"):
            return pred
    except:
        pass
    return ""


def is_image_valid(img_url: str) -> bool:
    try:
        r = requests.head(img_url, timeout=3, headers=HEADERS)
        ct = r.headers.get("content-type", "").lower()
        return r.status_code == 200 and ("image" in ct)
    except:
        return False


def get_searx_results(phone: str, url: str) -> list[dict]:
    global LAST_CALL
    wait = RATE_LIMIT - (time.time() - LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    LAST_CALL = time.time()
    try:
        r = requests.get(url,
                         params={"q": f'"{phone}" price Kenya', "format": "json", "language": "en", "safesearch": "0"},
                         headers=HEADERS,
                         timeout=20, )
        r.raise_for_status()
        raw = r.json().get("results", [])
        enriched = []
        for res in raw[:60]:
            title = res.get("title", "")
            content = res.get("content", "")
            url = res.get("url", "")
            full_text = f"{title} {content} {url}".lower()
            price_match = re.search(
                r'(?:ksh?|kes|shillings?)\\s*[:\\-]?\\s*(\\d{{3,}}(?:,\\d{{3}})*)(?!\\s*(?:gb|mb|gbp|usd|eur))',
                full_text, re.IGNORECASE)
            price = f"KSh {price_match.group(1)}" if price_match else None
            stock = "✅ In stock"
            text_lower = (title + " " + content).lower()
            if any(w in text_lower for w in ["out of stock", "sold out", "unavailable"]):
                stock = "❌ Out of stock"
            elif any(w in text_lower for w in ["limited stock", "few left", "hurry"]):
                stock = "⚠️ Limited stock"
            enriched.append({"title": title[:180], "url": url, "content": content[:300], "price_ksh": price,
                             "stock": stock, })
        return enriched
    except Exception as e:
        st.warning(f"⚠️ Error fetching from {url}: {e}")
        return []


def searx_all_results(phone: str) -> list[dict]:
    all_results = []
    for url in SEARX_INSTANCES:
        st.write(f"🌐 Trying SearXNG instance: {url}")
        results = get_searx_results(phone, url)
        if results:
            st.success(f"✅ Successfully fetched results from {url}")
            all_results = results
            break  # Stop on first successful instance
        else:
            st.warning(f"❌ Failed to get results from {url}")
    return all_results


def build_groq_context(results: list[dict]) -> str:
    lines = []
    for r in results:
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        lines.append(f"Title: {r['title']}{price}\nURL: {r['url']}\nSnippet: {r['content']}\nStock: {r['stock']}\n---")
    return "\n".join(lines) if lines else "No results found."


def parse_groq_response(raw: str):
    parts = raw.split("---PRICE---")
    if len(parts) < 2:
        return "", "", "", raw
    _, rest = parts[0], parts[1]
    spec_parts = rest.split("---SPECS---", 1)
    if len(spec_parts) < 2:
        return "", "", "", rest.strip()
    price_block, rest2 = spec_parts[0].strip(), spec_parts[1].strip()
    insight_parts = rest2.split("---INSIGHTS---", 1)
    if len(insight_parts) < 2:
        return price_block, rest2, "", ""
    specs_block, rest3 = insight_parts[0].strip(), insight_parts[1].strip()
    copy_parts = rest3.split("---COPY---", 1)
    insights_block = copy_parts[0].strip()
    copy_block = copy_parts[1].strip() if len(copy_parts) > 1 else ""
    return price_block, specs_block, insights_block, copy_block


def generate_marketing_with_data(phone: str, web_context: str, persona: str, tone: str) -> tuple:
    prompt = f"""You are the official marketing AI for **Tripple K Communications** (www.tripplek.co.ke).
    TRIPLE K VALUE PROPS (ALWAYS MENTION 1–2):
    - Accredited distributor of original brands
    - Full manufacturer warranty
    - Pay on delivery available
    {CHRISTMAS_HOOK} if {CHRISTMAS_HOOK}
    INPUT:
    PHONE: {phone}
    TARGET PERSONA: {persona}
    TONE: {tone}
    DATA:
    {web_context}
    RETURN EXACTLY:
    ---PRICE------SPECS------INSIGHTS------COPY---
    1. PRICE: "Retailer - KSh X,XXX - URL" only from data.
    2. SPECS: Up to 10 real specs.
    3. INSIGHTS: Short lines. No competitor names. Focus on Tripple K trust, warranty, delivery.
    4. COPY:
    - BANNERS: ≤40 chars
    - TIKTOK: <100 chars, fun, use emojis if Playful
    - IG/FB: Benefit-driven
    - WHATSAPP: Include phone {TRIPPLEK_PHONE}, warranty, pay on delivery
    - HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE
    Plain text only.
    """
    try:
        comp = client.chat.completions.create(model=MODEL,
                                              messages=[{"role": "user", "content": prompt}],
                                              temperature=0.6,
                                              max_tokens=2400, )
        return parse_groq_response(comp.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"🤖 Groq error: {e}")
        return "", "", "", ""


def generate_marketing_without_data(phone: str, persona: str, tone: str) -> tuple:
    prompt = f"""You are a marketing expert for **Tripple K Communications** in Kenya.
    Create realistic, helpful content for:
    PHONE: {phone}
    TARGET PERSONA: {persona}
    TONE: {tone}
    Tripple K VALUE PROPS (ALWAYS INCLUDE):
    - Accredited distributor of original brands
    - Full manufacturer warranty
    - Pay on delivery available
    {f"- {CHRISTMAS_HOOK}" if CHRISTMAS_HOOK else ""}
    DO NOT invent prices, retailers, or fake specs. Focus on general benefits, brand trust, and call-to-action.
    RETURN ONLY this
