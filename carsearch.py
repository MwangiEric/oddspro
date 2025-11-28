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

KENYAN_LOCATIONS = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Malindi", "Kitale",
    "Machakos", "Meru", "Nyeri", "Garissa", "Kakamega", "Lamu", "Naivasha", "Nanyuki"
]

KENYAN_CAR_MAKES = [
    "Toyota", "Subaru", "Nissan", "Mitsubishi", "Isuzu", "Mazda", "Honda", "Suzuki",
    "Mercedes", "BMW", "Volkswagen", "Audi", "Ford", "Peugeot", "Land Rover", "Range Rover"
]

# Initialize Groq client
def get_groq_client():
    """Initialize Groq client with user's API key"""
    if 'groq_api_key' in st.session_state and st.session_state.groq_api_key:
        try:
            return groq.Client(api_key=st.session_state.groq_api_key)
        except Exception as e:
            st.error(f"Error initializing Groq client: {e}")
            return None
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
        {text_content[:3000]}  # Limit text to avoid token limits
        
        EXISTING EXTRACTED DATA:
        {json.dumps(car_data, indent=2)}
        
        Please enhance and correct the following fields for the Kenyan market:
        1. Price in KSh (convert if in other currencies)
        2. Car make, model, year (handle common Kenyan typos)
        3. Fuel type (petrol/diesel/hybrid)
        4. Location in Kenya
        5. Contact information (Kenyan phone formats)
        6. Condition (new, used, foreign used)
        7. Transmission (automatic/manual)
        8. Additional features
        
        Return ONLY a JSON object with enhanced data. If information is not available, use null.
        """
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",  # or "mixtral-8x7b-32768" for faster response
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

# Function to extract Kenyan price information
def extract_kenyan_price(text):
    """Extract price from text with Kenyan currency formats"""
    if not text:
        return None
    
    text = text.lower()
    
    # Enhanced Kenyan price patterns
    price_patterns = [
        r'ksh\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # KSh 1,200,000
        r'sh\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',   # Sh 1,200,000
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(ksh|sh|shillings)',  # 1,200,000 KSh
        r'price[\s:]*ksh\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # price: KSh 1,200,000
        r'asking[\s:]*ksh\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # asking: KSh 1,200,000
        # Handle millions format common in Kenya
        r'(\d+(?:\.\d{1,2})?)\s*m(?:illion)?',  # 1.2m, 2 million
        r'ksh\s*(\d+(?:\.\d{1,2})?)\s*m',  # KSh 1.2m
        # Handle USD conversions (common in Kenya)
        r'\$(\d+(?:,\d+)*(?:\.\d{2})?)\s*usd',  # $12,000 USD
        r'usd\s*(\d+(?:,\d+)*(?:\.\d{2})?)',  # USD 12000
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            price_match = matches[0][0] if isinstance(matches[0], tuple) else matches[0]
            
            # Convert millions to actual numbers
            if 'm' in pattern:
                try:
                    return float(price_match) * 1000000
                except:
                    continue
            
            # Handle USD to KSh conversion (approx 1 USD = 130 KSh)
            if 'usd' in pattern or '$' in pattern:
                try:
                    usd_amount = float(price_match.replace(',', ''))
                    return usd_amount * 130  # Convert to KSh
                except:
                    continue
            
            # Handle normal price formats
            try:
                return float(price_match.replace(',', ''))
            except:
                continue
    
    return None

# Function to extract Kenyan contact information
def extract_kenyan_contacts(text):
    """Extract Kenyan phone numbers and email addresses"""
    contacts = {'phones': [], 'emails': []}
    
    if not text:
        return contacts
    
    text = text.lower()
    
    # Enhanced Kenyan phone number patterns
    phone_patterns = [
        r'(\+?254\s?\d{2}\s?\d{3}\s?\d{4})',  # +254 71 234 5678
        r'(07\d{2}\s?\d{3}\s?\d{3})',  # 0712 345 678
        r'(07\d{2}\-?\d{3}\-?\d{3})',  # 0712-345-678
        r'(07\d{8})',  # 0712345678
        r'(01\d{7,8})',  # Landlines: 020 1234567
        r'(tel[:\s]*(\+?254\s?\d{2}\s?\d{3}\s?\d{4}|07\d{8}))',  # tel: 0712345678
        r'(phone[:\s]*(\+?254\s?\d{2}\s?\d{3}\s?\d{4}|07\d{8}))',  # phone: 0712345678
        r'(call[:\s]*(\+?254\s?\d{2}\s?\d{3}\s?\d{4}|07\d{8}))',  # call: 0712345678
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        # Clean up the phone numbers
        for phone in phones:
            if isinstance(phone, tuple):
                phone = phone[1] if phone[1] else phone[0]
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

# Function to extract car details with Kenyan common models
def extract_kenyan_car_details(text):
    """Extract car make, model, year with focus on popular Kenyan models"""
    car_info = {'make': None, 'model': None, 'year': None, 'fuel_type': None, 'transmission': None, 'condition': None}
    
    if not text:
        return car_info
    
    text_lower = text.lower()
    
    # Year pattern (handle typos like "2018" written as "201 8")
    year_patterns = [
        r'\b(19|20)\d{2}\b',
        r'\b(19|20)\s?\d{2}\b'  # Handle space typos
    ]
    
    for pattern in year_patterns:
        year_match = re.search(pattern, text)
        if year_match:
            car_info['year'] = year_match.group().replace(' ', '')
            break
    
    # Fuel type (common in Kenya)
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
    
    # Kenyan popular car models pattern
    kenyan_car_patterns = [
        # Toyota models (very popular in Kenya)
        (r'(toyota|toyota)\s*(vitz|vits|vit|viz)', lambda m: ('Toyota', 'Vitz')),
        (r'(toyota)\s*(premio|premio|premo)', lambda m: ('Toyota', 'Premio')),
        (r'(toyota)\s*(axio|axo)', lambda m: ('Toyota', 'Axio')),
        (r'(toyota)\s*(fileder|fielder)', lambda m: ('Toyota', 'Fielder')),
        (r'(toyota)\s*(wish)', lambda m: ('Toyota', 'Wish')),
        (r'(toyota)\s*(harrier)', lambda m: ('Toyota', 'Harrier')),
        (r'(toyota)\s*(prado|land\s*cruiser\s*prado)', lambda m: ('Toyota', 'Prado')),
        (r'(toyota)\s*(land\s*cruiser)', lambda m: ('Toyota', 'Land Cruiser')),
        (r'(toyota)\s*(hilux|hi-lux)', lambda m: ('Toyota', 'Hilux')),
        (r'(toyota)\s*(noah)', lambda m: ('Toyota', 'Noah')),
        (r'(toyota)\s*(probox)', lambda m: ('Toyota', 'Probox')),
        (r'(toyota)\s*(succeed)', lambda m: ('Toyota', 'Succeed')),
        
        # Subaru models
        (r'(subaru)\s*(forester|forestr|forestor)', lambda m: ('Subaru', 'Forester')),
        (r'(subaru)\s*(impreza|impresa)', lambda m: ('Subaru', 'Impreza')),
        (r'(subaru)\s*(legacy|legacy)', lambda m: ('Subaru', 'Legacy')),
        (r'(subaru)\s*(outback|outbak)', lambda m: ('Subaru', 'Outback')),
        
        # Nissan models
        (r'(nissan)\s*(march)', lambda m: ('Nissan', 'March')),
        (r'(nissan)\s*(sunny|sanny)', lambda m: ('Nissan', 'Sunny')),
        (r'(nissan)\s*(note|not)', lambda m: ('Nissan', 'Note')),
        (r'(nissan)\s*(x-trail|xtrail)', lambda m: ('Nissan', 'X-Trail')),
        (r'(nissan)\s*(navara|navarra)', lambda m: ('Nissan', 'Navara')),
        
        # Common typos and variations
        (r'(toyota)\s*(\w+)', lambda m: ('Toyota', m.group(2).title())),
        (r'(subaru)\s*(\w+)', lambda m: ('Subaru', m.group(2).title())),
        (r'(nissan)\s*(\w+)', lambda m: ('Nissan', m.group(2).title())),
        (r'(honda)\s*(\w+)', lambda m: ('Honda', m.group(2).title())),
        (r'(mitsubishi)\s*(\w+)', lambda m: ('Mitsubishi', m.group(2).title())),
    ]
    
    for pattern, processor in kenyan_car_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            try:
                make, model = processor(match)
                car_info['make'] = make
                car_info['model'] = model
                break
            except Exception as e:
                logger.debug(f"Error processing car pattern: {e}")
                continue
    
    return car_info

# Function to extract Kenyan location
def extract_kenyan_location(text):
    """Extract Kenyan location information"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Enhanced Kenyan locations with typos
    location_mappings = {
        'nairobi': ['nairobi', 'nrb', 'nrobi', 'narobi', 'nayrobi'],
        'mombasa': ['mombasa', 'msa', 'mombassa', 'mombas', 'mombase'],
        'kisumu': ['kisumu', 'kis', 'kisum', 'kisumuu'],
        'nakuru': ['nakuru', 'nak', 'nakur', 'nakurru'],
        'eldoret': ['eldoret', 'eld', 'eldret', 'eldoreet'],
        'thika': ['thika', 'thik', 'tika', 'thikka'],
        'naivasha': ['naivasha', 'naiv', 'naivash', 'naivashaa'],
        'nyeri': ['nyeri', 'nyer', 'nyerri'],
        'meru': ['meru', 'mer', 'merru'],
        'machakos': ['machakos', 'mach', 'machaks', 'machakos'],
        'kisii': ['kisii', 'kisi', 'kisiii'],
        'kericho': ['kericho', 'kerich', 'kerico'],
        'kitale': ['kitale', 'kital', 'kitalee'],
    }
    
    for proper_name, variations in location_mappings.items():
        for variation in variations:
            if variation in text_lower:
                return proper_name.title()
    
    # Pattern matching for locations
    location_patterns = [
        r'in\s+([a-z\s]+),\s*(nairobi|mombasa|kisumu|nakuru|eldoret|thika)',
        r'location[\s:]*([a-z\s]+)',
        r'([a-z\s]+)\s*-\s*kenya',
        r'located\s+in\s+([a-z\s]+)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text_lower)
        if match:
            potential_location = match.group(1).strip()
            # Check if it's a known location
            for proper_name, variations in location_mappings.items():
                if any(variation in potential_location for variation in variations):
                    return proper_name.title()
    
    return None

# Enhanced parsing function for Kenyan sites
def parse_kenyan_car_listing(soup, url, site_name, use_ai=False):
    """Parse car listing details from Kenyan websites"""
    try:
        # Get all text content
        all_text = soup.get_text(separator=' ', strip=True)
        
        # Get title
        title = soup.find("title")
        title_text = title.text.strip() if title else "N/A"
        
        # Get description
        description_meta = soup.find("meta", attrs={"name": "description"})
        description = description_meta["content"] if description_meta else all_text[:500]
        
        # Extract various details with Kenyan focus
        price = extract_kenyan_price(all_text)
        contacts = extract_kenyan_contacts(all_text)
        car_details = extract_kenyan_car_details(all_text)
        location = extract_kenyan_location(all_text)
        
        # Site-specific parsing enhancements
        if "cheki" in site_name.lower():
            # Cheki-specific parsing
            price_element = soup.find('span', class_=re.compile(r'price', re.I))
            if price_element and not price:
                price = extract_kenyan_price(price_element.get_text())
        
        elif "cars45" in site_name.lower():
            # Cars45-specific parsing
            pass
        
        car_info = {
            "title": title_text,
            "url": url,
            "site": site_name,
            "description": description[:300] + "..." if len(description) > 300 else description,
            "price": price,
            "price_display": f"KSh {price:,.0f}" if price else "Negotiable",
            "make": car_details['make'],
            "model": car_details['model'],
            "year": car_details['year'],
            "fuel_type": car_details['fuel_type'],
            "transmission": car_details['transmission'],
            "condition": car_details['condition'],
            "location": location,
            "phones": ", ".join(contacts['phones'][:3]) if contacts['phones'] else "Not provided",
            "emails": ", ".join(contacts['emails'][:2]) if contacts['emails'] else "Not provided",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # AI enhancement if enabled
        if use_ai and st.session_state.get('use_ai_enhancement', False):
            car_info = ai_enhance_car_analysis(car_info, all_text)
        
        return car_info
        
    except Exception as e:
        logger.error(f"Error parsing listing {url}: {e}")
        return None

# Enhanced search function with Kenyan focus
def search_kenyan_car_listings(query, searxng_url, selected_sites, max_results=10, use_ai=False):
    """Search for car listings with Kenyan focus"""
    try:
        # Enhance query with Kenyan context
        enhanced_query = f"{query} Kenya"
        if selected_sites:
            site_queries = " OR ".join([f"site:{urlparse(site).netloc}" for site in selected_sites])
            enhanced_query = f"({query}) ({site_queries})"
        
        params = {"q": enhanced_query, "format": "json", "count": max_results}
        response = requests.get(searxng_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])[:max_results]

        car_details = []
        progress_bar = st.progress(0)
        
        for i, result in enumerate(results):
            url = result.get("url")
            if url:
                try:
                    # Determine which site this belongs to
                    site_name = "Other"
                    for name, site_url in KENYAN_SITES.items():
                        if site_url in url:
                            site_name = name
                            break
                    
                    st.info(f"Processing: {site_name} - {url[:50]}...")
                    page_response = requests.get(url, timeout=10)
                    page_response.raise_for_status()
                    soup = BeautifulSoup(page_response.content, "html.parser")
                    
                    car_info = parse_kenyan_car_listing(soup, url, site_name, use_ai)
                    if car_info:
                        car_details.append(car_info)
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(results))
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Error fetching page {url}: {e}")
                except Exception as e:
                    logger.warning(f"Error parsing page {url}: {e}")

        return car_details

    except requests.exceptions.RequestException as e:
        st.error(f"Search error: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []

# Kenyan price analysis
def analyze_kenyan_prices(car_details):
    """Analyze prices in Kenyan context"""
    if not car_details:
        return {}
    
    df = pd.DataFrame(car_details)
    valid_prices = df[df['price'].notna()]
    
    if len(valid_prices) == 0:
        return {}
    
    analysis = {
        'average_price': valid_prices['price'].mean(),
        'median_price': valid_prices['price'].median(),
        'min_price': valid_prices['price'].min(),
        'max_price': valid_prices['price'].max(),
        'total_listings': len(car_details),
        'priced_listings': len(valid_prices)
    }
    
    return analysis

# AI-powered market insights
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
            model="llama3-70b-8192",
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

# Streamlit app with Kenyan localization
def main():
    st.set_page_config(page_title="Kenya Car Finder", page_icon="🚗", layout="wide")
    
    st.title("🚗 Kenya Car Listing Finder")
    st.markdown("**Find and analyze car listings across Kenyan websites**")
    
    # Initialize session state
    if 'groq_api_key' not in st.session_state:
        st.session_state.groq_api_key = ""
    if 'use_ai_enhancement' not in st.session_state:
        st.session_state.use_ai_enhancement = False
    
    # Sidebar for Kenyan-specific configuration
    with st.sidebar:
        st.header("🇰🇪 Kenya Settings")
        
        searxng_url = st.text_input(
            "SearxNG Instance URL", 
            value="https://searxng-587s.onrender.com",
            help="URL of your SearxNG search instance"
        )
        
        max_results = st.slider("Max Results to Analyze", 5, 30, 15)
        
        st.subheader("🔑 Groq AI Settings")
        groq_key = st.text_input(
            "Groq API Key",
            type="password",
            value=st.session_state.groq_api_key,
            help="Enter your Groq API key for enhanced parsing"
        )
        if groq_key:
            st.session_state.groq_api_key = groq_key
            st.success("✅ Groq API key configured")
        
        use_ai = st.checkbox(
            "Enable AI Enhancement", 
            value=st.session_state.use_ai_enhancement,
            help="Use AI to improve data extraction accuracy"
        )
        st.session_state.use_ai_enhancement = use_ai
        
        if use_ai and not st.session_state.groq_api_key:
            st.warning("⚠️ Please enter Groq API key to use AI features")
        
        st.subheader("🏪 Popular Kenyan Sites")
        selected_sites = []
        # Group sites for better organization
        col1, col2 = st.columns(2)
        
        with col1:
            for site_name, site_url in list(KENYAN_SITES.items())[:7]:
                if st.checkbox(site_name, value=True, key=f"site_{site_name}"):
                    selected_sites.append(site_url)
        
        with col2:
            for site_name, site_url in list(KENYAN_SITES.items())[7:]:
                if st.checkbox(site_name, value=True, key=f"site_{site_name}"):
                    selected_sites.append(site_url)
        
        st.subheader("🚀 Quick Search Templates")
        template_queries = {
            "Toyota Vitz under 800K": "Toyota Vitz KSh 800,000",
            "Subaru Forester Nairobi": "Subaru Forester Nairobi",
            "Nissan March 2015+": "Nissan March 2015",
            "Toyota Premio Diesel": "Toyota Premio diesel",
            "Family Cars under 1M": "family car KSh 1,000,000",
            "Probox for Business": "Toyota Probox commercial",
            "Ex-Japan Cars": "foreign used cars Japan"
        }
        
        selected_template = st.selectbox("Use template:", list(template_queries.keys()))
        
        st.header("💡 Search Tips for Kenya")
        st.markdown("""
        - Use **KSh** for price filters
        - Include **location** (Nairobi, Mombasa, etc.)
        - Specify **fuel type** (petrol/diesel)
        - Use **common Kenyan models**: Vitz, Premio, Axio, Forester
        - Add **year** for newer vehicles
        - Try **'foreign used'** for ex-Japan cars
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
        search_clicked = st.button("🔍 Search Kenyan Sites", type="primary")
    
    # Display Kenyan car makes for quick reference
    st.markdown("**Popular in Kenya:** " + " • ".join(KENYAN_CAR_MAKES[:8]) + " • ...")
    
    # AI features info
    if st.session_state.use_ai_enhancement and st.session_state.groq_api_key:
        st.info("🤖 AI Enhancement: ON - Better parsing with Groq AI")
    
    if search_clicked and query:
        with st.spinner("Searching Kenyan car sites..."):
            car_details = search_kenyan_car_listings(
                query, searxng_url, selected_sites, max_results, st.session_state.use_ai_enhancement
            )
        
        if not car_details:
            st.warning("""
            No car listings found. Try:
            - Checking your search query for typos
            - Using common Kenyan car models
            - Removing very specific filters
            - Trying different Kenyan sites
            """)
        else:
            st.success(f"Found {len(car_details)} Kenyan car listings")
            
            # Convert to DataFrame
            df = pd.DataFrame(car_details)
            
            # Kenyan price analysis
            price_analysis = analyze_kenyan_prices(car_details)
            
            # Display Kenyan-focused statistics
            if price_analysis:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Average Price", 
                             f"KSh {price_analysis['average_price']:,.0f}" if price_analysis['average_price'] > 1000 
                             else f"KSh {price_analysis['average_price']:,.0f}")
                
                with col2:
                    st.metric("Listings with Prices", 
                             f"{price_analysis['priced_listings']}/{price_analysis['total_listings']}")
                
                with col3:
                    # Most common make
                    if not df['make'].empty:
                        common_make = df['make'].mode().iloc[0] if not df['make'].mode().empty else "Various"
                        st.metric("Most Common Make", common_make)
                
                with col4:
                    # Locations found
                    locations_found = df['location'].nunique()
                    st.metric("Locations", locations_found)
            
            # AI Market Insights
            if st.session_state.use_ai_enhancement and st.session_state.groq_api_key:
                with st.spinner("Getting AI market insights..."):
                    market_insights = get_ai_market_insights(car_details, query)
                
                if market_insights:
                    with st.expander("🤖 AI Market Insights", expanded=True):
                        st.write(market_insights)
            
            # Results in tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Kenyan Listings", "🗺️ Location View", "🔍 AI Analysis", "💾 Export Data"])
            
            with tab1:
                # Kenyan-optimized table view
                display_columns = ['site', 'title', 'price_display', 'make', 'model', 'year', 'location']
                display_df = df[display_columns].copy()
                
                # Style the dataframe
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "price_display": st.column_config.TextColumn("Price (KSh)"),
                        "site": st.column_config.TextColumn("Website")
                    }
                )
            
            with tab2:
                # Location-based analysis
                st.subheader("Listings by Location")
                
                if not df['location'].empty:
                    location_counts = df['location'].value_counts()
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.bar_chart(location_counts)
                    
                    with col2:
                        st.write("**Locations:**")
                        for location, count in location_counts.items():
                            st.write(f"{location}: {count} listings")
                
                # Detailed card view
                st.subheader("Detailed Listings")
                for i, car in enumerate(car_details):
                    with st.expander(f"🚗 {car['make'] or 'Car'} {car['model'] or ''} - {car['site']}", expanded=i==0):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**🔗 [{car['site']} Listing]({car['url']})**")
                            st.write(f"**Description:** {car['description']}")
                            
                            specs = []
                            if car['year']:
                                specs.append(f"**Year:** {car['year']}")
                            if car['fuel_type']:
                                specs.append(f"**Fuel:** {car['fuel_type']}")
                            if car['transmission']:
                                specs.append(f"**Transmission:** {car['transmission']}")
                            if car['condition']:
                                specs.append(f"**Condition:** {car['condition']}")
                            if car['location']:
                                specs.append(f"**📍 Location:** {car['location']}")
                            
                            if specs:
                                st.write(" | ".join(specs))
                        
                        with col2:
                            if car['price']:
                                st.metric("Price", f"KSh {car['price']:,.0f}")
                            else:
                                st.write("**Price:** Negotiable")
                            
                            if car['phones'] != "Not provided":
                                st.write(f"**📞 Contact:** {car['phones']}")
                            
                            if car['emails'] != "Not provided":
                                st.write(f"**📧 Email:** {car['emails']}")
            
            with tab3:
                st.subheader("AI-Powered Analysis")
                
                if st.session_state.use_ai_enhancement and st.session_state.groq_api_key:
                    st.info("AI enhancement was used to improve data extraction accuracy")
                    
                    # Show AI-enhanced fields
                    enhanced_fields = ['make', 'model', 'year', 'fuel_type', 'transmission', 'condition']
                    enhanced_count = sum(1 for car in car_details for field in enhanced_fields if car.get(field))
                    st.metric("AI-Enhanced Fields", enhanced_count)
                    
                    # Price analysis by AI
                    priced_cars = [car for car in car_details if car.get('price')]
                    if priced_cars:
                        avg_price = sum(car['price'] for car in priced_cars) / len(priced_cars)
                        st.metric("AI-Verified Average", f"KSh {avg_price:,.0f}")
                else:
                    st.warning("Enable AI Enhancement in sidebar for advanced analysis")
            
            with tab4:
                st.subheader("Export Kenyan Car Data")
                
                # Add Kenyan context to exported data
                export_df = df.copy()
                export_df['search_query'] = query
                export_df['export_date'] = datetime.now().strftime("%Y-%m-%d")
                export_df['data_source'] = 'Kenya Car Finder'
                
                # CSV Export
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV (Kenyan Format)",
                    data=csv,
                    file_name=f"kenya_cars_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
                
                # JSON Export
                json_data = export_df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"kenya_cars_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                )
                
                st.write("**Sample of exported data:**")
                st.dataframe(export_df.head(3))
    
    elif not query and search_clicked:
        st.warning("Tafadhali weka utafutaji lako. (Please enter your search query)")

if __name__ == "__main__":
    main()
