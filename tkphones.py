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
TRIPPLEK_URL = "www.tripplek.co.ke"
TRIPPLEK_LOCATION = "Moi Avenue Opposite MKU Towers"
SOCIAL_HANDLE = "Tripple K Communications"

# Logo and Icon URLs
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

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
}

# CSS Styling
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    .main {{
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    }}
    
    .header-container {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #6b0000 100%);
        padding: 2.5rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        margin-bottom: 2.5rem;
        box-shadow: 0 20px 40px rgba(139, 0, 0, 0.25);
        font-family: 'Poppins', sans-serif;
    }}
    
    .spec-card {{
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 25px rgba(139, 0, 0, 0.1);
        border-left: 5px solid {BRAND_MAROON};
        transition: all 0.3s ease;
        font-family: 'Poppins', sans-serif;
    }}
    
    .spec-card:hover {{
        transform: translateY(-8px);
        box-shadow: 0 15px 35px rgba(139, 0, 0, 0.2);
    }}
    
    .image-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 25px;
        margin: 2.5rem 0;
    }}
    
    .image-preview {{
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        transition: all 0.4s ease;
        background: white;
        padding: 15px;
    }}
    
    .image-preview:hover {{
        transform: scale(1.05) rotate(1deg);
        box-shadow: 0 25px 50px rgba(139, 0, 0, 0.3);
    }}
    
    .tab-container {{
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    }}
    
    .platform-tag {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        padding: 0.8rem 1.8rem;
        border-radius: 30px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1.5rem;
        font-family: 'Poppins', sans-serif;
    }}
    
    .price-display {{
        background: linear-gradient(135deg, {BRAND_GOLD} 0%, #ffed4e 100%);
        color: {BRAND_MAROON};
        padding: 1rem 2rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 1.8rem;
        display: inline-block;
        margin: 1.5rem 0;
        box-shadow: 0 8px 20px rgba(255, 215, 0, 0.3);
        font-family: 'Poppins', sans-serif;
    }}
    
    .benefit-highlight {{
        background: linear-gradient(135deg, {BRAND_GREEN}15 0%, #e8f5e8 100%);
        padding: 1.2rem;
        border-radius: 15px;
        margin: 0.8rem 0;
        border: 2px solid {BRAND_GREEN}30;
        font-family: 'Poppins', sans-serif;
    }}
    
    .stButton > button {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        border: none;
        padding: 14px 32px;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 6px 20px rgba(139, 0, 0, 0.25);
        font-family: 'Poppins', sans-serif;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(139, 0, 0, 0.4);
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

def download_icon(url: str, size: tuple = (50, 50)) -> Optional[Image.Image]:
    """Download and resize icon"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Handle transparency for icons
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # Keep transparency for icons
                img = img.resize(size, Image.Resampling.LANCZOS)
                return img
            else:
                img = img.convert('RGBA').resize(size, Image.Resampling.LANCZOS)
                return img
    except:
        # Create fallback icon
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([0, 0, size[0], size[1]], fill=BRAND_MAROON)
        return img
    return None

def get_logo(size: tuple = (300, 300)) -> Optional[Image.Image]:
    """Download and resize logo to 300x300"""
    try:
        response = requests.get(LOGO_URL, timeout=15)
        if response.status_code == 200:
            logo = Image.open(BytesIO(response.content))
            # Handle logo transparency
            if logo.mode in ('RGBA', 'LA', 'P'):
                if logo.mode == 'P':
                    logo = logo.convert('RGBA')
                # Create white background
                background = Image.new('RGBA', size, (255, 255, 255, 255))
                logo.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Calculate position to center
                x = (size[0] - logo.width) // 2
                y = (size[1] - logo.height) // 2
                
                background.paste(logo, (x, y), logo)
                return background
            else:
                logo.thumbnail(size, Image.Resampling.LANCZOS)
                return logo.convert('RGBA')
    except Exception as e:
        st.error(f"Logo error: {str(e)}")
        # Create simple logo as fallback
        img = Image.new('RGBA', size, BRAND_MAROON)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("poppins.ttf", 60)
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
        # Try different font paths
        font_paths = [
            "poppins.ttf",
            "Poppins-Regular.ttf",
            "/usr/share/fonts/truetype/poppins/Poppins-Regular.ttf",
            "C:/Windows/Fonts/poppins.ttf"
        ]
        
        for path in font_paths:
            try:
                if weight == "bold":
                    return ImageFont.truetype(path.replace("Regular", "Bold"), size)
                elif weight == "semibold":
                    return ImageFont.truetype(path.replace("Regular", "SemiBold"), size)
                else:
                    return ImageFont.truetype(path, size)
            except:
                continue
    except:
        pass
    
    # Fallback to default
    return ImageFont.load_default()

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
    
    # Screen
    display = raw_data.get("display", {})
    size = display.get("size", "")
    resolution = display.get("resolution", "")
    
    # Extract screen size
    inch_match = re.search(r'(\d+\.?\d*)\s*["]?inches', str(size), re.IGNORECASE)
    inches = inch_match.group(1) if inch_match else ""
    
    # Extract resolution
    res_match = re.search(r'(\d+)\s*x\s*(\d+)', str(resolution))
    if res_match:
        pixels = f"{res_match.group(1)} x {res_match.group(2)}"
        specs["screen"] = f"{inches}\" ({pixels})" if inches else pixels
    else:
        specs["screen"] = f"{inches}\"" if inches else "N/A"
    
    # Memory (RAM & Storage)
    memory = raw_data.get("memory", [])
    ram, storage = "N/A", "N/A"
    
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            val = str(mem.get("value", "")).upper()
            
            # Try multiple patterns for RAM
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
            
            # Try multiple patterns for Storage
            storage_patterns = [
                r'(\d+)\s*GB\s+(?:ROM|STORAGE|Internal)',
                r'ROM\s*:\s*(\d+)\s*GB',
                r'/\s*(\d+)\s*GB',
                r'(\d+)\s*GB$'
            ]
            
            # Also look for common storage sizes
            for size in ["512GB", "256GB", "128GB", "64GB", "32GB"]:
                if size in val and "RAM" not in val:
                    storage = size
                    break
            
            if storage == "N/A":
                for pattern in storage_patterns:
                    match = re.search(pattern, val)
                    if match:
                        storage = f"{match.group(1)}GB"
                        break
    
    specs["ram"] = ram
    specs["storage"] = storage if storage != "N/A" else "Premium Storage"
    
    # Camera
    camera = raw_data.get("mainCamera", {})
    camera_modules = camera.get("mainModules", "N/A")
    if isinstance(camera_modules, str) and "MP" in camera_modules.upper():
        mp_values = re.findall(r'(\d+\.?\d*)\s*MP', camera_modules.upper())
        if mp_values:
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
    
    # Key features for highlighting
    key_features = []
    if phone_specs.get("camera") != "N/A":
        key_features.append(phone_specs["camera"])
    if phone_specs.get("screen") != "N/A":
        key_features.append(phone_specs["screen"])
    if phone_specs.get("storage") != "N/A":
        key_features.append(phone_specs["storage"])
    
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
# ENHANCED AD GENERATOR WITH NEW LAYOUT
# ==========================================

def create_whatsapp_ad(phone_specs: Dict, phone_image_url: str, price: str = "") -> Image.Image:
    """Create WhatsApp ad with new layout: Phone on left, badges on right"""
    width, height = 1080, 1920  # WhatsApp story format
    
    # Create gradient background
    base = Image.new('RGB', (width, height), BRAND_WHITE)
    draw = ImageDraw.Draw(base)
    
    # Add subtle gradient overlay
    overlay = Image.new('RGBA', (width, height), (139, 0, 0, 10))
    base = Image.alpha_composite(base.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(base)
    
    # Load fonts
    title_font = get_font(48, "bold")
    header_font = get_font(36, "semibold")
    body_font = get_font(28)
    price_font = get_font(64, "bold")
    cta_font = get_font(40, "bold")
    small_font = get_font(24)
    badge_font = get_font(30, "bold")
    
    # Download and resize logo (300x300)
    logo = get_logo((300, 300))
    
    # HEADER SECTION
    header_height = 180
    draw.rectangle([0, 0, width, header_height], fill=BRAND_MAROON)
    
    # Add logo to header (centered)
    if logo:
        logo_x = (width - 300) // 2
        base.paste(logo, (logo_x, 40), logo if logo.mode == 'RGBA' else None)
    
    # Brand name below logo
    draw.text((width//2, 160), SOCIAL_HANDLE.upper(), 
              fill=BRAND_GOLD, font=header_font, anchor="mm")
    
    # MAIN CONTENT AREA - Split into two columns
    content_y = header_height + 40
    
    # COLUMN 1: PHONE IMAGE (Left - 50%)
    col1_width = width // 2
    col1_x = 40
    
    # Phone name above image
    draw.text((col1_x + col1_width//2, content_y), phone_specs["name"], 
              fill=BRAND_MAROON, font=title_font, anchor="mm")
    
    content_y += 60
    
    # Download and display phone image
    if phone_image_url:
        phone_img = download_image(phone_image_url)
        if phone_img:
            # Resize to fit column (leaving space around)
            max_phone_height = 700
            phone_img.thumbnail((col1_width - 80, max_phone_height), Image.Resampling.LANCZOS)
            
            # Add shadow effect
            shadow = Image.new('RGBA', (phone_img.width + 40, phone_img.height + 40), (0,0,0,30))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
            
            phone_x = col1_x + (col1_width - phone_img.width) // 2
            phone_y = content_y + 20
            
            # Paste shadow
            base.paste(shadow, (phone_x - 20, phone_y - 20), shadow)
            # Paste phone image
            base.paste(phone_img, (phone_x, phone_y))
            
            image_bottom = phone_y + phone_img.height
    
    # COLUMN 2: BADGES & SPECS (Right - 50%)
    col2_x = width // 2 + 40
    col2_width = width // 2 - 80
    col2_y = header_height + 100
    
    # Price display (if provided)
    if price:
        draw.text((col2_x + col2_width//2, col2_y), f"KES {price}", 
                  fill=BRAND_MAROON, font=price_font, anchor="mm")
        col2_y += 90
    
    # BADGES SECTION
    badges = [
        ("NEW", BRAND_GOLD, BRAND_MAROON),
        ("1-YEAR WARRANTY", BRAND_MAROON, BRAND_WHITE),
        ("FREE DELIVERY", BRAND_GREEN, BRAND_WHITE),
    ]
    
    badge_height = 70
    badge_spacing = 20
    
    for badge_text, bg_color, text_color in badges:
        # Calculate badge width based on text
        bbox = badge_font.getbbox(badge_text)
        badge_width = bbox[2] - bbox[0] + 60
        
        # Draw rounded rectangle badge
        draw.rounded_rectangle(
            [col2_x, col2_y, col2_x + badge_width, col2_y + badge_height],
            radius=15,
            fill=bg_color,
            outline=BRAND_GOLD if bg_color != BRAND_GOLD else BRAND_MAROON,
            width=3
        )
        
        # Draw badge text
        draw.text(
            (col2_x + badge_width//2, col2_y + badge_height//2),
            badge_text,
            fill=text_color,
            font=badge_font,
            anchor="mm"
        )
        
        col2_y += badge_height + badge_spacing
    
    col2_y += 40
    
    # SPECS SECTION WITH ICONS
    specs_title_y = col2_y
    draw.text((col2_x + col2_width//2, specs_title_y), "KEY SPECIFICATIONS", 
              fill=BRAND_MAROON, font=header_font, anchor="mm")
    
    specs_title_y += 60
    
    # Specs with icons
    specs = [
        ("screen", "Screen", phone_specs.get("screen", "Premium")),
        ("camera", "Camera", phone_specs.get("camera", "Advanced")),
        ("storage", "Storage", phone_specs.get("storage", "Ample")),
        ("battery", "Battery", phone_specs.get("battery", "Long-lasting")),
    ]
    
    spec_spacing = 75
    
    for icon_name, label, value in specs:
        # Draw icon
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (45, 45))
            if icon:
                base.paste(icon, (col2_x, specs_title_y - 22), icon)
        
        # Draw label and value
        draw.text((col2_x + 60, specs_title_y), label, 
                  fill=BRAND_MAROON, font=body_font, anchor="lm")
        draw.text((col2_x + 60, specs_title_y + 40), value, 
                  fill="#333", font=small_font, anchor="lm")
        
        specs_title_y += spec_spacing
    
    # CTA BUTTON (Centered below both columns)
    cta_y = max(image_bottom if 'image_bottom' in locals() else 1300, specs_title_y) + 80
    
    # Draw button with gradient effect
    button_width = 400
    button_height = 90
    button_x = (width - button_width) // 2
    
    for i in range(button_height):
        factor = i / button_height
        r = int(139 * (1 - factor * 0.2))
        g = 0
        b = 0
        draw.line([(button_x, cta_y + i), (button_x + button_width, cta_y + i)], fill=(r, g, b))
    
    # Add border
    draw.rounded_rectangle(
        [button_x, cta_y, button_x + button_width, cta_y + button_height],
        radius=20,
        outline=BRAND_GOLD,
        width=4
    )
    
    # Button text
    draw.text((width//2, cta_y + button_height//2), "ORDER NOW", 
              fill=BRAND_WHITE, font=cta_font, anchor="mm")
    
    # FOOTER SECTION
    footer_y = height - 180
    
    # Location
    location_y = footer_y
    location_icon = download_icon(ICON_URLS["location"], (30, 30))
    if location_icon:
        base.paste(location_icon, (width//2 - 200, location_y), location_icon)
    
    draw.text((width//2 - 160, location_y + 15), TRIPPLEK_LOCATION, 
              fill=BRAND_MAROON, font=small_font, anchor="lm")
    
    # Website
    website_y = location_y + 50
    draw.text((width//2, website_y), TRIPPLEK_URL, 
              fill=BRAND_MAROON, font=small_font, anchor="mm")
    
    # Social Media Icons
    social_y = website_y + 50
    social_icons = ["facebook", "instagram", "twitter", "tiktok"]
    icon_size = 40
    icon_spacing = 60
    total_width = len(social_icons) * icon_spacing
    start_x = (width - total_width) // 2 + icon_spacing // 2
    
    for i, icon_name in enumerate(social_icons):
        icon_url = ICON_URLS.get(icon_name)
        if icon_url:
            icon = download_icon(icon_url, (icon_size, icon_size))
            if icon:
                x_pos = start_x + (i * icon_spacing) - icon_size // 2
                base.paste(icon, (x_pos, social_y), icon)
    
    # Social handle below icons
    draw.text((width//2, social_y + icon_size + 20), f"@{SOCIAL_HANDLE.replace(' ', '').lower()}", 
              fill="#666", font=get_font(22), anchor="mm")
    
    # Contact info at very bottom
    bottom_y = height - 40
    draw.text((width//2, bottom_y), f"📞 {TRIPPLEK_PHONE} | 💬 {TRIPPLEK_PHONE}", 
              fill=BRAND_MAROON, font=get_font(26), anchor="mm")
    
    return base

# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    # Creative Header with Gradient
    st.markdown(f"""
    <div class="header-container">
        <h1 style="margin: 0; font-size: 3.2rem; font-weight: 700;">📱 Tripple K Marketing Suite</h1>
        <p style="margin: 1rem 0 0 0; font-size: 1.4rem; opacity: 0.95;">
            Professional Phone Marketing Platform
        </p>
        <div style="margin-top: 2rem; display: flex; justify-content: center; gap: 25px; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.25); padding: 10px 25px; border-radius: 25px; font-weight: 500;">📱 100% Genuine Phones</span>
            <span style="background: rgba(255,255,255,0.25); padding: 10px 25px; border-radius: 25px; font-weight: 500;">✓ 1-Year Warranty</span>
            <span style="background: rgba(255,255,255,0.25); padding: 10px 25px; border-radius: 25px; font-weight: 500;">🚚 Free Nairobi Delivery</span>
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
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Phone Search", "📝 Content Creator", "🎨 Ad Designer"])
    
    # TAB 1: PHONE SEARCH
    with tab1:
        st.markdown('<div class="tab-container">', unsafe_allow_html=True)
        st.markdown("### 📱 Find Phone Specifications")
        
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
                                
                                # Display phone info
                                st.markdown(f"## {specs['name']}")
                                
                                # Specs in two columns
                                col_spec1, col_spec2 = st.columns(2)
                                
                                with col_spec1:
                                    st.markdown('<div class="spec-card">', unsafe_allow_html=True)
                                    st.markdown(f"**🖥️ Screen:** {specs.get('screen', 'N/A')}")
                                    st.markdown(f"**📸 Camera:** {specs.get('camera', 'N/A')}")
                                    st.markdown(f"**⚡ RAM:** {specs.get('ram', 'N/A')}")
                                    st.markdown(f"**💾 Storage:** {specs.get('storage', 'N/A')}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                                
                                with col_spec2:
                                    st.markdown('<div class="spec-card">', unsafe_allow_html=True)
                                    st.markdown(f"**🔋 Battery:** {specs.get('battery', 'N/A')}")
                                    st.markdown(f"**🚀 Chipset:** {specs.get('chipset', 'N/A')}")
                                    st.markdown(f"**🪟 OS:** {specs.get('os', 'N/A')}")
                                    st.markdown(f"**📅 Launch:** {specs.get('launch_date', 'N/A')}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Phone images after specs
                                if images:
                                    st.markdown("### 📸 Phone Gallery")
                                    st.markdown('<div class="image-grid">', unsafe_allow_html=True)
                                    
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
                                    
                                    st.success("✅ Phone details loaded successfully!")
                                    st.info("Now proceed to Content Creator or Ad Designer tabs")
                else:
                    st.error("❌ No phones found. Try a different search term.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 2: CONTENT CREATOR
    with tab2:
        st.markdown('<div class="tab-container">', unsafe_allow_html=True)
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
                        st.markdown(f'<div class="platform-tag">{platform_name}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="spec-card">', unsafe_allow_html=True)
                        st.write(posts[platform_key])
                        
                        # Copy button
                        col_copy, _ = st.columns([1, 3])
                        with col_copy:
                            if st.button(f"📋 Copy {platform_name}", key=f"copy_{platform_key}"):
                                try:
                                    pyperclip.copy(posts[platform_key])
                                    st.success("✅ Copied to clipboard!")
                                except:
                                    st.info("📝 Text ready for manual copying")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 3: AD DESIGNER
    with tab3:
        st.markdown('<div class="tab-container">', unsafe_allow_html=True)
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
                                     help="Price will be displayed on the ad",
                                     key="price_input")
                st.session_state.price = price
            
            with col_image:
                selected_image = st.selectbox("Select main image:", 
                                             [f"Image {i+1}" for i in range(min(3, len(phone_images)))],
                                             key="image_select")
            
            # Benefits section
            st.markdown("### 🎯 Key Benefits Included in Ad")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                <div class="benefit-highlight">
                <strong>🛡️ 1-Year Warranty</strong><br>
                Official Manufacturer Warranty
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown("""
                <div class="benefit-highlight">
                <strong>🚚 Free Delivery</strong><br>
                Free Nairobi Delivery Service
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown("""
                <div class="benefit-highlight">
                <strong>✅ Genuine Products</strong><br>
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
                    
                    # Show ad in two columns
                    col_ad, col_features = st.columns([2, 1])
                    
                    with col_ad:
                        st.image(ad_image, use_container_width=True, 
                                caption="WhatsApp Marketing Ad (1080x1920)")
                    
                    with col_features:
                        st.markdown("### 📋 Ad Features")
                        st.markdown("""
                        **✅ What's Included:**
                        - Tripple K Logo (300x300)
                        - Phone image on left side
                        - Badges: NEW, WARRANTY, DELIVERY
                        - Key specifications with icons
                        - Price display (if provided)
                        - Contact information
                        - Location details
                        - Social media icons
                        - Professional CTA button
                        
                        **🎯 Best Used For:**
                        - WhatsApp Status updates
                        - Social Media Stories
                        - Customer Broadcasts
                        - Print materials
                        - Digital marketing
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
                               - Upload as status for 24-hour visibility
                               - Best posting times: 11 AM - 2 PM, 7 PM - 9 PM
                            
                            2. **Social Media:**
                               - Facebook/Instagram Stories
                               - Twitter posts with shortened link
                               - LinkedIn updates for business clients
                            
                            3. **Marketing Channels:**
                               - Email newsletters
                               - SMS campaigns
                               - Print as flyers/posters
                               - Digital displays in-store
                            
                            **Pro Tips:**
                            - Always include contact number in caption
                            - Mention specific delivery areas
                            - Specify warranty terms clearly
                            - Use relevant hashtags
                            - Tag location for local reach
                            """)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Creative Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 2.5rem 0;">
        <div style="display: flex; justify-content: center; align-items: flex-start; gap: 40px; margin-bottom: 2rem; flex-wrap: wrap;">
            <div style="text-align: left; max-width: 400px;">
                <h4 style="color: {BRAND_MAROON}; margin: 0 0 1rem 0; font-weight: 600;">Tripple K Communications</h4>
                <p style="margin: 8px 0; color: #555; font-size: 0.95rem;">
                    <strong>📍</strong> {TRIPPLEK_LOCATION}
                </p>
                <p style="margin: 8px 0; color: #555; font-size: 0.95rem;">
                    <strong>📞</strong> {TRIPPLEK_PHONE}
                </p>
                <p style="margin: 8px 0; color: #555; font-size: 0.95rem;">
                    <strong>🌐</strong> {TRIPPLEK_URL}
                </p>
            </div>
            
            <div style="background: linear-gradient(135deg, {BRAND_MAROON}15 0%, #fff5f5 100%); 
                       padding: 20px; border-radius: 15px; border: 2px solid {BRAND_MAROON}30;">
                <p style="margin: 0; font-weight: 700; color: {BRAND_MAROON}; font-size: 1.1rem;">🎯 Our Promise</p>
                <p style="margin: 10px 0 0 0; color: #666; font-size: 0.95rem;">
                    100% Genuine Products • Free Nairobi Delivery • Official Warranty • Professional Service
                </p>
            </div>
        </div>
        
        <div style="margin: 1.5rem 0;">
            <p style="color: {BRAND_MAROON}; font-weight: 600; margin-bottom: 1rem;">Follow Us</p>
            <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 1rem;">
                <span style="color: #666;">@{SOCIAL_HANDLE.replace(' ', '').lower()}</span>
            </div>
        </div>
        
        <p style="color: #888; font-size: 0.9rem; margin-top: 2rem;">
            Professional Phone Marketing Suite • Version 6.0 • Designed for Tripple K Communications
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()