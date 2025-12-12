#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
import json
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict
from groq import Groq

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("❌ Add `groq_key` to `.streamlit/secrets.toml`")
    st.stop()

client = Groq(api_key=GROQ_KEY)

# Reliable SearXNG instances (prioritized for Kenya)
SEARX_INSTANCES = [
    "https://searx.be/search",
    "https://search.ononoki.org/search", 
    "https://searxng.site/search",
    "https://searxng-587s.onrender.com/search"
]

MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RATE_LIMIT = 2.0  # Per instance
TRIPPLEK_PHONE = "+254700123456"

# Branding
BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"

# Seasonal hook
now = datetime.now()
is_christmas = (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 10)
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
        padding: 0.75rem 1.5rem;
        font-size: 16px;
    }}
    .stButton>button:hover {{
        background-color: #5a0000;
        transform: scale(1.05);
    }}
    h1, h2, h3 {{
        color: {BRAND_MAROON} !important;
    }}
    .dataframe thead th {{
        background-color: {BRAND_GREEN} !important;
        color: white !important;
        font-size: 14px;
    }}
    .dataframe {{
        font-size: 13px !important;
    }}
    .main {{
        background-color: {BACKGROUND_LIGHT};
    }}
    @media (max-width: 768px) {{
        .stTextArea textarea, .stCodeBlock {{
            font-size: 14px !important;
        }}
        [data-testid="column"] {{
            width: 100% !important;
        }}
        [data-testid="dataframe"] {{
            font-size: 12px !important;
        }}
        .dataframe td {{
            padding: 4px !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

def extract_retailer(url: str) -> str:
    """Extract retailer name from URL"""
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    return domain.split(".")[0]

def extract_price(full_text: str) -> str:
    """Improved price extraction for Kenyan formats"""
    # KSh25,000 | 25,000 KSh | KES 25.000 | Sh25K etc
    patterns = [
        r'(?:ksh?|kes?|sh\.?|shillings?)?\s*[:\-]?\s*([\d,\.]+(?:\d{3})*)',
        r'([\d,\.]+)\s*(?:ksh?|kes?|sh\.?)',
        r'(?:ksh?|kes?)\s*(\d{1,3}(?:[,\.]\d{3})*)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            price = re.sub(r'[^\d]', '', match.group(1))
            if price.isdigit() and int(price) > 1000:
                return f"KSh {int(price):,}"
    return None

def fetch_kenyan_prices(phone: str) -> list[dict]:
    """Fetch prices with per-instance rate limiting + failover"""
    instance_times = defaultdict(float)
    all_results = []
    
    for instance in SEARX_INSTANCES:
        # Per-instance rate limiting
        wait = RATE_LIMIT - (time.time() - instance_times[instance])
        if wait > 0:
            time.sleep(wait)
        instance_times[instance] = time.time()
        
        try:
            r = requests.get(
                instance,
                params={
                    "q": f'"{phone}" price Kenya OR KSh OR jumia OR kilimall',
                    "format": "json",
                    "language": "en",
                    "safesearch": "0"
                },
                headers=HEADERS,
                timeout=12
            )
            
            if r.status_code == 200:
                results = r.json().get("results", [])[:50]
                enriched = []
                
                for res in results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    url = res.get("url", "")
                    full_text = f"{title} {content} {url}".lower()
                    
                    price = extract_price(full_text)
                    stock = "✅ In stock"
                    
                    if any(w in full_text for w in ["out of stock", "sold out", "unavailable"]):
                        stock = "❌ Out of stock"
                    elif any(w in full_text for w in ["limited stock", "few left", "last"]):
                        stock = "⚠️ Limited"
                    
                    enriched.append({
                        "title": title,
                        "url": url,
                        "content": content[:200] + "...",
                        "price_ksh": price,
                        "stock": stock,
                        "retailer": extract_retailer(url)
                    })
                
                all_results.extend(enriched)
                return enriched
                
        except Exception:
            continue
    
    return all_results[:100]  # Fallback results

def generate_marketing_kit(phone: str, results: list[dict], persona: str, tone: str) -> dict:
    """Generate kit using structured JSON output"""
    
    # Prepare market context
    context = []
    for r in results:
        price = f" | {r['price_ksh']}" if r['price_ksh'] else ""
        context.append({
            "title": r['title'],
            "url": r['url'],
            "price": r['price_ksh'],
            "stock": r['stock'],
            "retailer": r['retailer']
        })
    
    json_schema = {
        "type": "object",
        "properties": {
            "prices": {"type": "array", "items": {"type": "string"}},
            "specs": {"type": "array", "items": {"type": "string"}},
            "insights": {"type": "array", "items": {"type": "string"}},
            "banners": {"type": "array", "items": {"type": "string", "maxItems": 2}},
            "tiktok": {"type": "string"},
            "instagram": {"type": "string"},
            "facebook": {"type": "string"},
            "whatsapp": {"type": "string"},
            "hashtags": {"type": "string"}
        },
        "required": ["prices", "specs", "banners", "whatsapp"]
    }
    
    prompt = f"""Tripple K Communications (tripplek.co.ke) - Kenya's trusted phone distributor.

PHONE: {phone}
PERSONA: {persona}
TONE: {tone}
VALUES: Genuine phones | Full warranty | Pay on delivery | Fast Nairobi delivery
{ "CHRISTMAS GIFT with warranty!" if is_christmas else ""}

MARKET DATA ({len(results)} listings):
{json.dumps(context, indent=2)}

Respond ONLY with valid JSON matching this schema: {json.dumps(json_schema['properties'])}
Generate:
- prices: ["Jumia - KSh 25,000 - URL", ...]
- specs: 5-8 key specs (one per line)
- insights: 3 market insights
- banners: 2 short lines (Tripple K branding)
- tiktok: 1 fun line <100 chars
- instagram: 2-3 sentences
- facebook: Like Instagram
- whatsapp: Include {TRIPPLEK_PHONE}
- hashtags: #TrippleK #PhoneDealsKE etc

Use ONLY real data from MARKET DATA above."""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        return json.loads(completion.choices[0].message.content)
        
    except Exception as e:
        return {"error": str(e)}

############################ STREAMLIT UI ####################################
inject_brand_css()
st.title("🚀 Tripple K Phone Ad Generator")
st.caption("✅ Data-Driven | Mobile-First | Production Ready")

if is_christmas:
    st.info("🎄 CHRISTMAS MODE: Festive copy + gift messaging!")

phone = st.text_input("📱 Phone model", value="Samsung Galaxy A17", 
                     placeholder="Xiaomi Poco X6 Pro, iPhone 16 etc")
persona = st.selectbox("👤 Target", 
    ["All Kenyan buyers", "Budget students", "Tech pros", "Camera lovers", "Business"], 0)
tone = st.selectbox("🎭 Tone", ["Playful", "Rational", "Luxury", "Urgent"], 0)

if st.button("🚀 Generate Marketing Kit", type="primary"):
    with st.spinner("🔍 Fetching Kenya prices..."):
        results = fetch_kenyan_prices(phone)
        
        if not results:
            st.error("❌ No search results. Try: 'Samsung A17', 'iPhone 16 Pro'")
            st.stop()
    
    with st.spinner("🤖 Building ad kit..."):
        kit = generate_marketing_kit(phone, results, persona, tone)
        
        if "error" in kit:
            st.error(f"AI Error: {kit['error']}")
            st.stop()

    # Price Analysis
    prices = [int(re.sub(r'[^\d]', '', p)) for r in results if (r['price_ksh'] and r['price_ksh'].isdigit())]
    if prices:
        min_p, max_p, avg_p = min(prices), max(prices), round(sum(prices)/len(prices))
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("💰 Lowest", f"KSh {min_p:,}")
        with col2: st.metric("📊 Average", f"KSh {avg_p:,}")
        with col3: st.metric("🔥 Highest", f"KSh {max_p:,}")
        
        rec_price = max_p - 800 if max_p > 10000 else max_p
        st.success(f"✅ **Tripple K Price:** KSh {rec_price:,}")

    # Market Prices Table - FIXED
    if kit.get("prices"):
        st.subheader("🏪 Market Prices")
        table_data = []
        for line in kit["prices"][:15]:
            parts = re.split(r'\s*-\s*', line.strip(), maxsplit=2)
            if len(parts) >= 2:
                retailer = extract_retailer(parts[-1]) if len(parts) > 2 else "Online"
                price_text = parts[1] if len(parts) > 1 else ""
                link_url = parts[-1] if len(parts) > 2 else line
                
                table_data.append({
                    "Retailer": retailer,
                    "Price": price_text,
                    "Stock": "✅",
                    "🔗": link_url  # Simple column name
                })
        
        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "🔗": st.column_config.LinkColumn("Visit")
            },
            hide_index=True
        )

    # Key Specs
    if kit.get("specs"):
        st.subheader("📋 Key Specs")
        for spec in kit["specs"][:10]:
            st.markdown(f"• {spec}")

    # Insights
    if kit.get("insights"):
        with st.expander("💡 Market Insights", expanded=True):
            for insight in kit["insights"]:
                st.markdown(f"- {insight}")

    # Social Copy
    st.subheader("📱 Ready-to-Post Copy")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🏷️ Banners**")
        for i, banner in enumerate(kit.get("banners", [])[:2]):
            st.code(banner, language=None)
    
    with c2:
        st.markdown("**📲 Social**")
        st.text_area("TikTok", kit.get("tiktok", ""), height=50, label_visibility="collapsed")
        st.text_area("Instagram", kit.get("instagram", ""), height=70, label_visibility="collapsed")
        st.text_area("Facebook", kit.get("facebook", ""), height=70, label_visibility="collapsed")
        st.text_area("WhatsApp", kit.get("whatsapp", f"📱 {phone}\nCall {TRIPPLEK_PHONE}"), 
                    height=90, label_visibility="collapsed")
    
    st.caption(f"Generated {datetime.now().strftime('%d/%m %H:%M EAT')} | **Tripple K Communications**")
