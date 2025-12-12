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
    st.error("âŒ Add `groq_key` to `.streamlit/secrets.toml`")
    st.stop()

from groq import Groq
client = Groq(api_key=GROQ_KEY)

# Multiple SearXNG instances for failover
SEARX_INSTANCES = [
    "https://searx.be/search",
    "https://search.ononoki.org/search",
    "https://searxng.site/search",
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
    @media (max-width: 768px) {{
        .stTextArea textarea, .stCodeBlock {{
            font-size: 14px !important;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        [data-testid="column"] {{
            width: 100% !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def extract_retailer(url: str) -> str:
    """Extract retailer name from URL (e.g., jumia.co.ke -> jumia)"""
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    return domain.split(".")[0]


def fetch_kenyan_prices(phone: str) -> list[dict]:
    """Fetch prices from multiple SearXNG instances with failover"""
    global LAST_CALL
    
    for instance in SEARX_INSTANCES:
        # Rate limit
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
                timeout=15
            )
            
            if r.status_code == 200:
                results = r.json().get("results", [])[:60]
                
                enriched = []
                for res in results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    url = res.get("url", "")
                    full_text = f"{title} {content} {url}".lower()
                    
                    # Extract price
                    price_match = re.search(
                        r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)',
                        full_text,
                        re.IGNORECASE
                    )
                    price = f"KSh {price_match.group(1)}" if price_match else None
                    
                    # Detect stock status
                    stock = "âœ… In stock"
                    if any(w in full_text for w in ["out of stock", "sold out", "unavailable"]):
                        stock = "âŒ Out of stock"
                    elif any(w in full_text for w in ["limited stock", "few left", "hurry"]):
                        stock = "âš ï¸ Limited stock"
                    
                    enriched.append({
                        "title": title[:180],
                        "url": url,
                        "content": content[:300],
                        "price_ksh": price,
                        "stock": stock
                    })
                
                return enriched
                
        except Exception as e:
            st.warning(f"âš ï¸ Trying backup search engine...")
            continue
    
    return []  # All instances failed


def generate_marketing_kit(phone: str, results: list[dict], persona: str, tone: str) -> dict:
    """Generate complete marketing kit using Groq"""
    
    # Build context from results
    context_lines = []
    for r in results:
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        context_lines.append(
            f"Title: {r['title']}{price}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {r['content']}\n"
            f"Stock: {r['stock']}\n---"
        )
    web_context = "\n".join(context_lines) if context_lines else "No market data available."
    
    # Groq prompt
    prompt = f"""You are the marketing AI for **Tripple K Communications** (www.tripplek.co.ke).

TRIPPLE K VALUE PROPS (mention 1-2):
âœ… Accredited distributor - only genuine phones
âœ… Full manufacturer warranty included
âœ… Pay on delivery available
âœ… Fast Nairobi delivery

{"ðŸŽ„ CHRISTMAS SEASON: Perfect gift with warranty & fast delivery!" if is_christmas else ""}

PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

MARKET DATA:
{web_context}

OUTPUT (4 sections separated by markers):

---PRICE---
For each result with price: "Retailer - KSh X,XXX - URL"

---SPECS---
List 5-10 key specs from data (battery, RAM, camera, storage, display)

---INSIGHTS---
3-5 short bullet points:
- What market emphasizes
- Price range & stock trends
- Why buy from Tripple K (warranty, genuine, delivery)

---COPY---
BANNERS: 2 lines, max 40 chars each, include "Tripple K"
TIKTOK: 1 line, <100 chars, fun hook with emoji if Playful
IG: 2-3 sentences, benefit-focused
FB: Similar to IG
WHATSAPP: Include phone {TRIPPLEK_PHONE}, warranty, pay on delivery
HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

RULES:
- Plain text only
- Use real data only
- Don't mention competitor names
- Focus on trust & value"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2400,
            timeout=50
        )
        
        raw = completion.choices[0].message.content.strip()
        
        # Parse sections
        parts = raw.split("---PRICE---")
        if len(parts) < 2:
            return {"error": "Invalid response format"}
        
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


############################ STREAMLIT UI ####################################
inject_brand_css()
st.title("ðŸ"± Tripple K Phone Ad Generator")
st.caption("Data-Driven Marketing Kits | www.tripplek.co.ke")

if is_christmas:
    st.info("ðŸŽ„ Christmas Special: Generate festive ads with warranty & delivery highlights!")

phone = st.text_input("ðŸ" Phone model", value="Samsung Galaxy A17", placeholder="e.g., Xiaomi Poco X6 Pro")
persona = st.selectbox("ðŸ'¤ Target Audience", 
    ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Business execs"],
    index=0)
tone = st.selectbox("ðŸŽ¨ Brand Tone", 
    ["Playful", "Rational", "Luxury", "FOMO"],
    index=0)

if st.button("ðŸš€ Generate Marketing Kit", type="primary"):
    with st.status("ðŸ" Fetching Kenyan market data...", expanded=True) as status:
        st.write("ðŸŒ Searching multiple sources...")
        results = fetch_kenyan_prices(phone)
        
        if not results:
            st.error("âŒ All search engines unavailable. Try again in 30 seconds.")
            st.stop()
        
        st.write(f"âœ… Found {len(results)} listings")
        st.write("ðŸ§  Generating marketing kit with AI...")
        
        kit = generate_marketing_kit(phone, results, persona, tone)
        
        if "error" in kit:
            st.error(f"AI error: {kit['error']}")
            st.stop()
        
        status.update(label="âœ… Marketing Kit Ready!", state="complete", expanded=False)
    
    # Display phone name
    st.markdown(f"## {phone}")
    
    # Price analysis
    prices = []
    for r in results:
        if r["price_ksh"]:
            clean = re.sub(r"[^\d]", "", r["price_ksh"])
            if clean.isdigit():
                prices.append(int(clean))
    
    if prices:
        min_p, max_p, avg_p = min(prices), max(prices), round(sum(prices)/len(prices))
        st.markdown(f"**Price Range:** KSh {min_p:,} â€" KSh {max_p:,} | **Avg:** KSh {avg_p:,}")
        rec_price = max_p - 500 if max_p > 5000 else max_p
        st.success(f"ðŸ'° **Recommended Tripple K Price:** KSh {rec_price:,}")
    
    # Price table
    st.subheader("ðŸ›' Market Prices")
    price_lines = [l.strip() for l in kit["prices"].splitlines() if l.strip()]
    if price_lines:
        rows = []
        for i, line in enumerate(price_lines):
            parts = line.split(" - ")
            if len(parts) >= 3:
                rows.append({
                    "Price": parts[1],
                    "Retailer": extract_retailer(parts[2]),
                    "Stock": results[i]["stock"] if i < len(results) else "âœ…",
                    "Link": " - ".join(parts[2:])
                })
        
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Specs
    if kit["specs"]:
        st.subheader("ðŸ"± Key Specs")
        st.text(kit["specs"])
    
    # Insights
    if kit["insights"]:
        with st.expander("ðŸ"ˆ Market Insights"):
            for line in kit["insights"].splitlines():
                if line.strip():
                    st.markdown(f"- {line.strip()}")
    
    # Copy
    st.subheader("ðŸ"£ Ready-to-Use Copy")
    
    lines = [l.strip() for l in kit["copy"].splitlines() if l.strip()]
    banners, social, hashtags = [], {}, ""
    current = None
    
    for line in lines:
        if line.startswith("BANNERS:"):
            current = "banner"
        elif "TikTok:" in line:
            social["TikTok"] = line.split(":", 1)[1].strip()
        elif "IG:" in line:
            social["IG"] = line.split(":", 1)[1].strip()
        elif "FB:" in line:
            social["FB"] = line.split(":", 1)[1].strip()
        elif "WHATSAPP:" in line or "WhatsApp:" in line:
            social["WhatsApp"] = line.split(":", 1)[1].strip()
        elif line.startswith("#"):
            hashtags = line
        elif current == "banner" and len(banners) < 2:
            banners.append(line)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**ðŸ–¼ï¸ Banner Text**")
        for b in banners[:2]:
            st.code(b, language="text")
    
    with c2:
        st.markdown("**ðŸ"² Social Media**")
        st.text_area("TikTok", social.get("TikTok", ""), height=60, key="tt")
        st.text_area("Instagram", social.get("IG", ""), height=70, key="ig")
        st.text_area("Facebook", social.get("FB", ""), height=70, key="fb")
        st.text_area("WhatsApp", social.get("WhatsApp", f"Get {phone} at Tripple K! Call {TRIPPLEK_PHONE}"), height=100, key="wa")
        st.text_input("Hashtags", hashtags)
    
    st.divider()
    st.caption(f"Generated {datetime.now().strftime('%d %b %Y %H:%M EAT')} | **Tripple K Communications** | tripplek.co.ke")
