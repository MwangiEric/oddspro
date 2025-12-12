#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
import math

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("Add groq_key to .streamlit/secrets.toml")
    st.stop()

from groq import Groq
client = Groq(api_key=GROQ_KEY)

# *** CHANGE IMPLEMENTED HERE ***
# Only use the requested SearXNG instance
SEARX_INSTANCES = [
    "https://searxng-587s.onrender.com/",
]

MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RATE_LIMIT = 3
LAST_CALL = 0

BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
TRIPPLEK_PHONE = "+254700123456"

now = datetime.now()
is_christmas = (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 10)
CHRISTMAS_HOOK = "Perfect Christmas gift with warranty & fast delivery!" if is_christmas else ""
CURRENT_YEAR = f'{now.year:04d}'
CURRENT_MONTH = f'{now.month:02d}'
####################################################################


# Initialize session state for multi-stage workflow
if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'kit' not in st.session_state:
    st.session_state['kit'] = None
if 'phone' not in st.session_state:
    st.session_state['phone'] = ""


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
    }}
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def warm_up_searx():
    """Ping all SearXNG instances on startup (now just the single one)."""
    def ping_instance(url):
        try:
            r = requests.get(url, params={"q": "test", "format": "json"}, timeout=8)
            return url if r.status_code == 200 else None
        except:
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = list(executor.map(ping_instance, SEARX_INSTANCES))
    
    online = [r for r in results if r]
    # Return the single instance if it is online, otherwise an empty list
    return online


def extract_retailer(url: str) -> str:
    """Extracts a clean retailer name from a URL."""
    if not url:
        return "Unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    retailer = domain.split(".")[0]
    return retailer.capitalize() if retailer else "Unknown"


def extract_slug_from_url(url: str) -> str:
    clean = url.split("?", 1)[0].split("#", 1)[0]
    parts = [p for p in clean.split("/") if p]
    return parts[-1].lower() if parts else ""


def predict_image_url(phone: str, url: str) -> str:
    """Uses Groq to predict likely product image URL with dynamic date."""
    slug = extract_slug_from_url(url)
    
    prompt = f"""Product: {phone}
URL: {url}
Slug: {slug}

Most Kenyan e-commerce sites use WooCommerce. Predict the direct image URL.
Common patterns:
/wp-content/uploads/{CURRENT_YEAR}/{CURRENT_MONTH}/{slug}.jpg
/wp-content/uploads/{CURRENT_YEAR}/{CURRENT_MONTH}/{slug}-1024x1024.jpg

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
    
    if not online_instances:
        st.error(f"The search API instance ({SEARX_INSTANCES[0]}) is currently unavailable. Please try again later.")
        return []

    # Since there's only one instance, the loop runs exactly once.
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
                raw_results = r.json().get("results", [])
                
                # SMART FILTER: Prioritize TLDs and known Kenyan retailers
                kenyan_indicators = ['.ke', 'jumia.co.ke', 'kilimall.co.ke', 'tripplek.co.ke', 'phoneplacekenya.com', 'masoko.com'] 
                
                filtered_results = []
                for res in raw_results:
                    url = res.get("url", "").lower()
                    # Filter for Kenyan URLs
                    if any(indicator in url for indicator in kenyan_indicators):
                        filtered_results.append(res)
                
                results = filtered_results[:60]
                
                enriched = []
                for res in results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    url = res.get("url", "")
                    
                    search_text = f"{title} {content}".lower() 
                    
                    price_match = re.search(
                        r'(?:ksh?|kes|shillings?|k\.sh\.)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)',
                        search_text,
                        re.IGNORECASE
                    )
                    
                    price_str = None
                    price_int = 0
                    if price_match:
                        clean_price = re.sub(r"[^\d]", "", price_match.group(1))
                        if clean_price.isdigit():
                            price_int = int(clean_price)
                            price_str = f"KSh {price_int:,}" 
                    
                    stock = "In stock"
                    if any(w in search_text for w in ["out of stock", "sold out", "unavailable"]):
                        stock = "Out of stock"
                    elif any(w in search_text for w in ["limited stock", "few left", "hurry"]):
                        stock = "Limited stock"
                    
                    enriched.append({
                        "title": title[:180],
                        "url": url,
                        "content": content[:300],
                        "price_ksh_str": price_str,
                        "price_ksh_int": price_int,
                        "stock": stock,
                        "retailer": extract_retailer(url)
                    })
                
                return enriched
                
        except Exception as e:
            # Report the failure for the only instance
            st.error(f"Search failed for {instance}. Error: {e}")
            return []
    
    return []


def generate_with_data(phone: str, results: list[dict], persona: str, tone: str) -> dict:
    context_lines = []
    for r in results:
        price = f" | {r['price_ksh_str']}" if r["price_ksh_str"] else ""
        context_lines.append(
            f"Retailer: {r.get('retailer', 'Unknown')}\n"
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

MARKET DATA (Use this for facts, specs, and price comparison):
{web_context}

OUTPUT EXACTLY 4 SECTIONS, each starting with the required marker:

---PRICE---
List: "Retailer - KSh X,XXX - URL" for each price result. Include the retailer name from the context. (DO NOT INCLUDE YOUR OWN RECOMMENDED PRICE HERE)

---SPECS---
5-10 key specs from data or general knowledge

---INSIGHTS---
3-5 bullet points on market trends, what makes this phone compelling for the PERSONA.

---COPY---
BANNERS: 2 lines, max 40 chars, include "Tripple K"
TIKTOK: 1 fun line <100 chars, use emoji for Playful tone
IG: 2-3 sentences highlighting benefits and value props
FB: Similar to IG
WHATSAPP: Include {TRIPPLEK_PHONE}, mention warranty, pay on delivery, {CHRISTMAS_HOOK if CHRISTMAS_HOOK else ""}
HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only. Use real data."""

    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5, 
            max_tokens=2400,
            timeout=50
        )
        
        raw = comp.choices[0].message.content.strip()
        
        parts = raw.split("---PRICE---")
        if len(parts) < 2:
            return {"error": f"Invalid format from AI. Missing ---PRICE--- marker in output: \n{raw[:500]}..."}
        
        rest = parts[1]
        price_block = rest.split("---SPECS---")[0].strip() if "---SPECS---" in rest else ""
        
        rest = rest.split("---SPECS---", 1)[1] if "---SPECS---" in rest else ""
        specs_block = rest.split("---INSIGHTS---")[0].strip() if "---INSIGHTS---" in rest else ""
        
        rest = rest.split("---INSIGHTS---", 1)[1] if "---INSIGHTS---" in rest else ""
        insights_block = rest.split("---COPY---")[0].strip() if "---INSIGHTS---" in rest else ""
        
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

