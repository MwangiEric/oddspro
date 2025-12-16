import streamlit as st
import requests
import re
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Optional, Dict, Any, List
import time
from datetime import datetime
from dateutil import parser
import pyperclip
import base64

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Tripple K Marketing Suite",
    layout="wide",
    page_icon="📱"
)

# Brand colors & info
BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"

# Icon URLs
ICON_URLS = {
    "processor": "https://ik.imagekit.io/ericmwangi/processor.png",
    "battery": "https://ik.imagekit.io/ericmwangi/battery.png",
    "android": "https://ik.imagekit.io/ericmwangi/android.png",
    "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
    "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
    "storage": "https://ik.imagekit.io/ericmwangi/memory.png",
    "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
    "call": "https://ik.imagekit.io/ericmwangi/call.png",
    "whatsapp": "https://ik.imagekit.io/ericmwangi/whatsapp.png",
    "facebook": "https://ik.imagekit.io/ericmwangi/facebook.png",
    "instagram": "https://ik.imagekit.io/ericmwangi/instagram.png",
    "tiktok": "https://ik.imagekit.io/ericmwangi/tiktok.png",
    "twitter": "https://ik.imagekit.io/ericmwangi/x.png",
}

# CSS Styling
st.markdown(f"""
<style>
    .main {{
        background: #f8f9fa;
    }}
    
    .phone-card {{
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 15px 35px rgba(139, 0, 0, 0.1);
        margin: 1.5rem 0;
    }}
    
    .spec-row {{
        display: flex;
        align-items: center;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
        border-radius: 12px;
        border-left: 4px solid {BRAND_MAROON};
        transition: transform 0.2s;
    }}
    
    .spec-row:hover {{
        transform: translateX(5px);
        background: #fff5f5;
    }}
    
    .spec-icon {{
        width: 32px;
        height: 32px;
        margin-right: 15px;
    }}
    
    .social-post-card {{
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }}
    
    .phone-image-main {{
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        border: 3px solid white;
        background: white;
        padding: 10px;
    }}
    
    .thumbnail-grid {{
        display: flex;
        gap: 10px;
        margin-top: 15px;
    }}
    
    .thumbnail {{
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s;
        cursor: pointer;
    }}
    
    .thumbnail:hover {{
        border-color: {BRAND_MAROON};
        transform: scale(1.05);
    }}
    
    .ad-container {{
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# API FUNCTIONS WITH 18s TIMEOUT
# ==========================================

@st.cache_data(ttl=3600)
def fetch_with_timeout(url: str) -> Optional[Dict]:
    """Fetch data with 18 second timeout"""
    try:
        response = requests.get(url, timeout=18)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out (18s). Please try again.")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
    return None

def search_phones(query: str) -> List[Dict]:
    """Search for phones - GET /gsm/search?q={query}"""
    url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(query)}"
    data = fetch_with_timeout(url)
    return data if data else []

def get_phone_details(phone_id: str) -> Dict:
    """Get phone info - GET /gsm/info/:id"""
    url = f"https://tkphsp2.vercel.app/gsm/info/{phone_id}"
    data = fetch_with_timeout(url)
    return data if data else {}

def get_phone_images(phone_id: str) -> List[str]:
    """Get phone images - GET /gsm/images/:id"""
    url = f"https://tkphsp2.vercel.app/gsm/images/{phone_id}"
    data = fetch_with_timeout(url)
    return data.get('images', []) if data else []

def download_image(url: str) -> Optional[Image.Image]:
    """Download image with timeout"""
    try:
        response = requests.get(url, timeout=18)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        pass
    return None

# ==========================================
# ENHANCED SPEC PARSER WITH AGE CALCULATION
# ==========================================

def calculate_phone_age(launch_date_str: str) -> str:
    """Calculate difference between launch date and today"""
    if not launch_date_str or launch_date_str == "N/A":
        return "Unknown"
    
    try:
        # Parse launch date
        launch_date = parser.parse(launch_date_str, fuzzy=True)
        today = datetime.now()
        
        # Calculate difference
        delta = today - launch_date
        
        if delta.days < 0:
            return "Upcoming"
        elif delta.days == 0:
            return "Launched today"
        elif delta.days < 30:
            return f"{delta.days} days ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = delta.days // 365
            months = (delta.days % 365) // 30
            if months > 0:
                return f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''} ago"
            return f"{years} year{'s' if years > 1 else ''} ago"
            
    except:
        return "Unknown"

def parse_phone_specs(raw_data: dict) -> Dict[str, Any]:
    """Parse phone specs from API response"""
    specs = {
        "name": raw_data.get("name", "Unknown Phone"),
        "id": raw_data.get("id", ""),
        "image": raw_data.get("image", ""),
    }
    
    # Screen
    display = raw_data.get("display", {})
    size = display.get("size", "N/A")
    resolution = display.get("resolution", "N/A")
    
    # Extract inches
    size_match = re.search(r'(\d+\.?\d*)\s*["]?inches', str(size), re.IGNORECASE)
    specs["screen_size"] = f"{size_match.group(1)}\"" if size_match else "N/A"
    
    # Extract resolution
    res_match = re.search(r'(\d+)\s*x\s*(\d+)', str(resolution))
    specs["resolution"] = f"{res_match.group(1)} × {res_match.group(2)}" if res_match else "N/A"
    
    # Camera
    camera = raw_data.get("mainCamera", {})
    camera_modules = camera.get("mainModules", "N/A")
    if isinstance(camera_modules, str) and "MP" in camera_modules:
        mp_values = re.findall(r'(\d+\.?\d*)\s*MP', camera_modules)
        specs["camera"] = " + ".join([f"{mp}MP" for mp in mp_values[:3]]) if mp_values else "N/A"
    else:
        specs["camera"] = "N/A"
    
    # RAM & Storage
    memory = raw_data.get("memory", [])
    ram, storage = "N/A", "N/A"
    
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            val = str(mem.get("value", "")).upper()
            
            # RAM patterns
            ram_matches = [
                r'(\d+)\s*GB\s+RAM',
                r'RAM\s*:\s*(\d+)\s*GB',
                r'^(\d+)\s*GB\s*/\s*\d+',
                r'(\d+)\s*GB.*RAM'
            ]
            
            for pattern in ram_matches:
                match = re.search(pattern, val)
                if match:
                    ram = f"{match.group(1)}GB"
                    break
            
            # Storage patterns
            storage_matches = [
                r'(\d+)\s*GB\s+(?:ROM|STORAGE|Internal)',
                r'(\d+)\s*GB$',
                r'/\s*(\d+)\s*GB',
                r'ROM\s*:\s*(\d+)\s*GB'
            ]
            
            for pattern in storage_matches:
                match = re.search(pattern, val)
                if match:
                    storage = f"{match.group(1)}GB"
                    break
    
    specs["ram"] = ram
    specs["storage"] = storage
    
    # Other specs
    specs["battery"] = raw_data.get("battery", {}).get("battType", "N/A")
    specs["chipset"] = raw_data.get("platform", {}).get("chipset", "N/A")
    specs["os"] = raw_data.get("platform", {}).get("os", "N/A")
    
    # Launch info with age calculation
    launch = raw_data.get("launced", {})
    launch_date = launch.get("announced", launch.get("status", "N/A"))
    specs["launch_date"] = launch_date
    specs["age"] = calculate_phone_age(launch_date)
    
    # Network
    specs["network"] = raw_data.get("network", "N/A")
    
    return specs

# ==========================================
# ICON HANDLING
# ==========================================

def get_icon_image(icon_name: str, size: int = 40) -> Optional[Image.Image]:
    """Get icon image from URL or create fallback"""
    if icon_name in ICON_URLS:
        try:
            img = download_image(ICON_URLS[icon_name])
            if img:
                img.thumbnail((size, size))
                return img
        except:
            pass
    
    # Fallback: create colored circle with letter
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Different colors for different icons
    colors = {
        "processor": "#4CAF50", "battery": "#FF9800", 
        "camera": "#2196F3", "memory": "#9C27B0",
        "storage": "#673AB7", "screen": "#00BCD4",
        "call": "#25D366", "whatsapp": "#25D366",
        "facebook": "#1877F2", "instagram": "#E4405F",
        "twitter": "#1DA1F2", "tiktok": "#000000"
    }
    
    color = colors.get(icon_name, BRAND_MAROON)
    draw.ellipse([0, 0, size, size], fill=color)
    
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    
    letter = icon_name[0].upper()
    draw.text((size//2, size//2), letter, fill="white", font=font, anchor="mm")
    return img

# ==========================================
# ENHANCED WHATSAPP AD GENERATOR
# ==========================================

def generate_whatsapp_ad(phone_specs: Dict) -> Image.Image:
    """Generate WhatsApp ad with icons"""
    width, height = 1080, 1920  # WhatsApp story size
    
    # Create gradient background
    img = Image.new('RGB', (width, height), color=BRAND_MAROON)
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)
        spec_font = ImageFont.truetype("arial.ttf", 42)
        cta_font = ImageFont.truetype("arial.ttf", 56)
        footer_font = ImageFont.truetype("arial.ttf", 36)
    except:
        title_font = ImageFont.load_default()
        spec_font = ImageFont.load_default()
        cta_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()
    
    # Header
    draw.rectangle([0, 0, width, 200], fill=BRAND_MAROON)
    draw.text((width//2, 100), "📱 TRIPPLE K COMMUNICATIONS", 
              fill="white", font=title_font, anchor="mm")
    
    # Get and display phone image
    images = get_phone_images(phone_specs["id"])
    if images:
        phone_img = download_image(images[0])
        if phone_img:
            # Resize to fit
            phone_img.thumbnail((600, 600))
            x_pos = (width - phone_img.width) // 2
            img.paste(phone_img, (x_pos, 250))
            spec_y = 250 + phone_img.height + 50
        else:
            spec_y = 400
    else:
        spec_y = 400
    
    # Phone name
    draw.text((width//2, spec_y), phone_specs["name"], 
              fill=BRAND_GOLD, font=title_font, anchor="mm")
    spec_y += 100
    
    # Specs with icons
    specs_with_icons = [
        ("screen", f"Screen: {phone_specs.get('screen_size', 'N/A')}"),
        ("camera", f"Camera: {phone_specs.get('camera', 'N/A')}"),
        ("memory", f"RAM: {phone_specs.get('ram', 'N/A')}"),
        ("storage", f"Storage: {phone_specs.get('storage', 'N/A')}"),
        ("battery", f"Battery: {phone_specs.get('battery', 'N/A')}"),
        ("processor", f"Chipset: {phone_specs.get('chipset', 'N/A')}"),
    ]
    
    # Draw specs
    for icon_name, text in specs_with_icons:
        if "N/A" not in text:
            # Get icon
            icon = get_icon_image(icon_name, 50)
            if icon:
                img.paste(icon, (width//2 - 300, spec_y - 25), icon)
            
            # Draw text
            draw.text((width//2 - 230, spec_y), text, 
                     fill="white", font=spec_font, anchor="lm")
            spec_y += 80
    
    # CTA Button
    cta_y = spec_y + 80
    draw.rounded_rectangle([width//2 - 250, cta_y - 50, width//2 + 250, cta_y + 50], 
                          radius=25, fill=BRAND_GOLD, outline=BRAND_MAROON, width=4)
    draw.text((width//2, cta_y), "ORDER NOW", 
              fill=BRAND_MAROON, font=cta_font, anchor="mm")
    
    # Contact info with icons
    contact_y = height - 200
    
    # Call icon
    call_icon = get_icon_image("call", 40)
    if call_icon:
        img.paste(call_icon, (width//2 - 150, contact_y - 20), call_icon)
    draw.text((width//2 - 100, contact_y), f"Call: {TRIPPLEK_PHONE}", 
              fill="white", font=footer_font, anchor="lm")
    
    # WhatsApp icon
    whatsapp_icon = get_icon_image("whatsapp", 40)
    if whatsapp_icon:
        img.paste(whatsapp_icon, (width//2 + 50, contact_y - 20), whatsapp_icon)
    draw.text((width//2 + 100, contact_y), f"Chat: {TRIPPLEK_PHONE}", 
              fill="white", font=footer_font, anchor="lm")
    
    # Social icons at bottom
    social_icons = ["facebook", "instagram", "twitter", "tiktok"]
    icon_spacing = 80
    start_x = width//2 - (len(social_icons) * icon_spacing)//2 + icon_spacing//2
    
    for i, icon_name in enumerate(social_icons):
        icon = get_icon_image(icon_name, 50)
        if icon:
            x_pos = start_x + (i * icon_spacing)
            img.paste(icon, (x_pos - 25, height - 100), icon)
    
    return img

# ==========================================
# RICH SOCIAL MEDIA POST GENERATOR
# ==========================================

def generate_rich_social_posts(phone_specs: Dict) -> Dict[str, str]:
    """Generate rich social media posts with emojis and formatting"""
    
    name = phone_specs["name"]
    age = phone_specs.get("age", "")
    
    posts = {
        "facebook": f"""📢 **NEW ARRIVAL AT TRIPPLE K!** 📢

✨ **{name}** ✨
{age if age != "Unknown" else ""}

🔥 **KEY SPECIFICATIONS:**
📱 **Display:** {phone_specs.get('screen_size', 'N/A')} ({phone_specs.get('resolution', 'N/A')})
📸 **Camera System:** {phone_specs.get('camera', 'N/A')}
⚡ **Performance:** {phone_specs.get('ram', 'N/A')} RAM | {phone_specs.get('storage', 'N/A')} Storage
🔋 **Battery:** {phone_specs.get('battery', 'N/A')}
🚀 **Processor:** {phone_specs.get('chipset', 'N/A')}

✅ **WHY BUY FROM TRIPPLE K:**
• 100% Genuine Products
• Official Warranty Included
• Free Delivery in Nairobi
• Flexible Payment Plans
• Expert After-Sales Support

📍 **Visit:** {TRIPPLEK_URL}
📞 **Call/WhatsApp:** {TRIPPLEK_PHONE}

#TrippleKCommunications #PhoneDealsKenya #TechKenya #GadgetsNairobi #SmartphoneKenya #MobilePhonesKE""",
        
        "instagram": f"""✨ **JUST LANDED!** ✨

📱 {name}
{age if age != "Unknown" else ""}

🌟 **SPEC HIGHLIGHTS:**
▪️ {phone_specs.get('screen_size', 'N/A')} Display
▪️ {phone_specs.get('camera', 'N/A')} Camera
▪️ {phone_specs.get('ram', 'N/A')} RAM + {phone_specs.get('storage', 'N/A')} Storage
▪️ {phone_specs.get('battery', 'N/A')} Battery
▪️ {phone_specs.get('chipset', 'N/A')} Chipset

💎 **Premium Features:**
• Premium Build Quality
• Latest Software
• Fast Charging Support
• High Refresh Rate Display

👉 **SWIPE UP TO ORDER**
📲 **DM for Special Offers**

🏷️ **Tripple K Communications**
📍 Nairobi, Kenya
📞 {TRIPPLEK_PHONE}

#TrippleK #TechLovers #PhoneAddict #GadgetGeek #KenyaTech #MobilePhotography""",
        
        "whatsapp": f"""*{name} - NOW AVAILABLE AT TRIPPLE K!*

*📊 Specifications:*
• *Display:* {phone_specs.get('screen_size', 'N/A')} ({phone_specs.get('resolution', 'N/A')})
• *Camera:* {phone_specs.get('camera', 'N/A')}
• *RAM:* {phone_specs.get('ram', 'N/A')}
• *Storage:* {phone_specs.get('storage', 'N/A')}
• *Battery:* {phone_specs.get('battery', 'N/A')}
• *Processor:* {phone_specs.get('chipset', 'N/A')}
• *Launch:* {phone_specs.get('launch_date', 'N/A')} ({age})

*✅ Tripple K Guarantee:*
✓ 100% Genuine Products
✓ Official Warranty
✓ Free Nairobi Delivery
✓ Installment Plans Available
✓ Expert Support

*📞 Contact Us:*
Phone/WhatsApp: {TRIPPLEK_PHONE}
Website: {TRIPPLEK_URL}

*🛒 Order Now & Get:*
• Screen Protector (Free)
• Phone Case (20% Off)
• Delivery in 24 Hours

_Forward to friends who need a new phone!_""",
        
        "tiktok": f"""🔥 PHONE ALERT! 🔥

{name} just dropped at Tripple K!

Why you NEED this phone:
✅ {phone_specs.get('screen_size', 'N/A')} screen for movies & games
✅ {phone_specs.get('camera', 'N/A')} for pro photos
✅ {phone_specs.get('ram', 'N/A')} RAM for multitasking
✅ {phone_specs.get('storage', 'N/A')} for all your files
✅ {phone_specs.get('battery', 'N/A')} for all-day power

💰 COMMENT "PRICE" for best deal!
📲 DM us for installment plans!

#PhoneTok #TechTok #KenyaTikTok #GadgetDeals #PhoneReview #TrippleK"""
    }
    
    return posts

# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    # Header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {BRAND_MAROON} 0%, #6b0000 100%); 
                padding: 2.5rem; border-radius: 20px; color: white; text-align: center; 
                margin-bottom: 2rem; box-shadow: 0 15px 35px rgba(139, 0, 0, 0.3);">
        <h1 style="margin: 0; font-size: 2.8rem;">📱 Tripple K Marketing Suite</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Professional Phone Marketing Platform
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'selected_phone' not in st.session_state:
        st.session_state.selected_phone = None
    if 'phone_specs' not in st.session_state:
        st.session_state.phone_specs = None
    if 'phone_images' not in st.session_state:
        st.session_state.phone_images = []
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Search Phone", "📱 Social Content", "🎨 Create Ads"])
    
    # TAB 1: SEARCH PHONE
    with tab1:
        st.markdown("### Find Phone Specifications")
        
        # Search bar
        col_search = st.columns([3, 1])
        with col_search[0]:
            search_query = st.text_input(
                "Enter phone model:", 
                placeholder="e.g., Samsung Galaxy S23 Ultra, iPhone 15 Pro Max",
                key="search_input"
            )
        with col_search[1]:
            search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_btn and search_query:
            with st.spinner("🔍 Searching database..."):
                results = search_phones(search_query)
                
                if results:
                    st.success(f"✅ Found {len(results)} phones")
                    
                    # Phone selection
                    phone_names = [r.get('name', 'Unknown') for r in results]
                    selected_name = st.selectbox("Select a phone:", phone_names, key="phone_select")
                    
                    if selected_name:
                        selected_data = next(r for r in results if r['name'] == selected_name)
                        
                        with st.spinner("📋 Fetching specifications..."):
                            # Get phone details
                            details = get_phone_details(selected_data['id'])
                            
                            if details:
                                # Parse specs
                                specs = parse_phone_specs(details)
                                
                                # Get phone images
                                images = get_phone_images(selected_data['id'])
                                
                                # Store in session
                                st.session_state.selected_phone = selected_data
                                st.session_state.phone_specs = specs
                                st.session_state.phone_images = images[:3]  # First 3 images
                                
                                # Display phone card
                                st.markdown('<div class="phone-card">', unsafe_allow_html=True)
                                
                                # Two-column layout: Image left, Specs right
                                col_img, col_specs = st.columns([1, 1])
                                
                                with col_img:
                                    # Main phone image
                                    st.markdown("#### 📸 Phone Preview")
                                    if images:
                                        main_img = download_image(images[0])
                                        if main_img:
                                            st.image(main_img, use_column_width=True, 
                                                    caption=specs['name'], 
                                                    output_format="PNG")
                                    
                                    # Thumbnail grid for first 3 images
                                    if len(images) > 1:
                                        st.markdown("#### More Images")
                                        cols = st.columns(3)
                                        for idx, img_url in enumerate(images[1:4]):  # Next 3 images
                                            with cols[idx]:
                                                try:
                                                    thumb_img = download_image(img_url)
                                                    if thumb_img:
                                                        thumb_img.thumbnail((150, 150))
                                                        st.image(thumb_img, use_column_width=True)
                                                except:
                                                    pass
                                
                                with col_specs:
                                    st.markdown(f"### {specs['name']}")
                                    
                                    # Age badge
                                    if specs['age'] != "Unknown":
                                        st.markdown(f"""
                                        <div style="background: {BRAND_GOLD}; color: {BRAND_MAROON}; 
                                                    padding: 0.5rem 1rem; border-radius: 20px; 
                                                    display: inline-block; font-weight: bold; margin-bottom: 1rem;">
                                            🕐 {specs['age']}
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    # Specs list
                                    spec_items = [
                                        ("screen", "Screen", f"{specs.get('screen_size', 'N/A')} ({specs.get('resolution', 'N/A')})"),
                                        ("camera", "Camera", specs.get('camera', 'N/A')),
                                        ("memory", "RAM", specs.get('ram', 'N/A')),
                                        ("storage", "Storage", specs.get('storage', 'N/A')),
                                        ("battery", "Battery", specs.get('battery', 'N/A')),
                                        ("processor", "Chipset", specs.get('chipset', 'N/A')),
                                        ("android", "OS", specs.get('os', 'N/A')),
                                        ("call", "Network", specs.get('network', 'N/A')),
                                    ]
                                    
                                    for icon_name, label, value in spec_items:
                                        if value != "N/A":
                                            st.markdown(f"""
                                            <div class="spec-row">
                                                <img src="{ICON_URLS.get(icon_name, '')}" class="spec-icon" onerror="this.style.display='none'">
                                                <div>
                                                    <strong>{label}:</strong><br>
                                                    <span style="color: #555;">{value}</span>
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                    
                                    # Launch info
                                    if specs.get('launch_date') != "N/A":
                                        st.info(f"**📅 Launch Date:** {specs['launch_date']}")
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error("❌ No phones found. Try a different search term.")
    
    # TAB 2: SOCIAL CONTENT
    with tab2:
        st.markdown("### Generate Social Media Content")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone in the 'Search Phone' tab")
        else:
            phone_specs = st.session_state.phone_specs
            
            # Generate posts button
            if st.button("✨ Generate All Social Media Posts", type="primary", use_container_width=True):
                with st.spinner("🎨 Creating content..."):
                    posts = generate_rich_social_posts(phone_specs)
                    
                    # Platform sections
                    platforms = [
                        ("📘", "Facebook", "facebook"),
                        ("📷", "Instagram", "instagram"),
                        ("💬", "WhatsApp", "whatsapp"),
                        ("🎵", "TikTok", "tiktok")
                    ]
                    
                    for icon, name, key in platforms:
                        with st.expander(f"{icon} {name} Post", expanded=True):
                            st.markdown(f'<div class="social-post-card">{posts[key]}</div>', 
                                       unsafe_allow_html=True)
                            
                            # Copy button
                            col_copy, col_dl = st.columns([4, 1])
                            with col_copy:
                                if st.button(f"📋 Copy {name} Post", key=f"copy_{key}"):
                                    # Create a copyable text area
                                    copied_text = st.text_area(f"{name} Post", posts[key], 
                                                             height=200, key=f"text_{key}")
                                    st.success("✅ Ready to copy! Select and copy the text above.")
                            
                            st.markdown("---")
    
    # TAB 3: CREATE ADS
    with tab3:
        st.markdown("### Create Marketing Ads")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone in the 'Search Phone' tab")
        else:
            phone_specs = st.session_state.phone_specs
            
            # Ad type selection
            st.markdown("#### Select Ad Type")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                facebook_ad = st.checkbox("Facebook Ad", value=True)
            with col2:
                whatsapp_ad = st.checkbox("WhatsApp Ad", value=True)
            with col3:
                instagram_ad = st.checkbox("Instagram Ad", value=True)
            
            # Generate ads button
            if st.button("🖼️ Generate Selected Ads", type="primary", use_container_width=True):
                with st.spinner("🎨 Generating ads..."):
                    generated_ads = {}
                    
                    # WhatsApp Ad
                    if whatsapp_ad:
                        try:
                            whatsapp_img = generate_whatsapp_ad(phone_specs)
                            buf = BytesIO()
                            whatsapp_img.save(buf, format="PNG", quality=95)
                            generated_ads["WhatsApp Ad"] = buf.getvalue()
                        except Exception as e:
                            st.error(f"Failed to create WhatsApp ad: {e}")
                    
                    # Display generated ads
                    if generated_ads:
                        st.success(f"✅ Generated {len(generated_ads)} ad(s)")
                        
                        for ad_name, ad_bytes in generated_ads.items():
                            st.markdown(f"### {ad_name}")
                            st.markdown('<div class="ad-container">', unsafe_allow_html=True)
                            
                            col_disp, col_info = st.columns([2, 1])
                            
                            with col_disp:
                                # Convert bytes to image
                                ad_image = Image.open(BytesIO(ad_bytes))
                                st.image(ad_image, use_column_width=True)
                            
                            with col_info:
                                st.markdown("#### 📋 Ad Details")
                                st.markdown(f"""
                                **Phone:** {phone_specs['name']}
                                
                                **Specs Shown:**
                                • {phone_specs.get('screen_size', 'N/A')} Display
                                • {phone_specs.get('camera', 'N/A')} Camera
                                • {phone_specs.get('ram', 'N/A')} RAM
                                • {phone_specs.get('storage', 'N/A')} Storage
                                
                                **CTA:** ORDER NOW
                                **Contact:** {TRIPPLEK_PHONE}
                                """)
                                
                                # Download button
                                st.download_button(
                                    label="📥 Download Ad",
                                    data=ad_bytes,
                                    file_name=f"tripplek_{ad_name.lower().replace(' ', '_')}.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                            st.markdown("---")

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 2rem;">
        <h3>Tripple K Communications</h3>
        <p>📞 {TRIPPLEK_PHONE} | 📱 WhatsApp: {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}</p>
        <div style="display: flex; justify-content: center; gap: 20px; margin: 1rem 0;">
            <img src="{ICON_URLS['facebook']}" width="30" height="30">
            <img src="{ICON_URLS['instagram']}" width="30" height="30">
            <img src="{ICON_URLS['twitter']}" width="30" height="30">
            <img src="{ICON_URLS['tiktok']}" width="30" height="30">
        </div>
        <p style="font-size: 0.9em; color: #666;">Professional Phone Marketing Suite v4.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()