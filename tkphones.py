#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime

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


def extract_ksh_prices(results: list[dict]) -> list[int]:
    prices = []
    for r in results:
        if r.get("price_ksh"):
            clean = re.sub(r"[^\d]", "", r["price_ksh"])
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
        # Recommend: slightly below max if stock is good, else near avg
        oos_count = sum(1 for r in results if "Out of stock" in r.get("stock", ""))
        if oos_count / len(results) > 0.5:
            rec = price_stats["avg"]
            just = "Market shows frequent stockouts—price at average to ensure competitiveness without underselling."
        else:
            rec = price_stats["max"] - 500 if price_stats["max"] > 5000 else price_stats["max"]
            just = f"Most retailers are in stock. Price just below the market high (KSh {price_stats['max']:,}) to attract value-conscious buyers while maintaining margin."

        price_stats["rec"] = rec
        price_stats["justification"] = just

        # Build 2-sentence summary
        low = f"KSh {price_stats['min']:,}"
        high = f"KSh {price_stats['max']:,}"
        stock_note = "Most listings are in stock." if oos_count == 0 else (
            "Several retailers are out of stock." if oos_count > len(results) // 2 else "Stock is generally available."
        )
        summary_parts.append(f"Kenyan prices for the {phone} range from {low} to {high}. {stock_note}")
    else:
        summary_parts.append(f"No clear pricing data found for {phone} in Kenya yet.")

    # Auto-recommend persona & tone (simple heuristic)
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


