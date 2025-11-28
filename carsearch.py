import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime
import logging
from urllib.parse import urlparse
import groq
import json
import time
import plotly.express as px

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kenyan-specific configurations
KENYAN_SITES = {
    "Cheki Kenya": "https://www.cheki.co.ke",
    "Cars45 Kenya": "https://www.cars45.co.ke", 
    "Jiji Kenya": "https://jiji.co.ke",
    "Facebook Marketplace": "https://www.facebook.com/marketplace",
    "OLX Kenya": "https://www.olx.co.ke",
    "Car & General": "https://www.carandgeneral.co.ke",
    "AutoTrader Kenya": "https://www.autotrader.co.ke",
    "Magari Deals": "https://www.magarideals.com",
    "Autochek Africa": "https://www.autochek.africa",
    "Cars Kenya": "https://www.carskenya.co.ke",
    "Auto Kenya": "https://www.autokenya.com",
    "Car Duka": "https://www.carduka.com",
    "Used Cars Kenya": "https://www.usedcars.co.ke",
    "Pigiame": "https://www.pigiame.co.ke"
}

# Hardcoded SearxNG instance
SEARXNG_URL = "https://searxng-587s.onrender.com"

# Initialize Groq client
def get_groq_client():
    """Initialize Groq client with secret API key"""
    try:
        if "groq_key" in st.secrets:
            return groq.Client(api_key=st.secrets["groq_key"])
    except Exception as e:
        logger.error(f"Error initializing Groq client: {e}")
    return None

# AI-enhanced parsing function
def ai_enhance_car_analysis(car_data, text_content):
    """Use Groq AI to enhance car data extraction and analysis"""
    client = get_groq_client()
    if not client:
        return car_data
    
    try:
        prompt = f"""
        Analyze this Kenyan car listing and extract structured information:
        
        TEXT CONTENT:
        {text_content[:3000]}
        
        EXISTING EXTRACTED DATA:
        {json.dumps(car_data, indent=2)}
        
        Please enhance and correct the following fields for the Kenyan market:
        1. Price in KSh (convert if in other currencies, handle formats like 800000, 800k, 1.2m)
        2. Car make, model, year (handle common Kenyan typos like vitz/vits/viz)
        3. Fuel type (petrol/diesel/hybrid)
        4. Location in Kenya
        5. Contact information (Kenyan phone formats: 07xxx, 01xxx, +254)
        6. Condition (new, used, foreign used)
        7. Transmission (automatic/manual)
        8. Additional features
        
        Return ONLY a JSON object with enhanced data. If information is not available, use null.
        """
        
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert at analyzing Kenyan car listings. Extract accurate information considering common Kenyan terminology and typos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        
        enhanced_data = json.loads(response.choices[0].message.content)
        
        # Merge enhanced data with existing data
        for key, value in enhanced_data.items():
            if value and value != "null" and value != "N/A":
                car_data[key] = value
                
        return car_data
        
    except Exception as e:
        logger.warning(f"AI enhancement failed: {e}")
        return car_data