OUTPUT EXACTLY 2 SECTIONS, each starting with the required marker:

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
            specs_block = parts.split("---COPY---")[0].strip() if "---COPY---" in parts else parts.strip()
            copy_block = parts.split("---COPY---", 1)[1].strip() if "---COPY---" in parts else ""
        
        return {
            "prices": "",
            "specs": specs_block,
            "insights": "",
            "copy": copy_block
        }
        
    except Exception as e:
        return {"error": str(e)}


def render_price_table(results: list[dict]):
    """Renders the price comparison table with Tripple K's recommended price using st.dataframe."""
    
    rows = []
    prices_numeric_for_calc = [r["price_ksh_int"] for r in results if r["price_ksh_int"] > 0]
    
    # 1. Add competitor listings (only those with a price)
    for r in results:
        if r["price_ksh_int"] > 0:
            rows.append({
                "Price": r["price_ksh_str"],
                "Retailer": r["retailer"],
                "Link": r["url"],
                "Stock": r["stock"],
                "price_val": r["price_ksh_int"],
                "is_rec": False
            })

    # 2. Calculate and add recommended price
    rec_price = 0
    if prices_numeric_for_calc:
        price_series = pd.Series(prices_numeric_for_calc)
        
        rec_price_base = price_series.quantile(0.75)
        rec_price = int(round((rec_price_base - 500) / 100) * 100)
        
        min_comp_price = price_series.min()
        if rec_price < min_comp_price * 0.90: 
            rec_price = int(round((min_comp_price - 100) / 100) * 100)
        
        rows.append({
            "Price": f"KSh {rec_price:,}",
            "Retailer": "Tripple K (Recommended)",
            "Link": "https://www.tripplek.co.ke",
            "Stock": "Available",
            "price_val": rec_price,
            "is_rec": True
        })
    
    # 3. Sort and create DataFrame
    rows.sort(key=lambda x: x["price_val"], reverse=True)
    
    # Prepare data for st.dataframe
    df = pd.DataFrame([{
        "Price": r["Price"],
        "Retailer": r["Retailer"],
        "Stock": r["Stock"],
        # Use Markdown links in a helper column for a clickable link in the dataframe
        "Link": f"[View Link]({r['Link']})" if r['Link'].startswith('http') else "N/A"
    } for r in rows])

    # 4. Render
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


def parse_and_render_copy(copy_block: str, phone: str):
    """Parses the copy block robustly and renders the UI sections."""
    
    markers = ["BANNERS:", "TIKTOK:", "IG:", "FB:", "WHATSAPP:", "HASHTAGS:"]
    social_data = {}
    banners = []
    hashtags = ""
    
    parts = re.split(f'({"|".join(markers)})', copy_block, flags=re.IGNORECASE)
    
    for i in range(1, len(parts), 2):
        marker = parts[i].upper().strip(':')
        content = parts[i+1].strip()
        
        if marker == "BANNERS":
            banners = [l.strip() for l in content.splitlines() if l.strip()][:2]
        elif marker == "HASHTAGS":
            hashtags = content.splitlines()[-1].strip() if content else ""
        elif marker in ("TIKTOK", "IG", "FB", "WHATSAPP"):
            key = marker.capitalize() if marker != "WHATSAPP" else "WhatsApp"
            social_data[key] = content

    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Banner Text**")
        if banners:
            for b in banners:
                st.code(b, language="text")
        else:
            st.caption("No banner text generated.")
    
    with c2:
        st.markdown("**Social Media Copy**")
        st.text_area("TikTok", social_data.get("TikTok", ""), height=60, key="tt")
        st.text_area("Instagram", social_data.get("IG", ""), height=70, key="ig")
        st.text_area("Facebook", social_data.get("FB", ""), height=70, key="fb")
        st.text_area("WhatsApp", social_data.get("WhatsApp", f"Get {phone} at Tripple K! {TRIPPLEK_PHONE}"), height=100, key="wa")
        st.text_input("Hashtags", hashtags)


