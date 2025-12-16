import streamlit as st
import requests
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import Optional, Dict, Any, List
import time
import pyperclip

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Tripple K Marketing Suite",
    layout="wide",
    page_icon="📱"
)

# Brand colors
BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
BRAND_GREEN = "#008000"
BRAND_WHITE = "#FFFFFF"

# Brand info
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
TRIPPLEK_LOCATION = "Moi Avenue Opposite MKU Towers"

# Logo URL
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# Icon URLs
ICON_URLS = {
    "processor": "https://ik.imagekit.io/ericmwangi/processor.png",
    "battery": "https://ik.imagekit.io/ericmwangi/battery.png",
    "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
    "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
    "storage": "https://ik.imagekit.io/ericmwangi/memory.png",
    "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
    "call": "https://ik.imagekit.io/ericmwangi/call.png",
    "whatsapp": "https://ik.imagekit.io/ericmwangi/whatsapp.png",
    "location": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
    "warranty": "https://cdn-icons-png.flaticon.com/512/411/411723.png",
    "delivery": "https://cdn-icons-png.flaticon.com/512/3095/3095113.png",
}

# CSS Styling
st.markdown(f"""
<style>
    .main {{
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }}
    
    .header-container {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #6b0000 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 15px 35px rgba(139, 0, 0, 0.3);
    }}
    
    .specs-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 15px;
        margin: 1.5rem 0;
    }}
    
    .spec-card {{
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 15px rgba(139, 0, 0, 0.1);
        border-left: 4px solid {BRAND_MAROON};
        transition: transform 0.3s;
    }}
    
    .spec-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(139, 0, 0, 0.2);
    }}
    
    .image-gallery {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        margin: 2rem 0;
    }}
    
    .image-card {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        transition: all 0.3s;
        background: white;
        padding: 10px;
    }}
    
    .image-card:hover {{
        transform: scale(1.03);
        box-shadow: 0 12px 30px rgba(139, 0, 0, 0.25);
    }}
    
    .post-container {{
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        border: 1px solid rgba(139, 0, 0, 0.1);
    }}
    
    .platform-tab {{
        background: {BRAND_MAROON};
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 25px;
        display: inline-block;
        margin-bottom: 1rem;
        font-weight: bold;
    }}
    
    .cta-button {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(139, 0, 0, 0.3);
        width: 100%;
        margin-top: 1rem;
    }}
    
    .cta-button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 0, 0, 0.4);
    }}
    
    .price-tag {{
        background: {BRAND_GOLD};
        color: {BRAND_MAROON};
        padding: 0.5rem 1.5rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.2em;
        display: inline-block;
        margin: 1rem 0;
    }}
    
    .benefit-item {{
        background: #f9f9f9;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 3px solid {BRAND_GREEN};
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# API FUNCTIONS
# ==========================================

@st.cache_data(ttl=3600)
def fetch_with_timeout(url: str) -> Optional[Dict]:
    """Fetch data with timeout"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
    return None

def search_phones(query: str) -> List[Dict]:
    """Search for phones"""
    url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(query)}"
    data = fetch_with_timeout(url)
    return data if data else []

def get_phone_details(phone_id: str) -> Dict:
    """Get phone info"""
    url = f"https://tkphsp2.vercel.app/gsm/info/{phone_id}"
    data = fetch_with_timeout(url)
    return data if data else {}

def get_phone_images(phone_id: str) -> List[str]:
    """Get phone images"""
    url = f"https://tkphsp2.vercel.app/gsm/images/{phone_id}"
    data = fetch_with_timeout(url)
    return data.get('images', []) if data else []

def download_image(url: str) -> Optional[Image.Image]:
    """Download image and fix transparency"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Convert to RGB to avoid transparency issues
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                return background
            return img.convert('RGB')
    except:
        return None
    return None

def download_icon(url: str, size: tuple = (50, 50)) -> Optional[Image.Image]:
    """Download and resize icon"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
    except:
        return None
    return None

# ==========================================
# IMPROVED SPEC PARSER
# ==========================================

