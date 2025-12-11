#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
PEXELS_KEY = st.secrets.get("pexels_api_key", "")
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
    </style>
    """, unsafe_allow_html=True)


def searx_all_results(phone: str) -> list[dict]:
    global LAST_CALL
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

            # Stock detection
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
        return enriched[:25]
    except Exception as e:
        st.warning(f"⚠️ SearX error: {str(e)[:60]}")
        return []


def enrich_stock_summary(results: list[dict]) -> str:
    oos = sum(1 for r in results if "Out of stock" in r.get("stock", ""))
    limited = sum(1 for r in results if "Limited stock" in r.get("stock", ""))
    if oos > 0:
        return f"❗ {oos} retailer(s) show OUT OF STOCK"
    elif limited > 0:
        return f"⏳ {limited} retailer(s) show LIMITED STOCK"
    return ""


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
    prompt = f"""You are the official marketing AI for **Tripple K Communications** (www.tripplek.co.ke), a top Kenyan tech store.

BRAND IDENTITY:
- Colors: **Mint Green (#E8F5E9 background) + Maroon (#8B0000 accents)**
- Style: **Clean, professional, product-focused flyers — NO PEOPLE**
- CTA: Always include **"Shop now at Tripple K Communications"** or **"Visit tripplek.co.ke"**

PHONE: {phone}
TARGET: {persona}
TONE: {tone}

WEB RESULTS:
{web_context}

INSTRUCTIONS — Return EXACTLY these 4 sections, separated by:
---PRICE---
---SPECS---
---INSIGHTS---
---COPY---

1. PRICE:
   - For EVERY result with visible KSh price, output:
     "Retailer - KSh X,XXX - https://..."
   - Extract retailer from domain (e.g., jumia.co.ke → Jumia)
   - NO LIMIT — list all verified prices.

2. SPECS:
   - Infer up to 10 key specs from web results. Arrange them from most desirable

3. INSIGHTS:
   - Selling Points, Tactics, Competitive Edge, Market Gap.

4. COPY:
   - BANNERS: 2 lines (≤40 chars), include store name
   - SOCIAL: Tweet, IG, FB — mention tripplek.co.ke
   - HASHTAGS: Include #TrippleK #TrippleKKE #PhoneDealsKE

RULES: Plain text only. No markdown. Be precise.
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

phone = st.text_input("🔍 Phone model (e.g., Tecno Spark 20)", value="Samsung Galaxy A17")
persona = st.selectbox("👤 Buyer Persona", 
                      ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Status execs"], 
                      index=0)
tone = st.selectbox("🎨 Brand Tone", 
                   ["Rational", "Playful", "Luxury", "FOMO"], 
                   index=0)

if st.button("🚀 Generate Tripple K Marketing Kit", type="primary"):
    fetch_date = datetime.now().strftime("%d %b %Y at %H:%M EAT")

    with st.status("🔍 Generating Tripple K Ad Kit...", expanded=True) as status:
        st.write("🌐 Fetching Kenyan offers...")
        web_results = searx_all_results(phone)
        stock_note = enrich_stock_summary(web_results)
        web_context = build_groq_context(web_results)

        st.write("🧠 Creating copy, specs & insights...")
        price_block, specs_block, insights_block, copy_block = generate_marketing(
            phone, web_context, persona, tone
        )
        status.update(label="✅ Tripple K Kit Ready!", state="complete", expanded=False)

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

    if stock_note:
        st.warning(stock_note)

    # ------- SPECS -------
    st.subheader("📱 Key Specs")
    st.text(specs_block or "Not extracted from sources.")

    # ------- INSIGHTS -------
    with st.expander("📈 Strategic Market Insights"):
        st.text(insights_block or "None generated.")

    # ------- COPY -------
    st.subheader("📣 Ready-to-Use Copy")
    lines = [l.strip() for l in copy_block.splitlines() if l.strip()]
    banners = []
    social = {"Tweet": "", "IG": "", "FB": ""}
    hashtags = ""
    for line in lines:
        if line.startswith("BANNERS:"):
            continue
        elif line.startswith("#"):
            hashtags = line
            break
        elif "Tweet:" in line or (not any(x in line for x in ["IG:", "FB:", "BANNERS:"]) and len(banners) < 2):
            banners.append(line)
        elif "IG:" in line:
            social["IG"] = line.replace("IG:", "").strip()
        elif "FB:" in line:
            social["FB"] = line.replace("FB:", "").strip()
        elif not banners and not any(x in line for x in ["IG:", "FB:"]):
            banners.append(line)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**🖼️ Banner Text**")
        for b in banners[:2]:
            st.code(b, language="plaintext")
    with c4:
        st.markdown("**📲 Social Posts**")
        st.text_area("Twitter", social["Tweet"], height=70)
        st.text_area("Instagram", social["IG"], height=70)
        st.text_area("Facebook", social["FB"], height=70)
        st.text_input("Hashtags", hashtags)

    # ------- FOOTER -------
    st.divider()
    st.caption(f"Generated for **Tripple K Communications** | [www.tripplek.co.ke](https://www.tripplek.co.ke) | Data: {fetch_date} EAT")