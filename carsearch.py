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
import plotly.graph_objects as go

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

# AI Market Insights
def get_ai_market_insights(car_details, query):
    """Get AI-powered market insights about the search results"""
    client = get_groq_client()
    if not client or not car_details:
        return None
    
    try:
        # Prepare data for analysis
        analysis_data = {
            "search_query": query,
            "total_listings": len(car_details),
            "price_range": f"KSh {min([c.get('price', 0) for c in car_details if c.get('price')]):,.0f} - KSh {max([c.get('price', 0) for c in car_details if c.get('price')]):,.0f}",
            "popular_makes": pd.Series([c.get('make') for c in car_details if c.get('make')]).value_counts().to_dict(),
            "common_locations": pd.Series([c.get('location') for c in car_details if c.get('location')]).value_counts().to_dict()
        }
        
        prompt = f"""
        Analyze this Kenyan car market data and provide insights:
        
        SEARCH QUERY: {query}
        DATA: {json.dumps(analysis_data, indent=2)}
        SAMPLE LISTINGS: {json.dumps(car_details[:3], indent=2)}
        
        Provide concise market insights focusing on:
        1. Price competitiveness in the Kenyan market
        2. Availability and demand patterns
        3. Recommendations for buyers/sellers
        4. Notable trends in the data
        
        Keep it brief and actionable for Kenyan car buyers.
        """
        
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a Kenyan automotive market analyst. Provide practical, localized insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.warning(f"AI market insights failed: {e}")
        return None

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
        title = result.get('title', '')
        content = result.get('content', '')
        url = result.get('url', '')
        
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
        return None

# Enhanced search function
def search_kenyan_car_listings(query, selected_sites, max_results=10, use_ai=False):
    """Search for car listings using JSON-first approach"""
    try:
        # Build query - if no sites selected, just add Kenya
        if not selected_sites:
            enhanced_query = f"{query} Kenya"
            st.info("🔍 Searching across Kenya...")
        else:
            site_queries = " OR ".join([f"site:{urlparse(site).netloc}" for site in selected_sites])
            enhanced_query = f"({query}) ({site_queries})"
            st.info(f"🔍 Searching {len(selected_sites)} selected sites...")
        
        params = {"q": enhanced_query, "format": "json", "count": max_results}
        response = requests.get(SEARXNG_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])[:max_results]

        car_details = []
        
        for result in results:
            car_info = parse_car_from_json(result, use_ai)
            if car_info:
                car_details.append(car_info)
        
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

def create_price_charts(car_details):
    """Create interactive price charts"""
    if not car_details:
        return None, None
    
    df = pd.DataFrame(car_details)
    priced_cars = df[df['price'].notna()]
    
    if len(priced_cars) < 2:
        return None, None
    
    # Price distribution chart
    fig_dist = px.histogram(
        priced_cars, 
        x='price',
        title='💰 Price Distribution',
        labels={'price': 'Price (KSh)'},
        nbins=20
    )
    fig_dist.update_layout(showlegend=False)
    
    # Price by make chart
    make_prices = priced_cars.groupby('make')['price'].mean().reset_index()
    fig_make = px.bar(
        make_prices,
        x='make',
        y='price',
        title='🚗 Average Price by Make',
        labels={'price': 'Average Price (KSh)', 'make': 'Car Make'}
    )
    
    return fig_dist, fig_make

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
            st.success(f"Found {len(car_details)} Kenyan car listings")
            
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
                    st.metric("Price Std Dev", f"KSh {price_analysis['price_std']:,.0f}")
                
                # Price charts
                fig_dist, fig_make = create_price_charts(car_details)
                if fig_dist and fig_make:
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        st.plotly_chart(fig_dist, use_container_width=True)
                    with chart_col2:
                        st.plotly_chart(fig_make, use_container_width=True)
            
            # 🤖 AI MARKET INSIGHTS
            if st.session_state.use_ai_enhancement and get_groq_client():
                with st.spinner("Getting AI market insights..."):
                    market_insights = get_ai_market_insights(car_details, query)
                
                if market_insights:
                    with st.expander("🤖 AI Market Insights", expanded=True):
                        st.write(market_insights)
            
            # Results tabs
            tab1, tab2, tab3 = st.tabs(["📋 Listings", "🔍 Detailed View", "💾 Export Data"])
            
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
                for i, car in enumerate(car_details):
                    with st.expander(f"🚗 {car['make'] or 'Car'} {car['model'] or ''} - {car['site']}", expanded=i<2):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**🔗 Source:** `{car['site']}`")
                            st.markdown(f"**📝 Title:** {car['title']}")
                            st.markdown(f"**📄 Description:** {car['description']}")
                            
                            # Car specifications
                            specs_col1, specs_col2 = st.columns(2)
                            with specs_col1:
                                if car['year']: st.write(f"**Year:** {car['year']}")
                                if car['fuel_type']: st.write(f"**Fuel:** {car['fuel_type']}")
                                if car['transmission']: st.write(f"**Transmission:** {car['transmission']}")
                            with specs_col2:
                                if car['condition']: st.write(f"**Condition:** {car['condition']}")
                                if car.get('ai_enhanced'): st.write("**🤖 AI Enhanced**")
                            
                            # Action buttons
                            st.markdown("---")
                            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                            
                            with action_col1:
                                if car['phones'] != "Not provided":
                                    if st.button("📋 Copy Contacts", key=f"copy_{i}"):
                                        st.code(car['phones'], language="text")
                                        st.success("Contacts copied to clipboard!")
                            
                            with action_col2:
                                if st.button("🔗 Share Listing", key=f"share_{i}"):
                                    st.code(car['url'], language="text")
                                    st.success("URL copied to clipboard!")
                            
                            with action_col3:
                                if car['phones'] != "Not provided":
                                    first_phone = car['phones'].split(',')[0].strip()
                                    st.markdown(f"[📞 Call {first_phone}](tel:{first_phone})")
                            
                            with action_col4:
                                if st.button("⭐ Save", key=f"save_{i}"):
                                    st.success("Listing saved!")
                        
                        with col2:
                            if car['price']:
                                st.metric("Price", f"KSh {car['price']:,.0f}")
                            else:
                                st.write("**Price:** Negotiable")
                            
                            if car['phones'] != "Not provided":
                                st.markdown("**📞 Contacts:**")
                                st.code(car['phones'], language="text")
            
            with tab3:
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
                
                # Export contacts only
                all_contacts = [c for c in car_details if c['phones'] != "Not provided"]
                if all_contacts:
                    contacts_text = "\n".join([f"{c['make']} {c['model']} - {c['phones']}" for c in all_contacts])
                    st.download_button(
                        label="📞 Export Contacts Only",
                        data=contacts_text,
                        file_name=f"car_contacts_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                    )
                
                st.write("**Sample data:**")
                st.dataframe(export_df.head(3))
    
    elif not query and search_clicked:
        st.warning("Please enter your search query")

if __name__ == "__main__":
    main()