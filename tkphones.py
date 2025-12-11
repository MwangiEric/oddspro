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
SEARX_URL = "https://searxng-587s.onrender.com/search".strip()  # Fixed trailing space
MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
LAST_CALL = 0
RATE_LIMIT = 3

# Branding
BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
DEFAULT_TONE = "Playful"

# Tripple K contact
TRIPPLEK_PHONE = "+254700123456"
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
        h2 {{
            font-size: 1.8rem;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def extract_retailer_simple(url: str) -> str:
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    # Extract main part before TLD (e.g., jumia from jumia.co.ke)
    parts = domain.split(".")
    return parts[0] if parts else "unknown"


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

Return ONLY a full, valid image URL or "unknown".
"""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=120,
            timeout=8,
        )
        pred = comp.choices[0].message.content.strip()
        if pred != "unknown" and pred.startswith("http"):
            return pred
    except:
        pass
    return ""


def is_image_valid(img_url: str) -> bool:
    try:
        r = requests.head(img_url, timeout=3, headers=HEADERS)
        return r.status_code == 200 and "image" in r.headers.get("content-type", "").lower()
    except:
        return False


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
                    r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)(?!\s*(?:gb|mb|gbp|usd|eur))',
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
                st.error("❌ SearXNG failed after 3 attempts. Falling back to AI-only mode.")
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

BRAND:
- CTA: "Shop now at Tripple K Communications" or "Visit tripplek.co.ke"
- Default tone: Playful

INPUT:
PHONE: {phone}
TARGET PERSONA: {persona}
TONE: {tone}
WEB CONTEXT (real snippets):
{web_context}

RETURN EXACTLY these 4 sections:
---PRICE---
---SPECS---
---INSIGHTS---
---COPY---

1. PRICE: "Retailer - KSh X,XXX - URL" for each priced result.

2. SPECS: Up to 10 specs from context.

3. INSIGHTS: Real trends from snippets. Short lines.

4. COPY:
   - BANNERS: 2 lines (≤40 chars)
   - TIKTOK: <100 chars
   - IG / FB: benefit-driven
   - WHATSAPP: Include phone number: {TRIPPLEK_PHONE}
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


def generate_marketing_without_data(phone: str, persona: str, tone: str) -> tuple:
    prompt = f"""You are a marketing expert for **Tripple K Communications** in Kenya.

Create realistic, helpful content for:
PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

DO NOT invent prices, retailers, or fake specs.
Focus on general benefits, brand trust, and call-to-action.

RETURN ONLY this section:
---COPY---

- BANNERS: 2 lines (≤40 chars)
- TIKTOK: 1 line <100 chars
- IG / FB: short posts
- WHATSAPP: include phone {TRIPPLEK_PHONE}
- HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only.
"""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            timeout=30,
            max_tokens=800,
        )
        raw = comp.choices[0].message.content.strip()
        # Fake empty blocks for price/specs/insights
        return ("", "", "", raw)
    except Exception as e:
        st.error(f"🤖 Groq fallback error: {e}")
        return "", "", "", ""


############################ STREAMLIT UI ####################################
inject_brand_css()
st.title("📱 Tripple K Phone Ad Generator")
st.caption("Flyer-Ready Marketing Kits for Tripple K Communications | www.tripplek.co.ke")

phone = st.text_input("🔍 Phone model (e.g., Tecno Spark 20)", value="Xiaomi Poco X6 Pro")
persona = st.selectbox("👤 Buyer Persona", 
                      ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Status execs"], 
                      index=0)
tone = st.selectbox("🎨 Brand Tone", 
                   ["Playful", "Rational", "Luxury", "FOMO"], 
                   index=0)

if st.button("🚀 Generate Tripple K Marketing Kit", type="primary"):
    fetch_date = datetime.now().strftime("%d %b %Y at %H:%M EAT")

    with st.status("🔍 Generating Tripple K Ad Kit...", expanded=True) as status:
        st.write("🌐 Fetching Kenyan offers...")
        web_results = searx_all_results(phone)
        searx_success = len(web_results) > 0

        if searx_success:
            web_context = build_groq_context(web_results)
            st.write("🧠 Creating data-driven copy...")
            price_block, specs_block, insights_block, copy_block = generate_marketing_with_data(
                phone, web_context, persona, tone
            )
            # Generate price summary
            from collections import defaultdict
            prices = []
            for r in web_results:
                if r.get("price_ksh"):
                    clean = re.sub(r"[^\d]", "", r["price_ksh"])
                    if clean.isdigit():
                        prices.append(int(clean))
            if prices:
                min_p, max_p, avg_p = min(prices), max(prices), round(sum(prices)/len(prices))
                oos = sum(1 for r in web_results if "Out of stock" in r.get("stock", ""))
                stock_note = "Most in stock." if oos == 0 else "Some out of stock."
                insights_summary = f"Kenyan prices for the {phone} range from KSh {min_p:,} to KSh {max_p:,}. {stock_note}"
                price_recommendation = f"**Recommended Price: KSh {max_p - 500:,}**"
                price_stats = {"min": min_p, "max": max_p, "avg": avg_p, "rec": max_p - 500}
            else:
                insights_summary = f"No pricing data found for {phone}."
                price_recommendation = ""
                price_stats = {}
        else:
            st.write("🧠 Creating AI-only copy (no live data)...")
            price_block, specs_block, insights_block, copy_block = generate_marketing_without_data(phone, persona, tone)
            insights_summary = f"⚠️ No live market data. AI-generated suggestions only."
            price_recommendation = ""
            price_stats = {}

        status.update(label="✅ Tripple K Kit Ready!", state="complete", expanded=False)

    # ------- PHONE NAME + SUMMARY -------
    st.markdown(f"## {phone}")
    st.markdown(insights_summary)
    if price_recommendation:
        with st.expander("💰 Price Strategy"):
            st.markdown(price_recommendation)
            if price_stats:
                st.markdown(f"📊 **Range**: KSh {price_stats['min']:,} – KSh {price_stats['max']:,} | **Avg**: KSh {price_stats['avg']:,}")

    # ------- PRICE TABLE (only if data exists) -------
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
        # Sort by numeric price (high to low)
        def extract_price(row):
            clean = re.sub(r"[^\d]", "", row["Price (KSh)"])
            return int(clean) if clean.isdigit() else 0
        rows.sort(key=extract_price, reverse=True)
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    elif not searx_success:
        st.caption("⚠️ No pricing data — SearXNG unavailable.")

    # ------- SPECS -------
    if specs_block and searx_success:
        st.sub00bheader("📱 Key Specs")
        st.text(specs_block)

    # ------- INSIGHTS -------
    if insights_block and searx_success:
        with st.expander("📈 Strategic Market Insights"):
            for line in insights_block.splitlines():
                if line.strip():
                    st.markdown(f"- {line.strip()}")

    # ------- COPY -------
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
        st.text_area("WhatsApp", social["WhatsApp"] or f"Hi! Interested in {phone}? Call/WhatsApp Tripple K: {TRIPPLEK_PHONE}", height=100)
        st.text_input("Hashtags", hashtags.strip())

    # ------- COMPETITOR IMAGES (non-blocking, only if data) -------
    if searx_success:
        st.subheader("📸 Competitor Product Images (Preview)")
        other_urls = [r for r in web_results if not is_tripplek_url(r["url"])][:4]
        valid_images = []
        with st.status("🔍 Checking competitor images...", expanded=False):
            for r in other_urls:
                url = r["url"]
                img_url = predict_image_url_with_groq(phone, url)
                if img_url and is_image_valid(img_url):
                    valid_images.append({"url": url, "img": img_url})
                    if len(valid_images) >= 3:
                        break
        if valid_images:
            cols = st.columns(2)
            for i, item in enumerate(valid_images):
                with cols[i % 2]:
                    st.image(item["img"], caption=item["url"], use_container_width=True)
        else:
            st.caption("No competitor images found.")

    st.divider()
    st.caption(f"Generated for **Tripple K Communications** | [www.tripplek.co.ke](https://www.tripplek.co.ke) | Data: {fetch_date} EAT")