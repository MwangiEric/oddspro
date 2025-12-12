#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures

############################ CONFIG ################################

# Robust SearXNG instances for failover. Your preferred instance is FIRST.
SEARX_INSTANCES = [
    "https://searxng-587s.onrender.com/", 
    "https://searx.be/search",
    "https://search.ononoki.org/search",
    "https://searxng.site/search",
    "https://northboot.xyz/search",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RATE_LIMIT = 0 # No rate limit

# Branding
BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
TRIPPLEK_PHONE = "+254700123456"

now = datetime.now()
CURRENT_YEAR = f'{now.year:04d}'
CURRENT_MONTH = f'{now.month:02d}'
####################################################################


# Initialize session state for workflow
if 'results' not in st.session_state:
    st.session_state['results'] = []
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
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def warm_up_searx():
    """Pings all instances to find available ones."""
    def ping_instance(url):
        try:
            r = requests.get(url, params={"q": "test", "format": "json"}, timeout=15)
            return url if r.status_code == 200 else None
        except:
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(ping_instance, SEARX_INSTANCES))
    
    online = [r for r in results if r]
    return online


def extract_retailer(url: str) -> str:
    """Extracts a clean retailer name from a URL."""
    if not url:
        return "Unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    retailer = domain.split(".")[0]
    return retailer.capitalize() if retailer else "Unknown"


def fetch_kenyan_prices(phone: str) -> list[dict]:
    
    online_instances = warm_up_searx()
    
    if not online_instances:
        st.error(f"All search API instances are currently unavailable.")
        return []

    # Try each online instance sequentially
    for instance in online_instances:
        
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
                timeout=45 # High timeout as requested
            )
            
            if r.status_code == 200:
                raw_results = r.json().get("results", [])
                
                # --- CHANGE IMPLEMENTED HERE ---
                # SMART FILTER: Only searching for 'ke' string in URL
                kenyan_indicators = ['ke'] 
                
                filtered_results = []
                for res in raw_results:
                    url = res.get("url", "").lower()
                    # Filter for Kenyan URLs (must contain 'ke')
                    if any(indicator in url for indicator in kenyan_indicators):
                        filtered_results.append(res)
                # -----------------------------
                
                results = filtered_results[:60]
                enriched = []
                for res in results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    url = res.get("url", "")
                    search_text = f"{title} {content}".lower() 
                    
                    # Price Extraction
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
                    
                    # Stock Check
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
            st.sidebar.warning(f"Search failed for {instance}. Trying next available search engine...")
            continue
    
    return [] 


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
                "title": r["title"],
                "is_rec": False
            })

    # 2. Calculate and add recommended price
    rec_price = 0
    if prices_numeric_for_calc:
        price_series = pd.Series(prices_numeric_for_calc)
        
        # Calculation logic for recommended price
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
            "title": f"{st.session_state.get('phone', 'Phone Model')} - Competitive Pricing",
            "is_rec": True
        })
    
    # 3. Sort and create DataFrame
    rows.sort(key=lambda x: x["price_val"], reverse=True)
    
    # Prepare data for st.dataframe
    df = pd.DataFrame([{
        "Retailer": r["Retailer"],
        "Price": r["Price"],
        "Stock": r["Stock"],
        "Product Title": r["title"] if r["is_rec"] else r["title"][:50] + "...",
        # Use Markdown links in a helper column for a clickable link in the dataframe
        "Link": f"[View Link]({r['Link']})" if r['Link'].startswith('http') else "N/A"
    } for r in rows])

    # 4. Render
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


############################ STREAMLIT UI ####################################
inject_brand_css()

# Sidebar
with st.sidebar:
    st.title("About this Tool")
    st.markdown("""
    This is a **Minimal, Non-AI** price comparison tool for Tripple K Communications.
    
    It retrieves live competitor pricing from Kenyan e-commerce sites to help set a competitive Tripple K price.
    """)
    st.divider()
    st.caption("Tripple K Communications")
    st.caption("Accredited distributor")

# Main view
st.title("Tripple K Price Finder (Minimal)")
st.caption("Data Retrieval and Comparison Only | tripplek.co.ke")

phone_input = st.text_input("Phone model", placeholder="e.g., Samsung Galaxy A17, Xiaomi Poco X7")

# --- STAGE 1: SEARCH ---
if st.button("Search Kenyan Prices", type="primary"):
    if not phone_input:
        st.error("Please enter a phone model")
    else:
        st.session_state['phone'] = phone_input
        
        with st.status("Searching Kenyan retailers (max 45s wait per instance)...", expanded=True) as status:
            results = fetch_kenyan_prices(phone_input)
            
            if not results:
                st.warning("No relevant Kenyan web data found or all search APIs are unreachable.")
            else:
                st.write(f"Found {len(results)} total listings.")

            st.session_state['results'] = results
            status.update(label="Search Complete!", state="complete", expanded=False)
            
            st.rerun() 


# Display results if available
if st.session_state['results']:
    phone = st.session_state.get('phone', phone_input)
    st.markdown(f"## {phone} - Price Analysis")
    
    prices_numeric = [r["price_ksh_int"] for r in st.session_state['results'] if r["price_ksh_int"] > 0]
    
    if prices_numeric:
        min_p, max_p = min(prices_numeric), max(prices_numeric)
        oos_count = sum(1 for r in st.session_state['results'] if "out" in r["stock"].lower())
        stock_note = "Most listings are in stock." if oos_count == 0 else "Some retailers are out of stock."
        
        st.info(f"**Market Price Range:** KSh {min_p:,} to KSh {max_p:,}. {stock_note}")
    
    st.subheader("Competitor Price Comparison")
    render_price_table(st.session_state['results'])
    
    # --- Display Raw Data for Debugging/Transparency ---
    st.subheader("Raw Data Snippets")
    with st.expander("Click to view snippets from the raw search results (for debugging)"):
        for i, r in enumerate(st.session_state['results']):
            st.markdown(f"**{i+1}. {r['retailer']}** (`{r['price_ksh_str']}`) - Stock: {r['stock']}")
            st.caption(f"**URL:** {r['url']}")
            st.caption(f"**Title:** {r['title']}")
            st.markdown(f"*{r['content']}*")
            st.markdown("---")

    
    st.divider()
    st.caption(f"Data Retrieved {datetime.now().strftime('%d %b %Y %H:%M EAT')} | tripplek.co.ke")