############################ STREAMLIT UI ####################################
inject_brand_css()

# Sidebar
with st.sidebar:
    st.title("Settings")
    # Toggling web data is still useful for generic copy flow
    use_web_data = st.toggle("Use live web data", value=True, help="Search Kenyan retailers for prices before generating copy.")
    
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

phone_input = st.text_input("Phone model", placeholder="e.g., Samsung Galaxy A17")

# --- STAGE 1: SEARCH ---
if st.button("Search Kenyan Prices", type="primary"):
    if not phone_input:
        st.error("Please enter a phone model")
    else:
        st.session_state['phone'] = phone_input
        st.session_state['kit'] = None # Clear previous kit
        
        with st.status("Searching Kenyan retailers...", expanded=True) as status:
            if use_web_data:
                results = fetch_kenyan_prices(phone_input)
                
                if not results:
                    st.warning("No relevant Kenyan web data found or search API is down. Proceed with generic copy if needed.")
                else:
                    st.write(f"Found {len(results)} relevant Kenyan listings")
            else:
                results = []
                st.info("Web data search skipped by user setting.")

            st.session_state['results'] = results
            status.update(label="Search Complete!", state="complete", expanded=False)
            
            st.rerun() 


# Display results if available
if st.session_state['results'] or st.session_state['kit']:
    phone = st.session_state.get('phone', phone_input)
    st.markdown(f"## {phone} - Market Analysis")
    
    prices_numeric = [r["price_ksh_int"] for r in st.session_state['results'] if r["price_ksh_int"] > 0]
    
    if st.session_state['results']:
        # Summary
        if prices_numeric:
            min_p, max_p = min(prices_numeric), max(prices_numeric)
            oos_count = sum(1 for r in st.session_state['results'] if "out" in r["stock"].lower())
            stock_note = "Most listings are in stock." if oos_count == 0 else "Some retailers are out of stock."
            
            st.info(f"**Market Price Range:** KSh {min_p:,} to KSh {max_p:,}. {stock_note}")
        
        # Price Table
        st.subheader("Competitor Price Comparison")
        render_price_table(st.session_state['results'])
    
    
    # --- STAGE 2: GENERATE COPY ---
    st.subheader("Generate Ad Copy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Data-Driven Copy", type="primary", disabled=not bool(prices_numeric)):
            with st.status("Generating copy with market data...", expanded=False):
                kit = generate_with_data(phone, st.session_state['results'], persona, tone)
                if "error" in kit:
                    st.error(f"AI error: {kit['error']}")
                else:
                    st.session_state['kit'] = kit
                    st.success("Copy Generation Complete!")
            st.rerun()

    with col2:
        if st.button("Generate Generic Copy"):
            with st.status("Generating generic copy...", expanded=False):
                kit = generate_without_data(phone, persona, tone)
                if "error" in kit:
                    st.error(f"AI error: {kit['error']}")
                else:
                    st.session_state['kit'] = kit
                    st.success("Copy Generation Complete!")
            st.rerun()

# --- DISPLAY FINAL KIT ---
if st.session_state['kit']:
    kit = st.session_state['kit']
    st.markdown("---")
    st.markdown(f"## Marketing Kit for {st.session_state['phone']}")
    
    # Specs
    if kit.get("specs"):
        st.subheader("Key Specs")
        st.text(kit["specs"])
    
    # Insights (Only available with data)
    if kit.get("insights") and st.session_state['results']:
        with st.expander("Strategic Market Insights"):
            for line in kit["insights"].splitlines():
                if line.strip():
                    st.markdown(f"* {line.strip()}")
    
    # Ad Copy
    if kit.get("copy"):
        st.subheader("Ready-to-Use Ad Copy")
        parse_and_render_copy(kit["copy"], st.session_state['phone'])

    # Product images (Only available with data)
    if st.session_state['results']:
        st.subheader("Product Images (Preview)")
        with st.spinner("Checking retailer sites..."):
            valid_images = []
            for r in st.session_state['results'][:5]:
                if "tripplek" not in r["url"].lower():
                    img_url = predict_image_url(st.session_state['phone'], r["url"])
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
    
    st.divider()
    st.caption(f"Generated {datetime.now().strftime('%d %b %Y %H:%M EAT')} | Tripple K Communications | tripplek.co.ke")