def searx_all_results(phone: str) -> list[dict]:
    global LAST_CALL
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        wait = RATE_LIMIT - (time.time() - LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        LAST_CALL = time.time()

        query = f'"{phone}" price Kenya'
        try:
            r = requests.get(
                SEARX_URL,
                params={
                    "q": query,
                    "format": "json",
                    "language": "en",
                    "safesearch": "0",
                },
                headers=HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            raw = r.json().get("results", [])
            enriched = []
            for i, res in enumerate(raw, 1):
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
                if any(w in text_lower for w in ["out of stock", "sold out", "unavailable", "not in stock"]):
                    stock = "❌ Out of stock"
                elif any(w in text_lower for w in ["limited stock", "few left", "ending soon", "flash sale", "hurry"]):
                    stock = "⚠️ Limited stock"

                enriched.append({
                    "position": i,
                    "title": title[:180],
                    "url": url,
                    "content": content[:300],
                    "price_ksh": price,
                    "stock": stock,
                })
            return enriched[:60]
        except Exception as e:
            if attempt < max_retries:
                st.warning(f"⚠️ SearX attempt {attempt}/3 failed. Retrying in {2**attempt}s...")
                time.sleep(2**attempt)
            else:
                st.error(f"❌ SearX failed after {max_retries} attempts. Is the server down?")
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
    pre, rest = parts[0], parts[1]
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


def generate_marketing(phone: str, web_context: str, persona: str, tone: str) -> tuple:
    prompt = f"""You are the official marketing AI for **Tripple K Communications** (www.tripplek.co.ke).

BRAND:
- CTA: "Shop now at Tripple K Communications" or "Visit tripplek.co.ke"
- Default tone if unspecified: Playful

INPUT:
PHONE: {phone}
TARGET PERSONA: {persona}
TONE: {tone}

WEB CONTEXT (real Kenyan retailer snippets):
{web_context}

TASK — Return EXACTLY these 4 sections:
---PRICE---
---SPECS---
---INSIGHTS---
---COPY---

1. PRICE: "Retailer - KSh X,XXX - URL" for each priced result.

2. SPECS: Up to 10 specs inferred from context (battery, RAM, camera, etc.)

3. INSIGHTS: 
   - What retailers emphasize?
   - Price/stock trends?
   - Opportunities for Tripple K?
   - Keep as clear lines or short paragraphs.

4. COPY (must use real  price, specs, stock, tone, persona):
   - BANNERS: 2 lines (≤40 chars), include store name
   - TIKTOK: 1 short, engaging line (<100 chars)
   - IG / FB: Slightly longer, benefit-driven
   - HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE + model tag

RULES: Plain text only. No markdown.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            timeout=50,
            max_tokens=2400,
        )
        raw = completion.choices[0].message.content.strip()
        return parse_groq_response(raw)
    except Exception as e:
        st.error(f"🤖 Groq error: {e}")
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
                   index=0)  # Playful is default

if st.button("🚀 Generate Tripple K Marketing Kit", type="primary"):
    fetch_date = datetime.now().strftime("%d %b %Y at %H:%M EAT")

    with st.status("🔍 Generating Tripple K Ad Kit...", expanded=True) as status:
        st.write("🌐 Fetching Kenyan offers (up to 60 results)...")
        web_results = searx_all_results(phone)
        if not web_results:
            st.error("🛑 No data retrieved. Aborting.")
            st.stop()

        # Generate summary & price recommendation
        insights_summary, price_recommendation, stats = recommend_price_and_summary(phone, web_results)
        web_context = build_groq_context(web_results)

        st.write("🧠 Creating copy, specs & insights...")
        price_block, specs_block, insights_block, copy_block = generate_marketing(
            phone, web_context, persona, tone
        )
        status.update(label="✅ Tripple K Kit Ready!", state="complete", expanded=False)

    # ------- PHONE NAME + SUMMARY -------
    st.markdown(f"## {phone}")
    st.markdown(insights_summary)
    if price_recommendation:
        with st.expander("💰 Price Strategy"):
            st.markdown(price_recommendation)
            st.caption(stats["justification"])
            if stats["min"] and stats["max"]:
                st.markdown(f"📊 **Range**: KSh {stats['min']:,} – KSh {stats['max']:,} | **Avg**: KSh {stats['avg']:,}")

    # ------- PRICE TABLE -------
    st.subheader("🛒 Verified Kenyan Prices")
    price_lines = [line.strip() for line in price_block.splitlines() if line.strip()]
    if price_lines:
        rows = []
        for i, line in enumerate(price_lines):
            parts = line.split(" - ")
            if len(parts) >= 3:
                retailer = parts[0]
                price = parts[1]
                url = " - ".join(parts[2:])
                stock = web_results[i].get("stock", "✅ In stock") if i < len(web_results) else "✅ In stock"
                rows.append({"Retailer": retailer, "Price (KSh)": price, "Link": url, "Stock": stock})
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No KSh prices found.")

    # ------- SPECS -------
    st.subheader("📱 Key Specs")
    st.text(specs_block or "Not extracted from sources.")

    # ------- INSIGHTS -------
    with st.expander("📈 Strategic Market Insights"):
        if insights_block:
            for line in insights_block.splitlines():
                if line.strip():
                    st.markdown(f"- {line.strip()}")
        else:
            st.text("None generated.")

    # ------- COPY -------
    st.subheader("📣 Ready-to-Use Copy")
    lines = [l.strip() for l in copy_block.splitlines() if l.strip()]
    banners = []
    social = {"TikTok": "", "IG": "", "FB": ""}
    hashtags = ""

    # Robust parsing
    current_block = None
    for line in lines:
        if line.startswith("BANNERS:"):
            current_block = "banner"
        elif line.startswith("TikTok:"):
            social["TikTok"] = line.replace("TikTok:", "").strip()
            current_block = "tiktok"
        elif line.startswith("IG:"):
            social["IG"] = line.replace("IG:", "").strip()
            current_block = "ig"
        elif line.startswith("FB:"):
            social["FB"] = line.replace("FB:", "").strip()
            current_block = "fb"
        elif line.startswith("#"):
            hashtags = line
            break
        elif current_block == "banner" and len(banners) < 2:
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
        st.text_input("Hashtags", hashtags.strip())

    st.divider()
    st.caption(f"Generated for **Tripple K Communications** | [www.tripplek.co.ke](https://www.tripplek.co.ke) | Data: {fetch_date} EAT")