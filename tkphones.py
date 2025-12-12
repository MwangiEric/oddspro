#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
import json
import os

############################ CONFIG ################################
# Get Groq key from secrets (required)
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("❗ Add `groq_key` to `.streamlit/secrets.toml`")
    st.stop()

from groq import Groq
client = Groq(api_key=GROQ_KEY)

# SearXNG instances (trimmed)
SEARX_INSTANCES = [
    "https://searx.be/search",
    "https://search.ononoki.org/search",
    "https://searxng.site/search",
    "https://northboot.xyz/search"
]

MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RATE_LIMIT = 3
LAST_CALL = 0

# Branding
BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
TRIPPLEK_PHONE = "+254700123456"

now = datetime.now()
is_christmas = (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 10)
CHRISTMAS_HOOK = "Perfect Christmas gift with warranty & fast delivery!" if is_christmas else ""
####################################################################

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
    }}
    h1, h2, h3 {{
        color: {BRAND_MAROON} !important;
    }}
    .dataframe thead th {{
        background-color: {BRAND_GREEN} !important;
        color: white !important;
    }}
    .main {{
        background-color: {BACKGROUND_LIGHT};
    }}
    .recommended-price {{
        background-color: #E8F5E9 !important;
        font-weight: bold;
    }}
    @media (max-width: 768px) {{
        .stTextArea textarea, .stCodeBlock {{
            font-size: 14px !important;
            white-space: pre-wrap;
            word-break: break-word;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def warm_up_searx():
    def ping_instance(url):
        try:
            r = requests.get(url, params={"q": "test", "format": "json"}, timeout=8)
            return url if r.status_code == 200 else None
        except:
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(ping_instance, SEARX_INSTANCES))
    online = [r for r in results if r]
    return online if online else SEARX_INSTANCES

def extract_retailer(url: str) -> str:
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    return domain.split(".")[0].capitalize()

def extract_slug_from_url(url: str) -> str:
    clean = url.split("?", 1)[0].split("#", 1)[0]
    parts = [p for p in clean.split("/") if p]
    return parts[-1].lower() if parts else ""

def predict_image_url(phone: str, url: str) -> str:
    slug = extract_slug_from_url(url)
    prompt = f"""Product: {phone}
URL: {url}
Slug: {slug}
Most Kenyan e-commerce sites use WooCommerce. Predict the direct image URL.
Common patterns:
/wp-content/uploads/2025/12/{slug}.jpg
/wp-content/uploads/2025/12/{slug}-1024x1024.jpg
Return only the full image URL or "unknown"."""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100,
            timeout=8
        )
        pred = comp.choices[0].message.content.strip()
        return pred if pred != "unknown" and pred.startswith("http") else ""
    except:
        return ""

def validate_image(url: str) -> bool:
    try:
        r = requests.head(url, timeout=3, headers=HEADERS)
        return r.status_code == 200 and "image" in r.headers.get("content-type", "").lower()
    except:
        return False

def fetch_kenyan_prices(phone: str) -> list[dict]:
    global LAST_CALL
    online_instances = warm_up_searx()
    for instance in online_instances:
        wait = RATE_LIMIT - (time.time() - LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        LAST_CALL = time.time()
        try:
            r = requests.get(
                instance,
                params={
                    "q": f'"{phone}" price Kenya',
                    "format": "json",
                    "language": "en",
                    "safesearch": "0"
                },
                headers=HEADERS,
                timeout=25
            )
            if r.status_code == 200:
                raw_results = r.json().get("results", [])[:60]
                st.session_state['raw_searx_results'] = raw_results  # Save raw
                enriched = []
                for res in raw_results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    url = res.get("url", "")
                    full_text = f"{title} {content}".lower()
                    
                    # --- ROBUST PRICE REGEX (handles decimals, commas, suffixes) ---
                    price_match = re.search(
                        r'(?:ksh?|kes|shillings?|k\.sh\.)\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d*)?)(?:\s*[/\'\-=]*)?|'
                        r'(\d{1,3}(?:,\d{3})*(?:\.\d*)?)\s*(?:ksh?|kes|shillings?|k\.sh\.)(?:\s*[/\'\-=]*)?',
                        full_text,
                        re.IGNORECASE
                    )
                    price_ksh_str = None
                    price_ksh_int = 0
                    if price_match:
                        raw_price = price_match.group(1) or price_match.group(2)
                        clean_price = re.sub(r"[^\d]", "", raw_price.split('.')[0])
                        if clean_price.isdigit() and len(clean_price) >= 4:
                            price_ksh_int = int(clean_price)
                            price_ksh_str = f"KSh {price_ksh_int:,}"
                    
                    # --- Stock ---
                    stock = "In stock"
                    if any(w in full_text for w in ["out of stock", "sold out", "unavailable"]):
                        stock = "Out of stock"
                    elif any(w in full_text for w in ["limited stock", "few left", "hurry"]):
                        stock = "Limited stock"
                    
                    enriched.append({
                        "title": title[:180],
                        "url": url,
                        "content": content[:300],
                        "price_ksh_str": price_ksh_str,
                        "price_ksh_int": price_ksh_int,
                        "stock": stock,
                        "published_date": res.get("publishedDate"),
                        "engine": res.get("engine", "Unknown")
                    })
                return enriched
        except Exception as e:
            st.sidebar.warning(f"Trying backup search engine...")
            continue
    return []

def generate_with_data(phone: str, results: list[dict], persona: str, tone: str) -> dict:
    context_lines = []
    for r in results:
        price = f" | {r['price_ksh_str']}" if r["price_ksh_str"] else ""
        context_lines.append(
            f"Title: {r['title']}{price}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {r['content']}\n"
            f"Stock: {r['stock']}\n---"
        )
    web_context = "\n".join(context_lines) if context_lines else "No data"
    
    prompt = f"""You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

TRIPPLE K VALUE PROPS (mention in copy):
* Accredited distributor
* Official warranty
* Pay on delivery
* Nairobi delivery

{f"SEASONAL: {CHRISTMAS_HOOK}" if CHRISTMAS_HOOK else ""}

PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

MARKET DATA:
{web_context}

OUTPUT 4 SECTIONS:

---PRICE---
List: "Retailer - KSh X,XXX - URL" for each result with price

---SPECS---
5-10 key specs from data

---INSIGHTS---
3-5 bullet points on market trends, what makes this phone compelling

---COPY---
BANNERS: 2 lines, max 40 chars, include "Tripple K"
TIKTOK: 1 fun line <100 chars, use emoji for Playful tone
IG: 2-3 sentences highlighting benefits
FB: Similar to IG
WHATSAPP: Include {TRIPPLEK_PHONE}, mention warranty, pay on delivery, {CHRISTMAS_HOOK if CHRISTMAS_HOOK else ""}
HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only. Use real data."""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2400,
            timeout=50
        )
        raw = comp.choices[0].message.content.strip()
        parts = raw.split("---PRICE---")
        if len(parts) < 2:
            return {"error": "Invalid format"}
        rest = parts[1]
        price_block = rest.split("---SPECS---")[0].strip() if "---SPECS---" in rest else ""
        rest = rest.split("---SPECS---", 1)[1] if "---SPECS---" in rest else ""
        specs_block = rest.split("---INSIGHTS---")[0].strip() if "---INSIGHTS---" in rest else ""
        rest = rest.split("---INSIGHTS---", 1)[1] if "---INSIGHTS---" in rest else ""
        insights_block = rest.split("---COPY---")[0].strip() if "---COPY---" in rest else ""
        copy_block = rest.split("---COPY---", 1)[1].strip() if "---COPY---" in rest else ""
        return {
            "prices": price_block,
            "specs": specs_block,
            "insights": insights_block,
            "copy": copy_block
        }
    except Exception as e:
        return {"error": str(e)}

def generate_without_data(phone: str, persona: str, tone: str) -> dict:
    prompt = f"""You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

Create marketing copy for:
PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

TRIPPLE K VALUE PROPS:
* Accredited distributor
* Official warranty
* Pay on delivery
* Nairobi delivery

{f"SEASONAL: {CHRISTMAS_HOOK}" if CHRISTMAS_HOOK else ""}

DO NOT invent prices or fake specs. Focus on benefits and trust.

OUTPUT:
---SPECS---
General expected specs for this phone model (if known)

---COPY---
BANNERS: 2 lines, max 40 chars
TIKTOK: 1 line <100 chars
IG: 2-3 sentences
FB: Similar to IG
WHATSAPP: Include {TRIPPLEK_PHONE}, warranty, delivery, {CHRISTMAS_HOOK if CHRISTMAS_HOOK else ""}
HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only."""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )
        raw = comp.choices[0].message.content.strip()
        specs_block = ""
        copy_block = raw
        if "---SPECS---" in raw:
            parts = raw.split("---SPECS---", 1)[1]
            specs_block = parts.split("---COPY---")[0].strip() if "---COPY---" in parts else ""
            copy_block = parts.split("---COPY---", 1)[1].strip() if "---COPY---" in parts else ""
        return {
            "prices": "",
            "specs": specs_block,
            "insights": "",
            "copy": copy_block
        }
    except Exception as e:
        return {"error": str(e)}

############################ STREAMLIT UI ####################################
inject_brand_css()

# Sidebar
with st.sidebar:
    st.title("GenerationStrategy")
    use_web_data = st.toggle("Use live web data", value=True, help="Search Kenyan retailers for real prices")
    persona = st.selectbox("Target Audience", 
        ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Business execs"],
        index=0)
    tone = st.selectbox("Brand Tone", 
        ["Playful", "Rational", "Luxury", "FOMO"],
        index=0)
    st.divider()
    st.caption("Tripple K Communications")
    st.caption("Accredited distributor")
    st.caption("Official warranty included")
    if CHRISTMAS_HOOK:
        st.success(CHRISTMAS_HOOK)

# Main view
st.title("Tripple K Phone Ad Generator")
st.caption("Data-Driven Marketing Kits | www.tripplek.co.ke")

phone = st.text_input("Phone model", placeholder="e.g., Samsung Galaxy A17, Poco X7")

if st.button("Generate Marketing Kit", type="primary"):
    if not phone:
        st.error("Please enter a phone model")
        st.stop()
    
    with st.status("Generating marketing kit...", expanded=True) as status:
        results = []
        if use_web_data:
            st.write("Searching Kenyan retailers...")
            results = fetch_kenyan_prices(phone)
            if not results:
                st.warning("No web data found. Generating AI-only copy...")
                use_web_data = False
            else:
                st.write(f"Found {len(results)} listings")
        st.write("Generating marketing content...")
        if use_web_data and results:
            kit = generate_with_data(phone, results, persona, tone)
        else:
            kit = generate_without_data(phone, persona, tone)
        if "error" in kit:
            st.error(f"AI error: {kit['error']}")
            st.stop()
        status.update(label="Marketing Kit Ready!", state="complete", expanded=False)

    # Summary
    st.markdown(f"## {phone}")
    if use_web_data and results:
        prices_numeric = [r["price_ksh_int"] for r in results if r["price_ksh_int"] > 0]
        if prices_numeric:
            min_p, max_p = min(prices_numeric), max(prices_numeric)
            oos_count = sum(1 for r in results if "out" in r["stock"].lower())
            stock_note = "Most listings are in stock." if oos_count == 0 else "Some retailers are out of stock."
            st.info(f"Kenyan prices range from KSh {min_p:,} to KSh {max_p:,}. {stock_note}")

    # Price Cards
    if use_web_data and results:
        priced_results = [r for r in results if r["price_ksh_int"] > 0]
        if priced_results:
            st.subheader("Competitor Prices")
            cols = st.columns(min(3, len(priced_results)))
            for i, r in enumerate(priced_results):
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div style="background:white;padding:1rem;border-radius:8px;box-shadow:0 2px 6px #ddd;margin-bottom:1rem;">
                        <h4 style="color:{BRAND_MAROON};margin:0;">{r['retailer']}</h4>
                        <p style="font-size:1.2rem;font-weight:bold;color:{BRAND_GREEN};margin:0.5rem 0;">{r['price_ksh_str']}</p>
                        <p style="font-size:0.9rem;color:gray;margin:0.25rem 0;">{r['stock']}</p>
                        <a href="{r['url']}" target="_blank" style="font-size:0.85rem;color:{BRAND_MAROON};">View →</a>
                    </div>
                    """, unsafe_allow_html=True)

    # Price Table with Recommended Price
    if kit.get("prices"):
        st.subheader("Market Price Comparison")
        price_lines = [l.strip() for l in kit["prices"].splitlines() if l.strip()]
        rows = []
        prices_numeric = []
        for i, line in enumerate(price_lines):
            parts = line.split(" - ")
            if len(parts) >= 3:
                price_str = parts[1]
                clean = re.sub(r"[^\d]", "", price_str)
                price_val = int(clean) if clean.isdigit() else 0
                if price_val > 0:
                    prices_numeric.append(price_val)
                    rows.append({
                        "Price": price_str,
                        "Retailer": extract_retailer(parts[2]),
                        "Link": " - ".join(parts[2:]),
                        "Stock": results[i]["stock"] if i < len(results) else "In stock",
                        "price_val": price_val,
                        "is_rec": False
                    })
        # Add Tripple K recommended price
        if prices_numeric:
            rec_price = max(prices_numeric) - 500
            rows.append({
                "Price": f"KSh {rec_price:,}",
                "Retailer": "Tripple K (Recommended)",
                "Link": "https://www.tripplek.co.ke",
                "Stock": "Available",
                "price_val": rec_price,
                "is_rec": True
            })
        rows.sort(key=lambda x: x["price_val"], reverse=True)
        df = pd.DataFrame([{
            "Retailer": r["Retailer"],
            "Price": r["Price"],
            "Stock": r["Stock"],
            "Link": f"[View]({r['Link']})" if r['Link'].startswith('http') else r['Link']
        } for r in rows])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Specs
    if kit.get("specs"):
        st.subheader("Key Specs")
        st.text(kit["specs"])

    # Insights
    if kit.get("insights"):
        with st.expander("Market Insights"):
            for line in kit["insights"].splitlines():
                if line.strip():
                    st.markdown(f"* {line.strip()}")

    # Ad Copy
    st.subheader("Ready-to-Use Ad Copy")
    lines = [l.strip() for l in kit["copy"].splitlines() if l.strip()]
    banners, social, hashtags = [], {}, ""
    for line in lines:
        if "BANNERS:" in line:
            pass
        elif "TikTok:" in line or "TIKTOK:" in line:
            social["TikTok"] = line.split(":", 1)[1].strip()
        elif "IG:" in line:
            social["IG"] = line.split(":", 1)[1].strip()
        elif "FB:" in line:
            social["FB"] = line.split(":", 1)[1].strip()
        elif "WHATSAPP:" in line.upper():
            social["WhatsApp"] = line.split(":", 1)[1].strip()
        elif line.startswith("#"):
            hashtags = line
        elif not any(k in line for k in ["BANNERS", "TIKTOK", "IG", "FB", "WHATSAPP", "HASHTAGS"]):
            if len(banners) < 2:
                banners.append(line)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Banner Text**")
        for b in banners[:2]:
            st.code(b, language="text")
    with c2:
        st.markdown("**Social Media Copy**")
        st.text_area("TikTok", social.get("TikTok", ""), height=60, key="tt")
        st.text_area("Instagram", social.get("IG", ""), height=70, key="ig")
        st.text_area("Facebook", social.get("FB", ""), height=70, key="fb")
        st.text_area("WhatsApp", social.get("WhatsApp", f"Get {phone} at Tripple K! Call {TRIPPLEK_PHONE}"), height=100, key="wa")
        st.text_input("Hashtags", hashtags)

    # Product Images
    if use_web_data and results:
        st.subheader("Product Images (Preview)")
        with st.spinner("Checking retailer sites..."):
            valid_images = []
            for r in results[:5]:
                if "tripplek" not in r["url"].lower():
                    img_url = predict_image_url(phone, r["url"])
                    if img_url and validate_image(img_url):
                        valid_images.append({"url": r["url"], "img": img_url})
                        if len(valid_images) >= 3:
                            break
            if valid_images:
                cols = st.columns(3)
                for i, item in enumerate(valid_images):
                    with cols[i]:
                        st.image(item["img"], use_container_width=True)
                        st.caption(extract_retailer(item["url"]))
            else:
                st.caption("No product images found")

    # --- DEBUG: Raw vs Filtered Results ---
    if use_web_data and 'raw_searx_results' in st.session_state:
        with st.expander("🔍 Raw vs Filtered Search Results"):
            st.write(f"**Raw SearXNG Results**: {len(st.session_state['raw_searx_results'])}")
            st.write(f"**Enriched Results**: {len(results)}")
            tab1, tab2 = st.tabs(["Raw", "Enriched"])
            with tab1:
                st.json(st.session_state['raw_searx_results'])
            with tab2:
                st.json(results)

st.divider()
st.caption(f"Generated {datetime.now().strftime('%d %b %Y %H:%M EAT')} | Tripple K Communications | tripplek.co.ke")
