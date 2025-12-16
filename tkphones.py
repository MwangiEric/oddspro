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
BRAND_BLACK = "#222222"

# Brand info
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "www.tripplek.co.ke"
TRIPPLEK_LOCATION = "Moi Avenue Opposite MKU Towers"
SOCIAL_HANDLE = "Tripple K Communications"

# Logo URL (adjust size in download function)
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
    "facebook": "https://ik.imagekit.io/ericmwangi/facebook.png",
    "instagram": "https://ik.imagekit.io/ericmwangi/instagram.png",
    "twitter": "https://ik.imagekit.io/ericmwangi/x.png",
    "tiktok": "https://ik.imagekit.io/ericmwangi/tiktok.png",
    "offer": "https://cdn-icons-png.flaticon.com/512/411/411746.png",
}

# CSS Styling
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    .main {{
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    }}
    
    .header-gradient {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #6b0000 100%);
        padding: 3rem 2.5rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        margin-bottom: 2.5rem;
        box-shadow: 0 20px 40px rgba(139, 0, 0, 0.25);
        font-family: 'Poppins', sans-serif;
        position: relative;
        overflow: hidden;
    }}
    
    .header-gradient::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="none"/><path d="M20,20 Q50,10 80,20 T100,50 T80,80 T50,90 T20,80 T0,50 T20,20 Z" fill="white" opacity="0.05"/></svg>');
        opacity: 0.3;
    }}
    
    .spec-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin: 2rem 0;
    }}
    
    .spec-tile {{
        background: white;
        border-radius: 18px;
        padding: 1.8rem;
        box-shadow: 0 12px 30px rgba(139, 0, 0, 0.08);
        border: 2px solid rgba(139, 0, 0, 0.05);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-family: 'Poppins', sans-serif;
        position: relative;
        overflow: hidden;
    }}
    
    .spec-tile::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 6px;
        height: 100%;
        background: linear-gradient(to bottom, {BRAND_MAROON}, {BRAND_GOLD});
    }}
    
    .spec-tile:hover {{
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 45px rgba(139, 0, 0, 0.15);
        border-color: rgba(139, 0, 0, 0.1);
    }}
    
    .image-showcase {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 30px;
        margin: 3rem 0;
    }}
    
    .showcase-card {{
        border-radius: 22px;
        overflow: hidden;
        box-shadow: 0 20px 45px rgba(0,0,0,0.15);
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        background: white;
        padding: 15px;
        position: relative;
    }}
    
    .showcase-card::after {{
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(to right, {BRAND_MAROON}, {BRAND_GOLD});
        border-radius: 0 0 22px 22px;
    }}
    
    .showcase-card:hover {{
        transform: translateY(-15px) rotate(1deg);
        box-shadow: 0 30px 60px rgba(139, 0, 0, 0.25);
    }}
    
    .tab-wrapper {{
        background: white;
        border-radius: 24px;
        padding: 2.5rem;
        margin: 2rem 0;
        box-shadow: 0 15px 35px rgba(0,0,0,0.06);
        border: 1px solid rgba(139, 0, 0, 0.08);
    }}
    
    .platform-label {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        padding: 1rem 2.2rem;
        border-radius: 35px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1.8rem;
        font-family: 'Poppins', sans-serif;
        box-shadow: 0 8px 25px rgba(139, 0, 0, 0.25);
        position: relative;
        overflow: hidden;
    }}
    
    .platform-label::after {{
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        transform: rotate(45deg);
        animation: shimmer 3s infinite;
    }}
    
    @keyframes shimmer {{
        0% {{ transform: rotate(45deg) translateX(-50%) translateY(-50%); }}
        100% {{ transform: rotate(45deg) translateX(50%) translateY(50%); }}
    }}
    
    .price-badge {{
        background: linear-gradient(135deg, {BRAND_GOLD} 0%, #ffed4e 100%);
        color: {BRAND_MAROON};
        padding: 1.2rem 2.5rem;
        border-radius: 30px;
        font-weight: 800;
        font-size: 2rem;
        display: inline-block;
        margin: 2rem 0;
        box-shadow: 0 12px 30px rgba(255, 215, 0, 0.35);
        font-family: 'Poppins', sans-serif;
        border: 3px solid white;
        position: relative;
        z-index: 1;
    }}
    
    .benefit-pill {{
        background: linear-gradient(135deg, {BRAND_GREEN}15 0%, #e8f5e8 100%);
        padding: 1.5rem;
        border-radius: 20px;
        margin: 1rem 0;
        border: 2px solid {BRAND_GREEN}40;
        font-family: 'Poppins', sans-serif;
        transition: all 0.3s ease;
    }}
    
    .benefit-pill:hover {{
        transform: translateX(10px);
        box-shadow: 0 10px 25px rgba(0, 128, 0, 0.1);
    }}
    
    .stButton > button {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        border: none;
        padding: 16px 36px;
        border-radius: 15px;
        font-weight: 600;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 10px 30px rgba(139, 0, 0, 0.3);
        font-family: 'Poppins', sans-serif;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 15px 40px rgba(139, 0, 0, 0.4);
    }}
    
    .feature-highlight {{
        background: linear-gradient(135deg, rgba(139,0,0,0.05) 0%, rgba(255,215,0,0.05) 100%);
        padding: 2rem;
        border-radius: 20px;
        border-left: 5px solid {BRAND_MAROON};
        margin: 1.5rem 0;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# UTILITY FUNCTIONS
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
    """Download image and fix transparency issues"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Convert RGBA to RGB to avoid transparency issues
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                return background
            return img.convert('RGB')
    except Exception as e:
        st.error(f"Image download error: {str(e)}")
    return None

def download_icon(url: str, size: tuple = (60, 60)) -> Optional[Image.Image]:
    """Download and resize icon with proper transparency handling"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Keep transparency for icons
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create new image with proper size
            result = Image.new('RGBA', size, (255, 255, 255, 0))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Center the icon
            x = (size[0] - img.width) // 2
            y = (size[1] - img.height) // 2
            result.paste(img, (x, y), img)
            return result
    except:
        # Create fallback colored icon
        result = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(result)
        draw.ellipse([0, 0, size[0], size[1]], fill=BRAND_MAROON)
        return result
    return None

def get_logo(size: tuple = (250, 250)) -> Optional[Image.Image]:
    """Download and resize logo to proper size (top-left placement)"""
    try:
        response = requests.get(LOGO_URL, timeout=15)
        if response.status_code == 200:
            logo = Image.open(BytesIO(response.content))
            
            # Handle transparency
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Resize while maintaining aspect ratio
            logo.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create new image with proper size
            result = Image.new('RGBA', size, (255, 255, 255, 0))
            
            # Center the logo in the canvas
            x = (size[0] - logo.width) // 2
            y = (size[1] - logo.height) // 2
            result.paste(logo, (x, y), logo)
            
            return result
    except Exception as e:
        # Create simple logo as fallback
        img = Image.new('RGBA', size, BRAND_MAROON)
        draw = ImageDraw.Draw(img)
        try:
            font = get_font(60, "bold")
        except:
            font = ImageFont.load_default()
        draw.text((size[0]//2, size[1]//2), "TK", fill=BRAND_GOLD, font=font, anchor="mm")
        return img
    return None

# ==========================================
# FONT MANAGEMENT
# ==========================================

def get_font(size: int, weight: str = "regular"):
    """Get Poppins font with fallback"""
    try:
        # Try different font paths for Poppins
        font_paths = [
            "poppins.ttf",
            "Poppins-Regular.ttf",
            "/usr/share/fonts/truetype/poppins/Poppins-Regular.ttf",
            "/System/Library/Fonts/Poppins.ttf",
            "C:/Windows/Fonts/poppins.ttf"
        ]
        
        for path in font_paths:
            try:
                if weight == "bold":
                    return ImageFont.truetype(path.replace("Regular", "Bold").replace("poppins", "Poppins-Bold"), size)
                elif weight == "semibold":
                    return ImageFont.truetype(path.replace("Regular", "SemiBold").replace("poppins", "Poppins-SemiBold"), size)
                elif weight == "medium":
                    return ImageFont.truetype(path.replace("Regular", "Medium").replace("poppins", "Poppins-Medium"), size)
                else:
                    return ImageFont.truetype(path, size)
            except:
                continue
    except:
        pass
    
    # Fallback to default with size adjustment
    default_font = ImageFont.load_default()
    return default_font

# ==========================================
# IMPROVED SPEC PARSER
# ==========================================

def parse_phone_specs(raw_data: dict) -> Dict[str, Any]:
    """Parse phone specs from API response"""
    specs = {
        "name": raw_data.get("name", "Unknown Phone"),
        "id": raw_data.get("id", ""),
        "image": raw_data.get("image", ""),
    }
    
    # Screen - enhanced parsing
    display = raw_data.get("display", {})
    size = display.get("size", "")
    resolution = display.get("resolution", "")
    
    # Extract screen size with better pattern matching
    size_match = re.search(r'(\d+\.?\d*)\s*["]?inches?', str(size), re.IGNORECASE)
    inches = size_match.group(1) if size_match else ""
    
    # Extract resolution
    res_match = re.search(r'(\d+)\s*[x×]\s*(\d+)', str(resolution))
    if res_match:
        pixels = f"{res_match.group(1)} × {res_match.group(2)}"
        specs["screen"] = f'{inches}" {pixels}' if inches else pixels
    else:
        specs["screen"] = f'{inches}"' if inches else "N/A"
    
    # Memory (RAM & Storage) - enhanced extraction
    memory = raw_data.get("memory", [])
    ram, storage = "N/A", "N/A"
    
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            val = str(mem.get("value", "")).upper()
            
            # RAM patterns
            ram_patterns = [
                r'(\d+)\s*GB\s+RAM',
                r'RAM\s*[:\-]?\s*(\d+)\s*GB',
                r'^(\d+)\s*GB\s*[/\|]\s*\d+',
                r'(\d+)\s*GB.*?RAM'
            ]
            
            for pattern in ram_patterns:
                match = re.search(pattern, val, re.IGNORECASE)
                if match:
                    ram = f"{match.group(1)}GB"
                    break
            
            # Storage patterns - comprehensive
            storage_patterns = [
                r'(\d+)\s*GB\s+(?:ROM|STORAGE|Internal)',
                r'ROM\s*[:\-]?\s*(\d+)\s*GB',
                r'[/\|]\s*(\d+)\s*GB(?!.*RAM)',
                r'(\d+)\s*GB$',
                r'STORAGE\s*[:\-]?\s*(\d+)\s*GB'
            ]
            
            # Also check for common storage sizes
            common_sizes = ["512GB", "256GB", "128GB", "64GB", "32GB"]
            for size in common_sizes:
                if size in val and "RAM" not in val.upper():
                    storage = size
                    break
            
            if storage == "N/A":
                for pattern in storage_patterns:
                    match = re.search(pattern, val, re.IGNORECASE)
                    if match:
                        storage = f"{match.group(1)}GB"
                        break
    
    specs["ram"] = ram
    specs["storage"] = storage if storage != "N/A" else "128GB"  # Default fallback
    
    # Camera - improved parsing
    camera = raw_data.get("mainCamera", {})
    camera_modules = camera.get("mainModules", "N/A")
    if isinstance(camera_modules, str) and "MP" in camera_modules.upper():
        # Extract all MP values
        mp_values = re.findall(r'(\d+\.?\d*)\s*MP', camera_modules.upper())
        if mp_values:
            # Take first 2-3 camera specs
            if len(mp_values) >= 3:
                specs["camera"] = f"{mp_values[0]}MP + {mp_values[1]}MP + {mp_values[2]}MP"
            elif len(mp_values) >= 2:
                specs["camera"] = f"{mp_values[0]}MP + {mp_values[1]}MP"
            else:
                specs["camera"] = f"{mp_values[0]}MP"
        else:
            specs["camera"] = "N/A"
    else:
        specs["camera"] = "N/A"
    
    # Other specs with improved formatting
    battery_raw = raw_data.get("battery", {}).get("battType", "N/A")
    specs["battery"] = re.sub(r'\s*\([^)]*\)', '', str(battery_raw))[:20]  # Clean up battery text
    
    chipset_raw = raw_data.get("platform", {}).get("chipset", "N/A")
    # Clean chipset name
    if chipset_raw != "N/A":
        chipset_clean = re.sub(r'\s*\([^)]*\)', '', chipset_raw)
        specs["chipset"] = chipset_clean[:25]  # Limit length
    else:
        specs["chipset"] = "N/A"
    
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
    if phone_specs.get("chipset") != "N/A" and phone_specs["chipset"] != "Unknown":
        key_features.append(phone_specs["chipset"])
    
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
• {key_features[2] if len(key_features) > 2 else 'Powerful performance'}

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
• {phone_specs.get('chipset', 'Powerful processor')}

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
# ENHANCED AD GENERATOR WITH IMPROVED LAYOUT
# ==========================================

def create_whatsapp_ad(phone_specs: Dict, phone_image_url: str, price: str = "") -> Image.Image:
    """Create WhatsApp ad with improved layout and spacing"""
    width, height = 1080, 1920  # WhatsApp story format
    
    # Create clean white background
    base = Image.new('RGB', (width, height), BRAND_WHITE)
    draw = ImageDraw.Draw(base)
    
    # Load fonts with Poppins
    title_font = get_font(52, "bold")  # Phone name
    header_font = get_font(42, "semibold")  # Section headers
    body_font = get_font(32, "medium")  # Spec labels
    spec_font = get_font(28)  # Spec values
    price_font = get_font(72, "bold")  # Price
    cta_font = get_font(44, "bold")  # CTA button
    badge_font = get_font(32, "bold")  # Badges
    small_font = get_font(26)  # Small text
    tiny_font = get_font(22)  # Tiny text
    
    # ==========================================
    # HEADER SECTION - Logo top-left
    # ==========================================
    
    # Add brand color header strip
    header_height = 180
    draw.rectangle([0, 0, width, header_height], fill=BRAND_MAROON)
    
    # Add decorative elements to header
    for i in range(5):
        y = header_height - 30 - (i * 15)
        draw.line([(0, y), (width, y)], fill=BRAND_GOLD, width=2)
    
    # Add logo at top-left (smaller size: 180x180)
    logo = get_logo((180, 180))
    if logo:
        base.paste(logo, (40, 10), logo)
    
    # Brand name beside logo
    brand_x = 240
    draw.text((brand_x, 60), SOCIAL_HANDLE, 
              fill=BRAND_WHITE, font=header_font, anchor="lm")
    draw.text((brand_x, 110), "Premium Phone Retailer", 
              fill=BRAND_GOLD, font=small_font, anchor="lm")
    
    # ==========================================
    # MAIN CONTENT AREA - Two Column Layout
    # ==========================================
    
    content_start = header_height + 40
    
    # Phone name centered
    draw.text((width//2, content_start), phone_specs["name"], 
              fill=BRAND_MAROON, font=title_font, anchor="mm")
    
    # Two columns
    col1_width = width // 2 + 60  # Left column slightly larger for phone
    col2_width = width - col1_width - 60  # Right column for specs
    
    col1_x = 40
    col2_x = col1_x + col1_width + 40
    
    # ==========================================
    # LEFT COLUMN: PHONE IMAGE
    # ==========================================
    
    phone_y = content_start + 80
    
    # Download and display phone image
    if phone_image_url:
        phone_img = download_image(phone_image_url)
        if phone_img:
            # Resize to fit column with generous spacing
            max_phone_height = 750
            phone_img.thumbnail((col1_width - 100, max_phone_height), Image.Resampling.LANCZOS)
            
            # Create shadow effect
            shadow = Image.new('RGBA', (phone_img.width + 60, phone_img.height + 60), (0,0,0,20))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
            
            phone_x = col1_x + (col1_width - phone_img.width) // 2
            
            # Draw phone stand
            stand_height = 40
            stand_width = phone_img.width // 3
            stand_x = phone_x + (phone_img.width - stand_width) // 2
            draw.rounded_rectangle([stand_x, phone_y + phone_img.height, 
                                   stand_x + stand_width, phone_y + phone_img.height + stand_height],
                                  radius=10, fill="#E0E0E0")
            
            # Paste shadow
            base.paste(shadow, (phone_x - 30, phone_y - 30), shadow)
            # Paste phone image
            base.paste(phone_img, (phone_x, phone_y))
            
            image_bottom = phone_y + phone_img.height + stand_height + 40
    
    # ==========================================
    # RIGHT COLUMN: PRICE, BADGES & SPECS
    # ==========================================
    
    right_col_y = content_start + 60
    
    # Price display (if provided)
    if price:
        # Price background
        price_bg_width = col2_width - 40
        price_bg_height = 100
        draw.rounded_rectangle([col2_x, right_col_y, 
                               col2_x + price_bg_width, right_col_y + price_bg_height],
                              radius=25, fill=BRAND_GOLD, outline=BRAND_MAROON, width=4)
        
        # Price text
        draw.text((col2_x + price_bg_width//2, right_col_y + price_bg_height//2),
                  f"KES {price}", fill=BRAND_MAROON, font=price_font, anchor="mm")
        
        right_col_y += price_bg_height + 40
    
    # BADGES SECTION
    badges = [
        ("NEW ARRIVAL", BRAND_MAROON, BRAND_GOLD),
        ("1-YEAR WARRANTY", BRAND_GOLD, BRAND_MAROON),
        ("FREE DELIVERY", BRAND_GREEN, BRAND_WHITE),
        ("BEST OFFER", BRAND_MAROON, BRAND_GOLD),
    ]
    
    badge_height = 75
    badge_spacing = 15
    
    for badge_text, bg_color, text_color in badges:
        # Calculate badge width
        bbox = badge_font.getbbox(badge_text)
        badge_width = bbox[2] - bbox[0] + 80
        
        # Draw badge
        draw.rounded_rectangle([col2_x, right_col_y, 
                               col2_x + badge_width, right_col_y + badge_height],
                              radius=20, fill=bg_color)
        
        # Badge text
        draw.text((col2_x + badge_width//2, right_col_y + badge_height//2),
                  badge_text, fill=text_color, font=badge_font, anchor="mm")
        
        right_col_y += badge_height + badge_spacing
    
    right_col_y += 30
    
    # SPECS SECTION WITH ICONS
    specs_title_y = right_col_y
    draw.text((col2_x + col2_width//2, specs_title_y), "KEY FEATURES", 
              fill=BRAND_MAROON, font=header_font, anchor="mm")
    
    specs_title_y += 70
    
    # Specs with icons - INCLUDING CHIPSET
    specs = [
        ("screen", "Display", phone_specs.get("screen", "Premium")),
        ("camera", "Camera", phone_specs.get("camera", "Advanced")),
        ("storage", "Storage", phone_specs.get("storage", "Ample")),
        ("battery", "Battery", phone_specs.get("battery", "Long-lasting")),
        ("processor", "Chipset", phone_specs.get("chipset", "Powerful")),  # Added chipset
    ]
    
    spec_spacing = 80
    icon_size = 50
    
    for icon_name, label, value in specs:
        # Draw icon
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (icon_size, icon_size))
            if icon:
                base.paste(icon, (col2_x, specs_title_y - icon_size//2), icon)
        
        # Draw label
        draw.text((col2_x + icon_size + 20, specs_title_y), label, 
                  fill=BRAND_MAROON, font=body_font, anchor="lm")
        
        # Draw value (with wrapping for long text)
        if len(value) > 25:
            value = value[:22] + "..."
        draw.text((col2_x + icon_size + 20, specs_title_y + 45), value, 
                  fill=BRAND_BLACK, font=spec_font, anchor="lm")
        
        specs_title_y += spec_spacing
    
    # ==========================================
    # BENEFITS SECTION (Below both columns)
    # ==========================================
    
    benefits_y = max(image_bottom if 'image_bottom' in locals() else 1300, specs_title_y) + 60
    
    # Benefits header
    draw.text((width//2, benefits_y), "WHY CHOOSE TRIOPLE K?", 
              fill=BRAND_MAROON, font=header_font, anchor="mm")
    
    benefits_y += 70
    
    # Benefits in 2x2 grid
    benefits = [
        ("warranty", "Official Warranty", "1-year manufacturer warranty"),
        ("delivery", "Free Delivery", "Free Nairobi delivery service"),
        ("offer", "Best Prices", "Competitive market prices"),
        ("call", "Expert Support", "Professional setup & support"),
    ]
    
    benefit_width = (width - 120) // 2
    benefit_height = 120
    benefit_spacing = 20
    
    for i, (icon_name, title, description) in enumerate(benefits):
        row = i // 2
        col = i % 2
        
        x = 60 + col * (benefit_width + benefit_spacing)
        y = benefits_y + row * (benefit_height + benefit_spacing)
        
        # Draw benefit card
        draw.rounded_rectangle([x, y, x + benefit_width, y + benefit_height],
                              radius=20, fill="#F8F9FA", outline=BRAND_GOLD, width=2)
        
        # Draw icon
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (40, 40))
            if icon:
                base.paste(icon, (x + 20, y + 20), icon)
        
        # Draw title
        draw.text((x + 75, y + 25), title, 
                  fill=BRAND_MAROON, font=body_font, anchor="lm")
        
        # Draw description
        if len(description) > 30:
            description = description[:28] + "..."
        draw.text((x + 75, y + 65), description, 
                  fill="#666", font=small_font, anchor="lm")
    
    benefits_y += (2 * (benefit_height + benefit_spacing)) + 40
    
    # ==========================================
    # CTA BUTTON
    # ==========================================
    
    cta_y = benefits_y
    
    # Draw button with gradient effect
    button_width = 450
    button_height = 100
    button_x = (width - button_width) // 2
    
    # Button background with gradient
    for i in range(button_height):
        factor = i / button_height
        r = int(139 * (1 - factor * 0.3))
        g = int(0 * (1 - factor * 0.3))
        b = int(0 * (1 - factor * 0.3))
        draw.line([(button_x, cta_y + i), (button_x + button_width, cta_y + i)], 
                  fill=(r, g, b))
    
    # Button border and text
    draw.rounded_rectangle([button_x, cta_y, button_x + button_width, cta_y + button_height],
                          radius=25, outline=BRAND_GOLD, width=5)
    
    draw.text((width//2, cta_y + button_height//2), "ORDER NOW", 
              fill=BRAND_WHITE, font=cta_font, anchor="mm")
    
    # ==========================================
    # FOOTER SECTION
    # ==========================================
    
    footer_y = height - 200
    
    # Location with icon
    location_icon = download_icon(ICON_URLS["location"], (35, 35))
    if location_icon:
        base.paste(location_icon, (width//2 - 220, footer_y), location_icon)
    
    draw.text((width//2 - 180, footer_y + 17), TRIPPLEK_LOCATION, 
              fill=BRAND_MAROON, font=small_font, anchor="lm")
    
    # Website
    website_y = footer_y + 50
    draw.text((width//2, website_y), TRIPPLEK_URL, 
              fill=BRAND_MAROON, font=small_font, anchor="mm")
    
    # Social Media Icons
    social_y = website_y + 50
    social_icons = ["facebook", "instagram", "twitter", "tiktok"]
    icon_size = 45
    icon_spacing = 70
    total_width = len(social_icons) * icon_spacing
    start_x = (width - total_width) // 2 + icon_spacing // 2
    
    for i, icon_name in enumerate(social_icons):
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (icon_size, icon_size))
            if icon:
                x_pos = start_x + (i * icon_spacing) - icon_size // 2
                base.paste(icon, (x_pos, social_y), icon)
    
    # Social handle
    social_handle_y = social_y + icon_size + 15
    draw.text((width//2, social_handle_y), f"@{SOCIAL_HANDLE.replace(' ', '').lower()}", 
              fill="#666", font=tiny_font, anchor="mm")
    
    # Contact info at bottom
    bottom_y = height - 50
    draw.text((width//2, bottom_y), f"📞 {TRIPPLEK_PHONE}  •  💬 {TRIPPLEK_PHONE}", 
              fill=BRAND_MAROON, font=get_font(28), anchor="mm")
    
    # Add decorative border
    draw.rectangle([10, 10, width-10, height-10], outline=BRAND_GOLD, width=4)
    
    return base

# ==========================================
# MAIN APPLICATION WITH IMPROVED LAYOUT
# ==========================================

def main():
    # Enhanced Header with Gradient
    st.markdown(f"""
    <div class="header-gradient">
        <h1 style="margin: 0; font-size: 3.5rem; font-weight: 800; letter-spacing: 1px;">📱 Tripple K Marketing Suite</h1>
        <p style="margin: 1.2rem 0 0 0; font-size: 1.5rem; opacity: 0.95; font-weight: 400;">
            Professional Phone Marketing & Content Creation Platform
        </p>
        <div style="margin-top: 2.5rem; display: flex; justify-content: center; gap: 30px; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.25); padding: 12px 28px; border-radius: 30px; font-weight: 500; backdrop-filter: blur(10px);">
                📱 100% Genuine Phones
            </div>
            <div style="background: rgba(255,255,255,0.25); padding: 12px 28px; border-radius: 30px; font-weight: 500; backdrop-filter: blur(10px);">
                🛡️ 1-Year Warranty
            </div>
            <div style="background: rgba(255,255,255,0.25); padding: 12px 28px; border-radius: 30px; font-weight: 500; backdrop-filter: blur(10px);">
                🚚 Free Nairobi Delivery
            </div>
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
    
    # Create tabs with icons
    tab1, tab2, tab3 = st.tabs(["🔍 Phone Search", "📝 Content Creator", "🎨 Ad Designer"])
    
    # TAB 1: PHONE SEARCH
    with tab1:
        st.markdown('<div class="tab-wrapper">', unsafe_allow_html=True)
        
        st.markdown("### 📱 Find Phone Specifications")
        st.markdown("Search for any phone model to get detailed specifications and images.")
        
        # Search section
        col_search, col_btn = st.columns([3, 1])
        with col_search:
            search_query = st.text_input(
                "Enter phone model:", 
                placeholder="e.g., Samsung Galaxy S23 Ultra, iPhone 15 Pro Max",
                key="search_input",
                help="Enter the full phone name for best results"
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
                                
                                # Display phone info
                                st.markdown(f"## 📱 {specs['name']}")
                                st.markdown("---")
                                
                                # Specs in enhanced grid
                                st.markdown("### 📊 Specifications")
                                st.markdown('<div class="spec-grid">', unsafe_allow_html=True)
                                
                                spec_items = [
                                    ("Display", specs.get('screen', 'N/A'), "🖥️"),
                                    ("Camera", specs.get('camera', 'N/A'), "📸"),
                                    ("RAM", specs.get('ram', 'N/A'), "⚡"),
                                    ("Storage", specs.get('storage', 'N/A'), "💾"),
                                    ("Battery", specs.get('battery', 'N/A'), "🔋"),
                                    ("Chipset", specs.get('chipset', 'N/A'), "🚀"),
                                    ("OS", specs.get('os', 'N/A'), "🪟"),
                                    ("Launch Date", specs.get('launch_date', 'N/A'), "📅"),
                                ]
                                
                                cols = st.columns(2)
                                for idx, (label, value, icon) in enumerate(spec_items):
                                    with cols[idx % 2]:
                                        st.markdown(f"""
                                        <div class="spec-tile">
                                            <div style="font-size: 1.8rem; margin-bottom: 10px;">{icon}</div>
                                            <strong style="color: {BRAND_MAROON}; font-size: 1.1rem;">{label}</strong><br>
                                            <span style="color: #444; font-size: 1rem; line-height: 1.5;">{value}</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Phone images after specs
                                if images:
                                    st.markdown("### 📸 Phone Gallery")
                                    st.markdown("First 3 images from the phone gallery:")
                                    st.markdown('<div class="image-showcase">', unsafe_allow_html=True)
                                    
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
                                    st.info("👉 Now proceed to Content Creator or Ad Designer tabs")
                else:
                    st.error("❌ No phones found. Try a different search term.")
                    st.markdown("""
                    **Tips for better search:**
                    - Use full phone names (e.g., "Samsung Galaxy S23 Ultra")
                    - Include brand names
                    - Check spelling
                    - Try different variations
                    """)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 2: CONTENT CREATOR
    with tab2:
        st.markdown('<div class="tab-wrapper">', unsafe_allow_html=True)
        st.markdown("### 📝 Generate Marketing Content")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone in the Phone Search tab")
        else:
            phone_specs = st.session_state.phone_specs
            
            # Generate content button
            if st.button("✨ Generate All Marketing Content", type="primary", use_container_width=True):
                with st.spinner("Creating professional content..."):
                    posts = generate_marketing_posts(phone_specs)
                    
                    # Display posts
                    platforms = [
                        ("Facebook Post", "facebook"),
                        ("Instagram Post", "instagram"),
                        ("WhatsApp Message", "whatsapp")
                    ]
                    
                    for platform_name, platform_key in platforms:
                        st.markdown(f'<div class="platform-label">{platform_name}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="feature-highlight">', unsafe_allow_html=True)
                        
                        # Display post content
                        st.text_area(
                            f"{platform_name} Content:",
                            posts[platform_key],
                            height=200,
                            key=f"text_{platform_key}"
                        )
                        
                        # Copy button
                        col_copy, col_clear = st.columns([1, 4])
                        with col_copy:
                            if st.button(f"📋 Copy", key=f"copy_{platform_key}"):
                                try:
                                    pyperclip.copy(posts[platform_key])
                                    st.success("✅ Copied to clipboard!")
                                except:
                                    st.info("📝 Text ready for manual copying")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 3: AD DESIGNER
    with tab3:
        st.markdown('<div class="tab-wrapper">', unsafe_allow_html=True)
        st.markdown("### 🎨 Design Marketing Ad")
        
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
                                     help="Price will be displayed prominently on the ad",
                                     key="price_input")
                st.session_state.price = price
            
            with col_image:
                selected_image = st.selectbox("Select main image:", 
                                             [f"Image {i+1}" for i in range(min(3, len(phone_images)))],
                                             key="image_select")
            
            # Benefits section
            st.markdown("### 🎯 Key Benefits Included in Ad")
            st.markdown('<div class="feature-highlight">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("""
                **🛡️ 1-Year Warranty**  
                Official Manufacturer Warranty
                """)
            with col2:
                st.markdown("""
                **🚚 Free Delivery**  
                Free Nairobi Delivery Service
                """)
            with col3:
                st.markdown("""
                **✅ Genuine Products**  
                100% Original & Authentic
                """)
            with col4:
                st.markdown("""
                **🎯 Best Prices**  
                Competitive Market Prices
                """)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
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
                    
                    # Show ad in two columns
                    col_ad, col_features = st.columns([2, 1])
                    
                    with col_ad:
                        st.image(ad_image, use_container_width=True, 
                                caption="WhatsApp Marketing Ad (1080x1920)")
                    
                    with col_features:
                        st.markdown("### 📋 Ad Features")
                        st.markdown("""
                        **✅ What's Included:**
                        - Tripple K Logo (top-left)
                        - Phone image on left side
                        - Price display (if provided)
                        - 4 key badges
                        - 5 specifications with icons
                        - 4 benefit cards
                        - Professional CTA button
                        - Location & website
                        - Social media icons
                        - Contact information
                        
                        **🎯 Specs Shown:**
                        1. Display
                        2. Camera
                        3. Storage
                        4. Battery
                        5. **Chipset** ✓
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
                        with st.expander("📝 Usage Tips & Best Practices"):
                            st.markdown("""
                            **Optimal Usage Guide:**
                            
                            1. **WhatsApp Status:**  
                               Upload as status for 24-hour visibility  
                               Best posting times: 11 AM - 2 PM, 7 PM - 9 PM
                            
                            2. **Social Media:**  
                               Facebook/Instagram Stories  
                               Twitter posts with shortened link  
                               LinkedIn updates for business clients
                            
                            3. **Marketing Channels:**  
                               Email newsletters  
                               SMS campaigns  
                               Print as flyers/posters  
                               Digital displays in-store
                            
                            **Pro Tips:**
                            - Always include contact number in caption
                            - Mention specific delivery areas
                            - Specify warranty terms clearly
                            - Use relevant hashtags
                            - Tag location for local reach
                            - Include chipset info for tech-savvy customers
                            """)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem 0;">
        <div style="display: flex; justify-content: center; align-items: flex-start; gap: 50px; margin-bottom: 2.5rem; flex-wrap: wrap;">
            <div style="text-align: left; max-width: 450px;">
                <h4 style="color: {BRAND_MAROON}; margin: 0 0 1.2rem 0; font-weight: 700; font-size: 1.4rem;">Tripple K Communications</h4>
                <div style="background: linear-gradient(135deg, {BRAND_MAROON}15 0%, #fff5f5 100%); padding: 1.5rem; border-radius: 20px; border: 2px solid {BRAND_MAROON}20;">
                    <p style="margin: 8px 0; color: #555; font-size: 1rem;">
                        <strong>📍</strong> {TRIPPLEK_LOCATION}
                    </p>
                    <p style="margin: 8px 0; color: #555; font-size: 1rem;">
                        <strong>📞</strong> {TRIPPLEK_PHONE}
                    </p>
                    <p style="margin: 8px 0; color: #555; font-size: 1rem;">
                        <strong>🌐</strong> {TRIPPLEK_URL}
                    </p>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, {BRAND_MAROON} 0%, #6b0000 100%); 
                       padding: 25px; border-radius: 20px; color: white; max-width: 500px;">
                <p style="margin: 0; font-weight: 800; font-size: 1.3rem; margin-bottom: 15px;">🎯 Our Promise</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: left;">
                    <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 10px;">
                        <strong>✓ 100% Genuine</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 10px;">
                        <strong>✓ Free Delivery</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 10px;">
                        <strong>✓ Official Warranty</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 10px;">
                        <strong>✓ Professional Service</strong>
                    </div>
                </div>
            </div>
        </div>
        
        <div style="margin: 2rem 0; padding-top: 2rem; border-top: 2px solid rgba(139,0,0,0.1);">
            <p style="color: {BRAND_MAROON}; font-weight: 600; margin-bottom: 1.2rem; font-size: 1.1rem;">Follow Us: @{SOCIAL_HANDLE.replace(' ', '').lower()}</p>
            <div style="display: flex; justify-content: center; gap: 25px; margin-bottom: 1.5rem;">
                <span style="color: #666; font-weight: 500;">Facebook</span>
                <span style="color: #666; font-weight: 500;">Instagram</span>
                <span style="color: #666; font-weight: 500;">Twitter</span>
                <span style="color: #666; font-weight: 500;">TikTok</span>
            </div>
        </div>
        
        <p style="color: #888; font-size: 0.9rem; margin-top: 2.5rem; padding-top: 1.5rem; border-top: 1px solid rgba(0,0,0,0.05);">
            Professional Phone Marketing Suite • Version 7.0 • Designed for Tripple K Communications
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()