def extract_storage(memory_data: List) -> str:
    """Extract storage information - IMPROVED"""
    storage = "N/A"
    
    for mem in memory_data:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            val = str(mem.get("value", "")).upper()
            
            # Pattern 1: "128GB" or "256GB" standalone
            simple_match = re.search(r'(\d+)\s*GB', val)
            if simple_match and "RAM" not in val:
                storage = f"{simple_match.group(1)}GB"
            
            # Pattern 2: "128GB/256GB/512GB" multiple options
            multi_match = re.findall(r'(\d+)\s*GB', val)
            if len(multi_match) > 1:
                # Skip first if it looks like RAM (e.g., "8GB/128GB")
                storage_vals = multi_match[1:] if len(multi_match[1:]) > 0 else multi_match
                storage = "/".join([f"{s}GB" for s in storage_vals[:3]])
            
            # Pattern 3: Storage mentioned with ROM
            rom_match = re.search(r'ROM\s*[:\-]?\s*(\d+)\s*GB', val)
            if rom_match:
                storage = f"{rom_match.group(1)}GB"
            
            # Pattern 4: Common storage sizes
            if "128GB" in val and storage == "N/A":
                storage = "128GB"
            elif "256GB" in val and storage == "N/A":
                storage = "256GB"
            elif "512GB" in val and storage == "N/A":
                storage = "512GB"
            elif "64GB" in val and storage == "N/A":
                storage = "64GB"
    
    return storage

def parse_phone_specs(raw_data: dict) -> Dict[str, Any]:
    """Parse phone specs from API response"""
    specs = {
        "name": raw_data.get("name", "Unknown Phone"),
        "id": raw_data.get("id", ""),
        "image": raw_data.get("image", ""),
    }
    
    # Screen
    display = raw_data.get("display", {})
    size = display.get("size", "")
    resolution = display.get("resolution", "")
    
    # Extract screen size
    inch_match = re.search(r'(\d+\.?\d*)\s*["]?inches', str(size), re.IGNORECASE)
    inches = inch_match.group(1) if inch_match else ""
    
    # Extract resolution
    res_match = re.search(r'(\d+)\s*x\s*(\d+)', str(resolution))
    pixels = f"{res_match.group(1)} x {res_match.group(2)}" if res_match else ""
    
    if inches and pixels:
        specs["screen"] = f"{inches} inch ({pixels})"
    elif inches:
        specs["screen"] = f"{inches} inch"
    elif pixels:
        specs["screen"] = pixels
    else:
        specs["screen"] = "N/A"
    
    # Memory (RAM)
    memory = raw_data.get("memory", [])
    ram = "N/A"
    
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            val = str(mem.get("value", "")).upper()
            
            # Find RAM
            ram_patterns = [
                r'(\d+)\s*GB\s+RAM',
                r'RAM\s*:\s*(\d+)\s*GB',
                r'^(\d+)\s*GB\s*/\s*\d+',
                r'(\d+)\s*GB.*RAM'
            ]
            
            for pattern in ram_patterns:
                match = re.search(pattern, val)
                if match:
                    ram = f"{match.group(1)}GB"
                    break
    
    specs["ram"] = ram
    
    # Storage - using improved function
    specs["storage"] = extract_storage(memory)
    
    # Camera
    camera = raw_data.get("mainCamera", {})
    camera_modules = camera.get("mainModules", "N/A")
    if isinstance(camera_modules, str) and "MP" in camera_modules.upper():
        mp_values = re.findall(r'(\d+\.?\d*)\s*MP', camera_modules.upper())
        if mp_values:
            # Take first 2 camera specs
            if len(mp_values) >= 2:
                specs["camera"] = f"{mp_values[0]}MP + {mp_values[1]}MP"
            else:
                specs["camera"] = f"{mp_values[0]}MP"
        else:
            specs["camera"] = "N/A"
    else:
        specs["camera"] = "N/A"
    
    # Other specs
    specs["battery"] = raw_data.get("battery", {}).get("battType", "N/A")
    specs["chipset"] = raw_data.get("platform", {}).get("chipset", "N/A")
    specs["os"] = raw_data.get("platform", {}).get("os", "N/A")
    
    # Launch info
    launch = raw_data.get("launced", {})
    specs["launch_date"] = launch.get("announced", launch.get("status", "N/A"))
    
    return specs