# Enhanced Kenyan price extraction
def extract_kenyan_price(text):
    """Extract price from text with all Kenyan currency formats"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # All Kenyan price patterns
    price_patterns = [
        # Formatted prices with currency
        r'ksh\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'sh\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(ksh|sh|shillings)',
        
        # Million formats
        r'(\d+(?:\.\d{1,2})?)\s*m(?:illion)?',
        r'ksh\s*(\d+(?:\.\d{1,2})?)\s*m',
        
        # K format
        r'(\d+(?:\.\d)?)\s*k\b',
        r'ksh\s*(\d+)\s*k',
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            price_match = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
            
            try:
                # Handle million format
                if 'm' in pattern:
                    return float(price_match) * 1000000
                
                # Handle k format
                if 'k' in pattern and not 'ksh' in pattern:
                    return float(price_match) * 1000
                
                # Handle normal numbers
                clean_price = price_match.replace(',', '')
                return float(clean_price)
                
            except ValueError:
                continue
    
    # Final fallback: look for large standalone numbers near price keywords
    if any(keyword in text_lower for keyword in ['price', 'cost', 'asking', 'ksh', 'sh']):
        big_numbers = re.findall(r'\b(\d{5,7})\b', text)
        if big_numbers:
            try:
                return float(big_numbers[0])
            except:
                pass
    
    return None

# Enhanced Kenyan contact extraction
def extract_kenyan_contacts(text):
    """Extract all Kenyan phone numbers and email addresses"""
    contacts = {'phones': [], 'emails': []}
    
    if not text:
        return contacts
    
    # All Kenyan phone number patterns
    phone_patterns = [
        r'(\+?254\s?\d{2}\s?\d{3}\s?\d{4})',
        r'(07\d{2}\s?\d{3}\s?\d{3})',
        r'(07\d{2}\-?\d{3}\-?\d{3})',
        r'(07\d{8})',
        r'(01\d{7,8})',
        r'(011\d{6,7})',
        r'(010\d{6,7})',
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        for phone in phones:
            cleaned_phone = re.sub(r'[\s\-]', '', str(phone))
            if cleaned_phone and cleaned_phone not in contacts['phones']:
                contacts['phones'].append(cleaned_phone)
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    contacts['emails'].extend(emails)
    
    # Remove duplicates
    contacts['phones'] = list(set(contacts['phones']))
    contacts['emails'] = list(set(contacts['emails']))
    
    return contacts

# Enhanced car details extraction
def extract_kenyan_car_details(text):
    """Extract car make, model, year with focus on popular Kenyan models"""
    car_info = {'make': None, 'model': None, 'year': None, 'fuel_type': None, 'transmission': None, 'condition': None}
    
    if not text:
        return car_info
    
    text_lower = text.lower()
    
    # Year extraction with typo handling
    year_patterns = [
        r'\b(19|20)\d{2}\b',
        r'\b(19|20)\s?\d{2}\b'
    ]
    
    for pattern in year_patterns:
        year_match = re.search(pattern, text)
        if year_match:
            car_info['year'] = year_match.group().replace(' ', '')
            break
    
    # Fuel type
    fuel_types = ['petrol', 'diesel', 'hybrid', 'electric']
    for fuel in fuel_types:
        if fuel in text_lower:
            car_info['fuel_type'] = fuel.capitalize()
            break
    
    # Transmission type
    if 'automatic' in text_lower or 'at' in text_lower:
        car_info['transmission'] = 'Automatic'
    elif 'manual' in text_lower or 'mt' in text_lower:
        car_info['transmission'] = 'Manual'
    
    # Condition
    if 'new' in text_lower:
        car_info['condition'] = 'New'
    elif 'used' in text_lower or 'second' in text_lower:
        car_info['condition'] = 'Used'
    elif 'foreign used' in text_lower or 'ex-japan' in text_lower:
        car_info['condition'] = 'Foreign Used'
    
    # Kenyan car models with typo handling
    kenyan_car_patterns = [
        (r'(toyota|toyota)\s*(vitz|vits|vit|viz)', lambda m: ('Toyota', 'Vitz')),
        (r'(toyota)\s*(premio|premio|premo)', lambda m: ('Toyota', 'Premio')),
        (r'(toyota)\s*(axio|axo)', lambda m: ('Toyota', 'Axio')),
        (r'(toyota)\s*(fileder|fielder)', lambda m: ('Toyota', 'Fielder')),
        (r'(toyota)\s*(wish)', lambda m: ('Toyota', 'Wish')),
        (r'(toyota)\s*(probox)', lambda m: ('Toyota', 'Probox')),
        (r'(subaru)\s*(forester|forestr|forestor)', lambda m: ('Subaru', 'Forester')),
        (r'(nissan)\s*(march)', lambda m: ('Nissan', 'March')),
        (r'(nissan)\s*(sunny|sanny)', lambda m: ('Nissan', 'Sunny')),
    ]
    
    for pattern, processor in kenyan_car_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            try:
                make, model = processor(match)
                car_info['make'] = make
                car_info['model'] = model
                break
            except:
                continue
    
    return car_info

# Get site from URL
def get_site_from_url(url):
    """Extract full domain from URL"""
    try:
        domain = urlparse(url).netloc
        return domain
    except:
        return url.split('/')[2] if '//' in url else url.split('/')[0]

# Parse car listing from JSON data
def parse_car_from_json(result, use_ai=False):
    """Parse car listing primarily from JSON data"""
    try:
        title = result.get('title', 'No Title')
        content = result.get('content', result.get('snippet', ''))
        url = result.get('url', result.get('link', ''))
        
        # Combine title and content for parsing
        combined_text = f"{title} {content}"
        
        # Extract details from JSON data
        price = extract_kenyan_price(combined_text)
        contacts = extract_kenyan_contacts(combined_text)
        car_details = extract_kenyan_car_details(combined_text)
        
        car_info = {
            "title": title,
            "url": url,
            "site": get_site_from_url(url),
            "description": content[:300] + "..." if len(content) > 300 else content,
            "price": price,
            "price_display": f"KSh {price:,.0f}" if price else "Negotiable",
            "make": car_details['make'],
            "model": car_details['model'],
            "year": car_details['year'],
            "fuel_type": car_details['fuel_type'],
            "transmission": car_details['transmission'],
            "condition": car_details['condition'],
            "phones": ", ".join(contacts['phones'][:3]) if contacts['phones'] else "Not provided",
            "emails": ", ".join(contacts['emails'][:2]) if contacts['emails'] else "Not provided",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "json"
        }
        
        # AI enhancement if available
        if use_ai:
            car_info = ai_enhance_car_analysis(car_info, combined_text)
            car_info['ai_enhanced'] = True
        
        return car_info
        
    except Exception as e:
        logger.error(f"Error parsing JSON result: {e}")
        # Return basic info instead of failing
        return {
            "title": result.get('title', 'Error parsing'),
            "url": result.get('url', ''),
            "site": get_site_from_url(result.get('url', '')),
            "description": "Failed to parse details",
            "price": None,
            "price_display": "Unknown",
            "make": None,
            "model": None,
            "error": str(e)
        }

# Enhanced search function
def search_kenyan_car_listings(query, selected_sites, max_results=10, use_ai=False):
    """Search for car listings using JSON-first approach"""
    try:
        # Build query - if no sites selected, just add Kenya
        car_context = "car vehicles for sale"
        
        if not selected_sites:
            enhanced_query = f"{query} {car_context} Kenya"
            st.info("🔍 Searching across Kenya...")
        else:
            site_queries = " OR ".join([f"site:{urlparse(site).netloc}" for site in selected_sites])
            enhanced_query = f"({query} {car_context}) ({site_queries})"
            st.info(f"🔍 Searching {len(selected_sites)} selected sites...")
        
        # Show the actual query being sent
        st.write(f"**🔍 Search Query:** `{enhanced_query}`")
        
        params = {"q": enhanced_query, "format": "json", "count": max_results}
        response = requests.get(SEARXNG_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        # Show raw results count
        st.write(f"**📦 Raw Results Found:** {len(results)}")

        car_details = []
        
        # Create container for live results
        results_container = st.container()
        
        with results_container:
            st.subheader("🔄 Live Processing")
            
            for i, result in enumerate(results):
                # Show raw result immediately
                with st.expander(f"📦 Raw Result {i+1}", expanded=False):
                    st.json(result)
                
                # Parse the result
                with st.spinner(f"Parsing result {i+1}..."):
                    car_info = parse_car_from_json(result, use_ai)
                
                if car_info:
                    car_details.append(car_info)
                    
                    # Show parsed result
                    with st.expander(f"✅ Parsed: {car_info['title'][:50]}...", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Site:** {car_info['site']}")
                            st.write(f"**Price:** {car_info['price_display']}")
                            st.write(f"**Make/Model:** {car_info['make']} {car_info['model']}")
                        with col2:
                            st.write(f"**Contacts:** {car_info['phones']}")
                            if car_info.get('ai_enhanced'):
                                st.success("🤖 AI Enhanced")
                
                st.markdown("---")
        
        return car_details

    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []

# Price analysis and visualization
def create_price_analysis(car_details):
    """Create comprehensive price analysis and visualizations"""
    if not car_details:
        return None
    
    df = pd.DataFrame(car_details)
    valid_prices = df[df['price'].notna()]
    
    if len(valid_prices) == 0:
        return None
    
    analysis = {
        'average_price': valid_prices['price'].mean(),
        'median_price': valid_prices['price'].median(),
        'min_price': valid_prices['price'].min(),
        'max_price': valid_prices['price'].max(),
        'total_listings': len(car_details),
        'priced_listings': len(valid_prices),
        'price_std': valid_prices['price'].std()
    }
    
    return analysis

# Instance health check
def check_instance_health():
    """Check if SearxNG instance is ready"""
    with st.spinner("🔄 Starting SmartRev search engine... (4 seconds)"):
        start_time = time.time()
        
        for i in range(4):
            try:
                response = requests.get(SEARXNG_URL, timeout=1)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1 - (time.time() - start_time) % 1)
        
        return True

# Streamlit app
def main():
    st.set_page_config(page_title="SmartRev - Kenya Car Finder", page_icon="🚗", layout="wide")
    
    # Initialize session state
    if 'use_ai_enhancement' not in st.session_state:
        st.session_state.use_ai_enhancement = True
    
    # App header
    st.title("🚗 SmartRev - Kenya Car Finder")
    st.markdown("**Find and analyze car listings across Kenyan websites**")
    
    # Instance health check on load
    if 'instance_ready' not in st.session_state:
        check_instance_health()
        st.session_state.instance_ready = True
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🇰🇪 SmartRev Settings")
        
        st.subheader("🏪 Select Kenyan Sites")
        selected_sites = []
        
        # Display sites in two columns
        col1, col2 = st.columns(2)
        sites_list = list(KENYAN_SITES.items())
        
        with col1:
            for site_name, site_url in sites_list[:7]:
                if st.checkbox(site_name, value=False, key=f"site_{site_name}"):
                    selected_sites.append(site_url)
        
        with col2:
            for site_name, site_url in sites_list[7:]:
                if st.checkbox(site_name, value=False, key=f"site_{site_name}"):
                    selected_sites.append(site_url)
        
        st.subheader("🤖 AI Enhancement")
        use_ai = st.checkbox(
            "Enable AI Data Enhancement", 
            value=st.session_state.use_ai_enhancement,
            help="Use AI to improve data extraction accuracy"
        )
        st.session_state.use_ai_enhancement = use_ai
        
        if use_ai and not get_groq_client():
            st.warning("⚠️ Groq API key not found in secrets")
        
        st.subheader("🔍 Quick Search Templates")
        template_queries = {
            "Toyota Vitz under 800K": "Toyota Vitz KSh 800,000",
            "Subaru Forester Nairobi": "Subaru Forester Nairobi",
            "Nissan March 2015+": "Nissan March 2015",
            "Toyota Premio Diesel": "Toyota Premio diesel",
            "Family Cars under 1M": "family car KSh 1,000,000"
        }
        
        selected_template = st.selectbox("Use template:", list(template_queries.keys()))
        
        st.markdown("---")
        st.markdown("**💡 Search Tips:**")
        st.markdown("""
        - Use **KSh** for price filters
        - Include **location** for better results
        - Try **common models**: Vitz, Premio, Forester
        - Select sites or search **all Kenya**
        """)
    
    # Main search interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        default_query = template_queries[selected_template] if selected_template else ""
        query = st.text_input(
            "Search for cars in Kenya:",
            value=default_query,
            placeholder="e.g., Toyota Vitz Nairobi KSh 800,000",
            help="Enter car make, model, location, and price range"
        )
    
    with col2:
        st.write("")  
        st.write("")  
        search_clicked = st.button("🔍 Search SmartRev", type="primary")
    
    # Perform search
    if search_clicked and query:
        with st.spinner("Searching Kenyan car listings..."):
            car_details = search_kenyan_car_listings(
                query, selected_sites, max_results=15, use_ai=st.session_state.use_ai_enhancement
            )
        
        if not car_details:
            st.warning("""
            No car listings found. Try:
            - Checking your search query
            - Using common Kenyan car models  
            - Selecting different sites
            """)
        else:
            st.success(f"✅ Found {len(car_details)} Kenyan car listings")
            
            # Convert to DataFrame
            df = pd.DataFrame(car_details)
            
            # 📊 COMPREHENSIVE SUMMARY DASHBOARD
            st.subheader("📊 Search Summary")
            
            # Key metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                total_listings = len(car_details)
                st.metric("Total Listings", total_listings)
            
            with col2:
                priced_listings = len([c for c in car_details if c['price']])
                st.metric("With Prices", f"{priced_listings}/{total_listings}")
            
            with col3:
                contact_listings = len([c for c in car_details if c['phones'] != "Not provided"])
                st.metric("With Contacts", f"{contact_listings}/{total_listings}")
            
            with col4:
                unique_sites = df['site'].nunique()
                st.metric("Sites Found", unique_sites)
            
            with col5:
                ai_enhanced = len([c for c in car_details if c.get('ai_enhanced')])
                if ai_enhanced > 0:
                    st.metric("🤖 AI Enhanced", f"{ai_enhanced}/{total_listings}")
            
            # 💰 PRICE ANALYSIS SECTION
            price_analysis = create_price_analysis(car_details)
            if price_analysis:
                st.subheader("💰 Price Analysis")
                
                # Price metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Average Price", f"KSh {price_analysis['average_price']:,.0f}")
                
                with col2:
                    st.metric("Median Price", f"KSh {price_analysis['median_price']:,.0f}")
                
                with col3:
                    st.metric("Price Range", f"KSh {price_analysis['min_price']:,.0f} - {price_analysis['max_price']:,.0f}")
                
                with col4:
                    st.metric("Listings Priced", f"{price_analysis['priced_listings']}/{price_analysis['total_listings']}")
            
            # Results tabs
            tab1, tab2 = st.tabs(["📋 Final Results", "💾 Export Data"])
            
            with tab1:
                display_columns = ['site', 'title', 'price_display', 'make', 'model', 'year']
                display_df = df[display_columns].copy()
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "price_display": st.column_config.TextColumn("Price (KSh)"),
                        "site": st.column_config.TextColumn("Website")
                    }
                )
            
            with tab2:
                st.subheader("💾 Export Data")
                
                export_df = df.copy()
                export_df['search_query'] = query
                export_df['export_date'] = datetime.now().strftime("%Y-%m-%d")
                
                # CSV Export
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"smartrev_kenya_cars_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
                
                st.write("**Sample data:**")
                st.dataframe(export_df.head(3))
    
    elif not query and search_clicked:
        st.warning("Please enter your search query")

if __name__ == "__main__":
    main()