# ==========================================
# MARKETING CONTENT GENERATOR
# ==========================================

def generate_marketing_posts(phone_specs: Dict) -> Dict[str, str]:
    """Generate professional marketing posts"""
    name = phone_specs["name"]
    
    # Choose key specs for highlighting
    key_features = []
    if phone_specs.get("camera") != "N/A":
        key_features.append(phone_specs["camera"])
    if phone_specs.get("screen") != "N/A":
        key_features.append(phone_specs["screen"])
    if phone_specs.get("storage") != "N/A":
        key_features.append(f"{phone_specs['storage']} storage")
    
    feature_text = " | ".join(key_features[:2])
    
    posts = {
        "facebook": f"""NEW ARRIVAL AT TRIPPLE K COMMUNICATIONS!

{name} is now in stock!

This premium device features {feature_text} and delivers exceptional performance for both work and entertainment.

Why choose Tripple K?
• 1-Year Official Warranty
• Free Delivery in Nairobi
• 100% Genuine Products
• Professional Setup & Support

Get yours today and experience the perfect blend of style and functionality.

Contact us now:
Phone/WhatsApp: {TRIPPLEK_PHONE}
Visit: {TRIPPLEK_URL}
Location: {TRIPPLEK_LOCATION}

#TrippleKCommunications #PhoneDealsNairobi #GenuinePhones #TechKenya #MobilePhones""",
        
        "instagram": f"""JUST ARRIVED: {name}

Now available at Tripple K Communications!

Key Features:
• {key_features[0] if len(key_features) > 0 else 'Premium specifications'}
• {key_features[1] if len(key_features) > 1 else 'Advanced technology'}

Tripple K Benefits:
✓ Official Warranty
✓ Free Delivery
✓ Professional Service

Swipe up for details or DM for pricing.

Tripple K Communications
{TRIPPLEK_PHONE}
{TRIPPLEK_LOCATION}

#TrippleK #PhoneNairobi #TechStore #GadgetShop #KenyaBusiness""",
        
        "whatsapp": f"""*PHONE ALERT - TRIOPLE K COMMUNICATIONS*

*{name}* now available!

Key Specifications:
• {phone_specs.get('screen', 'Premium display')}
• {phone_specs.get('camera', 'Advanced camera system')}
• {phone_specs.get('storage', 'Ample storage')}

*Tripple K Guarantee:*
✅ 1-Year Official Warranty
✅ Free Nairobi Delivery
✅ 100% Genuine Products
✅ Professional Setup

*Location:* {TRIPPLEK_LOCATION}
*Contact:* {TRIPPLEK_PHONE}

Limited stock available. Message us now to reserve your unit!

*Tripple K Communications - Your Trusted Phone Partner*"""
    }
    
    return posts

# ==========================================
# ENHANCED AD GENERATOR WITH ICONS
# ==========================================

def create_whatsapp_ad(phone_specs: Dict, phone_image_url: str, price: str = "") -> Image.Image:
    """Create WhatsApp ad with icons and branding"""
    width, height = 1080, 1920  # WhatsApp story format
    
    # Create gradient background
    base = Image.new('RGB', (width, height), BRAND_MAROON)
    
    # Add subtle gradient
    for y in range(height):
        factor = y / height
        r = min(255, int(139 + (100 * factor)))
        g = 0
        b = 0
        for x in range(width):
            base.putpixel((x, y), (r, g, b))
    
    draw = ImageDraw.Draw(base)
    
    # Load fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 60)
        header_font = ImageFont.truetype("arial.ttf", 42)
        body_font = ImageFont.truetype("arial.ttf", 32)
        price_font = ImageFont.truetype("arial.ttf", 72)
        cta_font = ImageFont.truetype("arial.ttf", 38)
        small_font = ImageFont.truetype("arial.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        price_font = ImageFont.load_default()
        cta_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Download logo
    logo = download_icon(LOGO_URL, (200, 60))
    
    # Header section
    draw.rectangle([0, 0, width, 180], fill=BRAND_MAROON)
    
    if logo:
        base.paste(logo, (width//2 - 100, 60), logo)
    
    # Brand name
    draw.text((width//2, 130), "TRIPPLE K COMMUNICATIONS", 
              fill=BRAND_GOLD, font=header_font, anchor="mm")
    
    # Phone name
    draw.text((width//2, 220), phone_specs["name"], 
              fill=BRAND_WHITE, font=title_font, anchor="mm")
    
    # Phone image
    y_offset = 280
    if phone_image_url:
        phone_img = download_image(phone_image_url)
        if phone_img:
            # Resize and add shadow
            phone_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
            
            # Create shadow
            shadow = Image.new('RGBA', (phone_img.width + 20, phone_img.height + 20), (0,0,0,100))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
            
            x_pos = (width - phone_img.width) // 2
            base.paste(shadow, (x_pos - 10, y_offset + 10), shadow)
            base.paste(phone_img, (x_pos, y_offset))
            y_offset += phone_img.height + 40
    
    # Price tag (if provided)
    if price:
        # Draw price background
        price_width = 400
        price_height = 80
        price_x = (width - price_width) // 2
        price_y = y_offset
        
        draw.rounded_rectangle([price_x, price_y, price_x + price_width, price_y + price_height], 
                              radius=20, fill=BRAND_GOLD, outline=BRAND_MAROON, width=4)
        
        draw.text((width//2, price_y + price_height//2), f"KES {price}", 
                  fill=BRAND_MAROON, font=price_font, anchor="mm")
        
        y_offset += price_height + 40
    
    # Key specs with icons
    specs_y = y_offset
    
    # Create specs container
    specs_height = 300
    draw.rectangle([50, specs_y, width-50, specs_y + specs_height], 
                   fill=BRAND_WHITE, outline=BRAND_GOLD, width=3)
    
    # Draw specs grid
    specs = [
        ("screen", "Screen", phone_specs.get("screen", "N/A")),
        ("camera", "Camera", phone_specs.get("camera", "N/A")),
        ("storage", "Storage", phone_specs.get("storage", "N/A")),
        ("battery", "Battery", phone_specs.get("battery", "N/A")),
    ]
    
    # Position specs in 2x2 grid
    box_width = (width - 100) // 2
    box_height = specs_height // 2
    
    for i, (icon_name, label, value) in enumerate(specs):
        if i < 2:
            x = 50
            y = specs_y + (i * box_height)
        else:
            x = 50 + box_width
            y = specs_y + ((i-2) * box_height)
        
        # Draw icon
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (40, 40))
            if icon:
                base.paste(icon, (x + 30, y + 30), icon)
        
        # Draw label and value
        draw.text((x + 90, y + 25), label, fill=BRAND_MAROON, font=body_font)
        draw.text((x + 90, y + 65), value if value != "N/A" else "Premium", 
                  fill="#333", font=small_font)
    
    y_offset = specs_y + specs_height + 40
    
    # Benefits section
    benefits_y = y_offset
    
    # Benefits header
    draw.text((width//2, benefits_y), "WHY BUY FROM US?", 
              fill=BRAND_GOLD, font=header_font, anchor="mm")
    
    benefits_y += 60
    
    # Benefits with icons
    benefits = [
        ("warranty", "1-Year Official Warranty"),
        ("delivery", "Free Nairobi Delivery"),
        ("call", "Professional Support"),
    ]
    
    for i, (icon_name, text) in enumerate(benefits):
        y = benefits_y + (i * 70)
        
        # Draw icon
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (35, 35))
            if icon:
                base.paste(icon, (width//2 - 200, y), icon)
        
        # Draw text
        draw.text((width//2 - 150, y + 17), text, 
                  fill=BRAND_WHITE, font=small_font, anchor="lm")
    
    benefits_y += 210
    
    # Location with icon
    location_icon = download_icon(ICON_URLS["location"], (30, 30))
    if location_icon:
        base.paste(location_icon, (width//2 - 200, benefits_y), location_icon)
    
    draw.text((width//2 - 160, benefits_y + 15), TRIPPLEK_LOCATION, 
              fill=BRAND_WHITE, font=small_font, anchor="lm")
    
    benefits_y += 50
    
    # Contact section
    contact_y = benefits_y
    
    # Call icon
    call_icon = download_icon(ICON_URLS["call"], (35, 35))
    if call_icon:
        base.paste(call_icon, (width//2 - 180, contact_y), call_icon)
    
    draw.text((width//2 - 140, contact_y + 17), f"Call: {TRIPPLEK_PHONE}", 
              fill=BRAND_WHITE, font=small_font, anchor="lm")
    
    # WhatsApp icon
    whatsapp_icon = download_icon(ICON_URLS["whatsapp"], (35, 35))
    if whatsapp_icon:
        base.paste(whatsapp_icon, (width//2 + 20, contact_y), whatsapp_icon)
    
    draw.text((width//2 + 60, contact_y + 17), f"Chat: {TRIPPLEK_PHONE}", 
              fill=BRAND_WHITE, font=small_font, anchor="lm")
    
    contact_y += 70
    
    # CTA Button
    cta_y = height - 150
    draw.rounded_rectangle([width//2 - 200, cta_y, width//2 + 200, cta_y + 80], 
                          radius=20, fill=BRAND_GREEN, outline=BRAND_GOLD, width=3)
    
    draw.text((width//2, cta_y + 40), "ORDER NOW", 
              fill=BRAND_WHITE, font=cta_font, anchor="mm")
    
    return base

# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    # Creative Header
    st.markdown("""
    <div class="header-container">
        <h1 style="margin: 0; font-size: 3rem;">📱 Tripple K Marketing Suite</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.3rem; opacity: 0.9;">
            Create Professional Phone Marketing Content
        </p>
        <div style="margin-top: 1.5rem; display: flex; justify-content: center; gap: 20px;">
            <span style="background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 20px;">📱 Genuine Phones</span>
            <span style="background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 20px;">✓ Official Warranty</span>
            <span style="background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 20px;">🚚 Free Delivery</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'phone_specs' not in st.session_state:
        st.session_state.phone_specs = None
    if 'phone_images' not in st.session_state:
        st.session_state.phone_images = []
    if 'price' not in st.session_state:
        st.session_state.price = ""
    
    # Create tabs with creative layout
    tab1, tab2, tab3 = st.tabs(["🔍 Phone Search", "📝 Content Creator", "🎨 Ad Designer"])
    
    # TAB 1: PHONE SEARCH
    with tab1:
        st.markdown("### Find Phone Specifications")
        
        # Search section
        col_search, col_btn = st.columns([3, 1])
        with col_search:
            search_query = st.text_input(
                "Enter phone model:", 
                placeholder="e.g., Samsung Galaxy S23 Ultra, iPhone 15 Pro Max",
                key="search_input"
            )
        with col_btn:
            search_btn = st.button("🔍 Search Database", type="primary", use_container_width=True)
        
        if search_btn and search_query:
            with st.spinner("Searching phone database..."):
                results = search_phones(search_query)
                
                if results:
                    st.success(f"✅ Found {len(results)} phone(s)")
                    
                    # Phone selection
                    phone_names = [r.get('name', 'Unknown') for r in results]
                    selected_name = st.selectbox("Select a phone:", phone_names, key="phone_select")
                    
                    if selected_name:
                        selected_phone = next(r for r in results if r['name'] == selected_name)
                        
                        with st.spinner("Fetching specifications..."):
                            # Get phone details
                            details = get_phone_details(selected_phone['id'])
                            
                            if details:
                                # Parse specs
                                specs = parse_phone_specs(details)
                                
                                # Get phone images
                                images = get_phone_images(selected_phone['id'])
                                
                                # Store in session state
                                st.session_state.phone_specs = specs
                                st.session_state.phone_images = images
                                
                                # Display phone info in creative layout
                                st.markdown(f"## {specs['name']}")
                                
                                # Specs in grid
                                st.markdown("### 📊 Specifications")
                                st.markdown('<div class="specs-grid">', unsafe_allow_html=True)
                                
                                spec_items = [
                                    ("🖥️ Screen", specs.get('screen', 'N/A')),
                                    ("📸 Camera", specs.get('camera', 'N/A')),
                                    ("⚡ RAM", specs.get('ram', 'N/A')),
                                    ("💾 Storage", specs.get('storage', 'N/A')),
                                    ("🔋 Battery", specs.get('battery', 'N/A')),
                                    ("🚀 Chipset", specs.get('chipset', 'N/A')),
                                    ("🪟 OS", specs.get('os', 'N/A')),
                                    ("📅 Launch", specs.get('launch_date', 'N/A')),
                                ]
                                
                                cols = st.columns(2)
                                for idx, (label, value) in enumerate(spec_items):
                                    with cols[idx % 2]:
                                        st.markdown(f"""
                                        <div class="spec-card">
                                            <strong>{label}</strong><br>
                                            <span style="color: #555; font-size: 0.95em;">{value}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Phone images after specs
                                if images:
                                    st.markdown("### 📸 Phone Gallery")
                                    st.markdown('<div class="image-gallery">', unsafe_allow_html=True)
                                    
                                    cols = st.columns(3)
                                    for idx, img_url in enumerate(images[:3]):
                                        with cols[idx]:
                                            try:
                                                img = download_image(img_url)
                                                if img:
                                                    st.image(img, use_container_width=True, 
                                                            caption=f"Image {idx+1}")
                                            except:
                                                st.error("Could not load image")
                                    
                                    st.markdown('</div>', unsafe_allow_html=True)
                                    
                                    # Success message
                                    st.success("✅ Phone details loaded successfully!")
                                    st.info("Now proceed to Content Creator or Ad Designer tabs")
                else:
                    st.error("❌ No phones found. Try a different search term.")
    
    # TAB 2: CONTENT CREATOR
    with tab2:
        st.markdown("### Generate Marketing Content")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone in the Phone Search tab")
        else:
            phone_specs = st.session_state.phone_specs
            
            # Generate content button
            if st.button("✨ Generate All Marketing Content", type="primary", use_container_width=True):
                with st.spinner("Creating professional content..."):
                    posts = generate_marketing_posts(phone_specs)
                    
                    # Display posts in creative containers
                    platforms = [
                        ("Facebook Post", "facebook"),
                        ("Instagram Post", "instagram"),
                        ("WhatsApp Message", "whatsapp")
                    ]
                    
                    for platform_name, platform_key in platforms:
                        st.markdown(f'<div class="platform-tab">{platform_name}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="post-container">', unsafe_allow_html=True)
                        st.write(posts[platform_key])
                        
                        # Copy button
                        col_copy, col_space = st.columns([1, 3])
                        with col_copy:
                            if st.button(f"📋 Copy {platform_name}", key=f"copy_{platform_key}"):
                                try:
                                    pyperclip.copy(posts[platform_key])
                                    st.success("✅ Copied to clipboard!")
                                except:
                                    st.info("📝 Text ready for manual copying")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 3: AD DESIGNER
    with tab3:
        st.markdown("### Design Marketing Ad")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone")
        elif not st.session_state.phone_images:
            st.info("⚠️ No images available for this phone")
        else:
            phone_specs = st.session_state.phone_specs
            phone_images = st.session_state.phone_images
            
            # Price input
            col_price, col_image = st.columns(2)
            with col_price:
                price = st.text_input("Enter price (KES):", 
                                     placeholder="e.g., 45,999",
                                     help="Price will be displayed on the ad")
                st.session_state.price = price
            
            with col_image:
                selected_image = st.selectbox("Select main image:", 
                                             [f"Image {i+1}" for i in range(min(3, len(phone_images)))])
            
            # Benefits reminder
            st.markdown("### 🎯 Key Benefits (Included in Ad)")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                <div class="benefit-item">
                <strong>✓ Official Warranty</strong><br>
                1-Year Manufacturer Warranty
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown("""
                <div class="benefit-item">
                <strong>✓ Free Delivery</strong><br>
                Free Nairobi Delivery Service
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown("""
                <div class="benefit-item">
                <strong>✓ Genuine Products</strong><br>
                100% Original & Authentic
                </div>
                """, unsafe_allow_html=True)
            
            # Generate ad button
            if st.button("🎨 Generate WhatsApp Ad", type="primary", use_container_width=True):
                with st.spinner("Designing professional ad..."):
                    # Get selected image index
                    img_idx = int(selected_image.split()[-1]) - 1
                    main_image_url = phone_images[img_idx]
                    
                    # Create ad
                    ad_image = create_whatsapp_ad(phone_specs, main_image_url, price)
                    
                    # Display ad
                    st.markdown("### 🖼️ Ad Preview")
                    col_ad, col_info = st.columns([2, 1])
                    
                    with col_ad:
                        st.image(ad_image, use_container_width=True, 
                                caption="WhatsApp Marketing Ad (1080x1920)")
                    
                    with col_info:
                        st.markdown("### 📋 Ad Features")
                        st.markdown("""
                        **✅ Includes:**
                        - Tripple K Logo
                        - Phone Specifications with Icons
                        - Price Display (if provided)
                        - Key Benefits with Icons
                        - Contact Information
                        - Location Details
                        - Professional CTA Button
                        
                        **🎯 Best For:**
                        - WhatsApp Status
                        - Social Media Posts
                        - Customer Broadcasts
                        - Print Materials
                        """)
                    
                    # Download section
                    st.markdown("---")
                    st.markdown("### 📥 Download Ad")
                    
                    # Convert to bytes
                    buf = BytesIO()
                    ad_image.save(buf, format="PNG", quality=100)
                    img_bytes = buf.getvalue()
                    
                    col_dl, col_tips = st.columns([1, 2])
                    with col_dl:
                        st.download_button(
                            label="⬇️ Download High-Quality PNG",
                            data=img_bytes,
                            file_name=f"tripplek_{phone_specs['name'].replace(' ', '_')}_ad.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    
                    with col_tips:
                        with st.expander("📝 Usage Tips"):
                            st.markdown("""
                            **Optimal Usage:**
                            1. **WhatsApp Status:** Upload as status (24-hour visibility)
                            2. **Social Media:** Post on Facebook/Instagram
                            3. **Broadcast:** Send to customer groups
                            4. **Print:** Use for flyers or posters
                            
                            **Best Posting Times:**
                            - Weekdays: 11 AM - 2 PM
                            - Weekends: 10 AM - 4 PM
                            
                            **Call to Action:**
                            - Include your contact number in caption
                            - Mention delivery areas
                            - Specify warranty terms
                            """)

    # Creative Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <div style="display: flex; justify-content: center; align-items: center; gap: 30px; margin-bottom: 1rem;">
            <div style="text-align: left;">
                <h4 style="color: {BRAND_MAROON}; margin: 0;">Tripple K Communications</h4>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📍 Location:</strong> {TRIPPLEK_LOCATION}
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>📞 Contact:</strong> {TRIPPLEK_PHONE}
                </p>
                <p style="margin: 5px 0; color: #666;">
                    <strong>🌐 Website:</strong> {TRIPPLEK_URL}
                </p>
            </div>
            <div style="background: {BRAND_MAROON}; padding: 15px; border-radius: 10px; color: white;">
                <p style="margin: 0; font-weight: bold;">🎯 Our Promise</p>
                <p style="margin: 5px 0 0 0; font-size: 0.9em;">
                    100% Genuine • Free Delivery • Official Warranty
                </p>
            </div>
        </div>
        <p style="color: #888; font-size: 0.9rem;">
            Professional Phone Marketing Suite • Version 5.0 • Designed for Tripple K Communications
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()