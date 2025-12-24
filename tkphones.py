import streamlit as st
import requests
import re
from datetime import datetime
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from io import BytesIO
from typing import Optional, Tuple, Dict, Any, List
import time
from functools import wraps
import base64
import traceback

# Optional import for background removal
try:
    import rembg
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("Warning: rembg not installed. Background removal will be disabled.")

# ==========================================
# CONFIGURATION
# ==========================================
GROQ_KEY = st.secrets.get("groq_key", "")
if GROQ_KEY:
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    MODEL = "llama-3.3-70b-versatile"
else:
    client = None

# Brand colors
BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
BRAND_ACCENT = "#FF6B35"
BRAND_WHITE = "#FFFFFF"
BRAND_BLACK = "#333333"
LIGHT_BG = "#F8F9FA"
DARK_BG = "#1a1a1a"

# Contact info
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_WHATSAPP = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
TRIPPLEK_LOCATION = "CBD Opposite MKU Towers"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# Platform info
PLATFORM_INFO = {
    "facebook": {
        "name": "Tripple K Communication",
        "icon_url": "https://ik.imagekit.io/ericmwangi/facebook.png"
    },
    "tiktok": {
        "name": "Tripple K",
        "icon_url": "https://ik.imagekit.io/ericmwangi/tiktok.png"
    }
}

# API Base URLs
API_BASE = "https://tkphsp2.vercel.app"
SEARCH_ENDPOINT = f"{API_BASE}/gsm/search"
IMAGES_ENDPOINT = f"{API_BASE}/gsm/images"
INFO_ENDPOINT = f"{API_BASE}/gsm/info"

# Badge options
BADGE_OPTIONS = {
    "new_arrival": {"text": "NEW ARRIVAL", "color": "#FF6B35", "icon": "🆕"},
    "best_seller": {"text": "BEST SELLER", "color": "#4CAF50", "icon": "🏆"},
    "limited_stock": {"text": "LIMITED STOCK", "color": "#FFC107", "icon": "⚡"},
    "official_warranty": {"text": "OFFICIAL WARRANTY", "color": "#2196F3", "icon": "✅"},
    "trending": {"text": "TRENDING NOW", "color": "#9C27B0", "icon": "🔥"},
    "free_delivery": {"text": "FREE DELIVERY", "color": "#00BCD4", "icon": "🚚"},
    "discount": {"text": "SPECIAL OFFER", "color": "#FF5722", "icon": "💰"},
    "premium": {"text": "PREMIUM QUALITY", "color": "#795548", "icon": "💎"},
}

# Rate limiting
RATE_LIMIT_CALLS = 3
RATE_LIMIT_WINDOW = 60

st.set_page_config(
    page_title="Tripple K Phone Marketing Suite",
    layout="wide",
    page_icon="📱"
)

# ==========================================
# STYLING
# ==========================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    
    * {{
        font-family: 'Poppins', sans-serif;
    }}
    
    .main {{
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }}
    
    .header-box {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #6b0000 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    
    .specs-container {{
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }}
    
    .spec-item {{
        display: flex;
        align-items: center;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        border-left: 4px solid {BRAND_MAROON};
        background: #f8f9fa;
    }}
    
    .spec-label {{
        font-weight: bold;
        color: {BRAND_MAROON};
        min-width: 100px;
        margin-right: 15px;
    }}
    
    .spec-value {{
        color: #333;
        flex-grow: 1;
    }}
    
    .selected-image {{
        border: 3px solid {BRAND_MAROON};
        border-radius: 10px;
        padding: 10px;
        margin-top: 1rem;
    }}
    
    .stButton>button {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        border: none;
        padding: 12px 28px;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 12px rgba(139, 0, 0, 0.3);
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(139, 0, 0, 0.4);
    }}
    
    .copy-button {{
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%) !important;
    }}
    
    .badge-selection {{
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 2px solid {BRAND_MAROON};
    }}
    
    .social-post {{
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 5px solid {BRAND_MAROON};
    }}
    
    .phone-card {{
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        cursor: pointer;
        transition: all 0.3s;
        border: 2px solid transparent;
    }}
    
    .phone-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-color: {BRAND_MAROON};
    }}
    
    .phone-card-selected {{
        border-color: {BRAND_MAROON} !important;
        background-color: #f8f0f0;
    }}
    
    .price-display {{
        background: linear-gradient(135deg, {BRAND_GOLD} 0%, #ffb300 100%);
        color: {BRAND_MAROON};
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.2rem;
        text-align: center;
        margin: 0.5rem 0;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# UTILITY FUNCTIONS - IMPROVED
# ==========================================

def retry_on_error(max_retries=3, delay=1):
    """Decorator for retrying functions on error"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@st.cache_data(ttl=3600)
@retry_on_error(max_retries=2)
def download_image_safe(url: str) -> Optional[Image.Image]:
    """Download image safely"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB to avoid issues
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            return img
    except Exception as e:
        print(f"Download error for {url}: {str(e)}")
    return None

@st.cache_data(ttl=86400)
def get_logo_safe() -> Optional[Image.Image]:
    """Get logo with proper transparency handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(LOGO_URL, timeout=10, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGBA for transparency
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGBA')
            
            # Remove white background gently
            data = img.getdata()
            new_data = []
            for item in data:
                r, g, b, a = item
                # Only remove very light pixels
                if r > 250 and g > 250 and b > 250 and a > 0:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            
            img = img.resize((180, 60), Image.Resampling.LANCZOS)
            return img
    except Exception as e:
        print(f"Logo error: {e}")
    return None

def get_phone_images(phone_id: str) -> List[str]:
    """Get phone images from API"""
    try:
        url = f"{IMAGES_ENDPOINT}/{phone_id}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=15, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict) and "images" in data:
                images = data["images"]
                if isinstance(images, list):
                    valid_images = [img for img in images if isinstance(img, str) and img.startswith('http')]
                    return valid_images[:8]
            elif isinstance(data, list):
                valid_images = [img for img in data if isinstance(img, str) and img.startswith('http')]
                return valid_images[:8]
    except Exception as e:
        print(f"Error getting images for {phone_id}: {e}")
    
    return []

def search_phones(query: str) -> List[Dict[str, Any]]:
    """Search for phones"""
    try:
        url = f"{SEARCH_ENDPOINT}?q={requests.utils.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=10, headers=headers)
        
        if response.status_code == 200:
            results = response.json()
            return results or []
    except Exception as e:
        print(f"Search error: {e}")
    
    return []

def get_phone_details(phone_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed phone information from API"""
    try:
        url = f"{INFO_ENDPOINT}/{phone_id}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=15, headers=headers)
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting phone details: {e}")
    
    return None

def extract_image_id_from_search_result(phone_data: Dict[str, Any]) -> str:
    """Extract the correct image ID from search result"""
    phone_id = phone_data.get("id", "")
    if phone_id and "-" in phone_id:
        parts = phone_id.split("-")
        if len(parts) >= 2:
            base = "-".join(parts[:-1])
            number_part = parts[-1]
            return f"{base}-pictures-{number_part}"
    return phone_id

def remove_background_with_rembg(image: Image.Image) -> Image.Image:
    """Remove background using rembg if available"""
    if not REMBG_AVAILABLE:
        # If rembg is not available, use simple method
        return remove_background_simple(image)

    try:
        # Convert PIL image to bytes
        img_byte_arr = BytesIO()
        if image.mode == 'RGBA':
            # Create white background for RGBA images
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            background.save(img_byte_arr, format='PNG')
        else:
            image.save(img_byte_arr, format='PNG')
        
        img_byte_arr = img_byte_arr.getvalue()

        # Remove background
        output_bytes = rembg.remove(img_byte_arr)

        # Convert back to PIL image
        output_buffer = BytesIO(output_bytes)
        result_image = Image.open(output_buffer)

        # Ensure the result is in RGBA mode to preserve transparency
        if result_image.mode != 'RGBA':
            result_image = result_image.convert('RGBA')

        return result_image
    except Exception as e:
        print(f"Error in background removal: {e}")
        # Return original image if removal fails
        return remove_background_simple(image)

def remove_background_simple(image: Image.Image) -> Image.Image:
    """Simple background removal for fallback"""
    try:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        data = image.getdata()
        new_data = []
        
        for item in data:
            r, g, b, a = item
            # Remove white and near-white pixels
            if r > 220 and g > 220 and b > 220:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        image.putdata(new_data)
        return image
    except:
        return image

def create_phone_image_for_ad(image_url: str, target_size: Tuple[int, int]) -> Optional[Image.Image]:
    """Create phone image for ad with proper sizing and background removal"""
    try:
        phone_img = download_image_safe(image_url)
        if not phone_img:
            return None

        # Create a clean copy
        phone_img = phone_img.copy()

        # Remove background
        phone_img = remove_background_with_rembg(phone_img)

        # Convert to RGBA for transparency
        if phone_img.mode != 'RGBA':
            phone_img = phone_img.convert('RGBA')

        # Calculate resize dimensions maintaining aspect ratio
        original_width, original_height = phone_img.size
        target_width, target_height = target_size

        # Calculate scaling factor (80% of available space)
        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        scale = min(width_ratio, height_ratio) * 0.8

        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        # Resize
        phone_img = phone_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create new transparent image
        result = Image.new('RGBA', target_size, (255, 255, 255, 0))

        # Calculate position (center)
        x = (target_width - new_width) // 2
        y = (target_height - new_height) // 2

        # Paste phone image
        result.paste(phone_img, (x, y), phone_img)

        return result
    except Exception as e:
        print(f"Error creating phone image: {e}")
        return None

def format_price(price_str: str) -> str:
    """Format price string with commas"""
    if not price_str:
        return "99,999"
    
    # Remove any non-digit characters except commas
    clean_price = re.sub(r'[^\d,]', '', price_str)
    
    try:
        # Remove commas for conversion
        num_str = clean_price.replace(',', '')
        if num_str:
            num = int(num_str)
            return f"{num:,}"
    except:
        pass
    
    return "99,999"

def copy_to_clipboard(text: str):
    """Copy text to clipboard using JavaScript"""
    # Create a unique key for the component
    key = f"copy_{hash(text) % 10000}"
    
    js_code = f"""
    <script>
    function copyText() {{
        const text = `{text}`;
        navigator.clipboard.writeText(text).then(() => {{
            alert('✓ Copied to clipboard!');
        }}).catch(err => {{
            console.error('Failed to copy: ', err);
        }});
    }}
    copyText();
    </script>
    """
    
    # Use markdown with HTML for the copy functionality
    st.markdown(js_code, unsafe_allow_html=True)

def get_icon_safe(url: str, name: str) -> Optional[Image.Image]:
    """Get icon safely"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

            # Convert to RGBA for transparency
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            return img
    except Exception as e:
        print(f"Icon download error for {name}: {str(e)}")
    return None

# ==========================================
# SPEC PARSING - IMPROVED
# ==========================================

def parse_phone_specs_from_detailed_info(detailed_data: dict, search_data: dict) -> Dict[str, Any]:
    """Parse phone specs from detailed API response"""
    if not detailed_data:
        return parse_phone_specs_from_search(search_data)
    
    name = detailed_data.get("name", search_data.get("name", "Unknown Phone"))
    phone_id = search_data.get("id", "")
    image_url = search_data.get("image", "")
    
    # Screen size
    display = detailed_data.get("display", {})
    screen_size = display.get("size", "N/A")
    screen = "N/A"
    if screen_size and isinstance(screen_size, str):
        inches_match = re.search(r'(\d+\.?\d*)\s*inches', screen_size, re.IGNORECASE)
        if inches_match:
            screen = f"{inches_match.group(1)} inches"
        else:
            num_match = re.search(r'(\d+\.?\d*)', screen_size)
            if num_match:
                screen = f"{num_match.group(1)} inches"
    
    # Camera
    main_camera = detailed_data.get("mainCamera", {})
    camera_specs = main_camera.get("modules", "")
    camera = "N/A"
    if camera_specs and isinstance(camera_specs, str):
        mp_matches = re.findall(r'(\d+\.?\d*)\s*MP', camera_specs, re.IGNORECASE)
        if mp_matches:
            camera = " + ".join(mp_matches[:2])
    
    # RAM and storage
    memory_info = detailed_data.get("memory", {})
    ram = "N/A"
    storage = "N/A"
    
    if isinstance(memory_info, dict):
        internal = memory_info.get("internal", "")
        if internal and isinstance(internal, str):
            ram_match = re.search(r'(\d+)\s*GB\s*RAM', internal, re.IGNORECASE)
            if ram_match:
                ram = f"{ram_match.group(1)}GB"
            
            storage_match = re.search(r'(\d+)\s*GB\s*(?:ROM|storage|internal)', internal, re.IGNORECASE)
            if storage_match:
                storage = f"{storage_match.group(1)}GB"
    
    # Chipset
    platform = detailed_data.get("platform", {})
    chipset = platform.get("chipset", "N/A")
    
    # Battery
    battery_info = detailed_data.get("battery", {})
    battery = battery_info.get("type", battery_info.get("battType", "N/A"))
    
    return {
        "name": name,
        "id": phone_id,
        "image_url": image_url,
        "specs": {
            "screen": screen,
            "camera": camera,
            "ram": ram,
            "storage": storage,
            "chipset": chipset,
            "battery": battery,
        },
        "detailed_data": detailed_data,
    }

def parse_phone_specs_from_search(phone_data: dict) -> Dict[str, Any]:
    """Parse basic phone specs from search result (fallback)"""
    if not phone_data:
        return {"name": "Unknown Phone", "id": "unknown", "specs": {}}
    
    return {
        "name": phone_data.get("name", "Unknown Phone"),
        "id": phone_data.get("id", ""),
        "image_url": phone_data.get("image", ""),
        "specs": {
            "screen": "Check details",
            "camera": "Check details",
            "ram": "Check details",
            "storage": "Check details",
            "chipset": "Check details",
            "battery": "Check details",
        },
    }

# ==========================================
# AD LAYOUTS - INDEPENDENT POSITIONS
# ==========================================

AD_LAYOUTS = {
    "facebook": {
        "size": (1200, 1200),  # Square format
        "background": BRAND_MAROON,
        "regions": {
            "logo": {"x": 50, "y": 40, "width": 180, "height": 60},
            "badges": {"x": 50, "y": 120, "width": 1100, "height": 60},
            "phone": {"x": 150, "y": 200, "width": 500, "height": 500},
            "content": {"x": 700, "y": 200, "width": 400, "height": 500},
            "price": {"x": 700, "y": 720, "width": 400, "height": 80},
            "cta": {"x": 700, "y": 820, "width": 180, "height": 60},
            "contact": {"x": 900, "y": 820, "width": 200, "height": 60},
            "footer": {"x": 50, "y": 900, "width": 1100, "height": 250},
        }
    },
    "whatsapp": {
        "size": (1080, 1920),  # Vertical format
        "background": BRAND_WHITE,
        "regions": {
            "logo": {"x": 50, "y": 40, "width": 180, "height": 60},
            "badges": {"x": 50, "y": 120, "width": 980, "height": 60},
            "phone": {"x": 140, "y": 200, "width": 800, "height": 700},
            "content": {"x": 100, "y": 920, "width": 880, "height": 400},
            "price": {"x": 100, "y": 1340, "width": 880, "height": 80},
            "cta": {"x": 100, "y": 1440, "width": 400, "height": 70},
            "contact": {"x": 520, "y": 1440, "width": 460, "height": 70},
            "footer": {"x": 100, "y": 1530, "width": 880, "height": 350},
        }
    },
    "instagram": {
        "size": (1080, 1350),
        "background": BRAND_MAROON,
        "regions": {
            "logo": {"x": 450, "y": 30, "width": 180, "height": 60},
            "badges": {"x": 100, "y": 110, "width": 880, "height": 60},
            "phone": {"x": 140, "y": 190, "width": 800, "height": 500},
            "content": {"x": 100, "y": 710, "width": 880, "height": 300},
            "price": {"x": 100, "y": 1030, "width": 880, "height": 80},
            "cta": {"x": 390, "y": 1130, "width": 150, "height": 60},
            "contact": {"x": 550, "y": 1130, "width": 200, "height": 60},
            "footer": {"x": 100, "y": 1210, "width": 880, "height": 100},
        }
    }
}

# ==========================================
# AD GENERATOR - WITH BADGES AND IMPROVED LAYOUT
# ==========================================

class AdvancedAdGenerator:
    """Advanced ad generator with badges and improved layout"""
    
    def __init__(self, platform: str = "facebook"):
        self.platform = platform
        self.layout = AD_LAYOUTS[platform]
        self.width, self.height = self.layout["size"]

        # Load fonts
        try:
            # Try to load Poppins font
            self.title_font = ImageFont.truetype("poppins.ttf", 42 if platform == "instagram" else 36)
            self.subtitle_font = ImageFont.truetype("poppins.ttf", 28 if platform == "instagram" else 24)
            self.body_font = ImageFont.truetype("poppins.ttf", 22 if platform == "instagram" else 18)
            self.small_font = ImageFont.truetype("poppins.ttf", 16 if platform == "instagram" else 14)
            self.price_font = ImageFont.truetype("poppins.ttf", 38 if platform == "instagram" else 32)
        except:
            # Fallback to default fonts
            default = ImageFont.load_default()
            self.title_font = default
            self.subtitle_font = default
            self.body_font = default
            self.small_font = default
            self.price_font = default
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_base_image(self) -> Image.Image:
        """Create base image with gradient background"""
        base_color = self.hex_to_rgb(self.layout["background"])
        img = Image.new('RGB', (self.width, self.height), base_color)
        
        return img
    
    def draw_logo(self, img: Image.Image) -> Image.Image:
        """Draw logo"""
        region = self.layout["regions"]["logo"]
        logo = get_logo_safe()

        if logo:
            x = region["x"] + (region["width"] - logo.width) // 2
            y = region["y"] + (region["height"] - logo.height) // 2

            # Add circular background
            draw = ImageDraw.Draw(img, 'RGBA')
            circle_x = x + logo.width // 2
            circle_y = y + logo.height // 2
            radius = max(logo.width, logo.height) // 2 + 8
            draw.ellipse(
                [circle_x - radius, circle_y - radius, circle_x + radius, circle_y + radius],
                fill=(255, 215, 0, 80)
            )

            img.paste(logo, (x, y), logo)

        return img
    
    def draw_badges(self, img: Image.Image, draw: ImageDraw.ImageDraw, badges: List[str]):
        """Draw selected badges"""
        if not badges:
            return

        region = self.layout["regions"]["badges"]
        x, y = region["x"], region["y"]
        max_width = region["width"]

        current_x = x
        badge_height = 40
        badge_spacing = 10

        for badge_key in badges[:4]:  # Max 4 badges
            if badge_key in BADGE_OPTIONS:
                badge = BADGE_OPTIONS[badge_key]
                badge_text = f"{badge['icon']} {badge['text']}"

                # Calculate text size
                bbox = draw.textbbox((0, 0), badge_text, font=self.small_font)
                text_width = bbox[2] - bbox[0] + 20
                text_height = badge_height

                # Check if badge fits in current row
                if current_x + text_width > x + max_width:
                    break

                # Draw badge background
                badge_color = self.hex_to_rgb(badge['color'])
                draw.rounded_rectangle(
                    [current_x, y, current_x + text_width, y + badge_height],
                    radius=badge_height // 2,
                    fill=badge_color
                )

                # Draw badge text
                text_y = y + (badge_height - (bbox[3] - bbox[1])) // 2
                draw.text(
                    (current_x + 10, text_y),
                    badge_text,
                    fill=BRAND_WHITE,
                    font=self.small_font
                )

                current_x += text_width + badge_spacing
    
    def draw_phone_image(self, img: Image.Image, phone_img_url: str) -> Image.Image:
        """Draw phone image with proper alignment"""
        if not phone_img_url:
            return img
        
        region = self.layout["regions"]["phone"]
        
        # Create phone image
        phone_img = create_phone_image_for_ad(phone_img_url, (region["width"], region["height"]))
        
        if phone_img:
            # Center in region
            x = region["x"] + (region["width"] - phone_img.width) // 2
            y = region["y"] + (region["height"] - phone_img.height) // 2
            
            # Add shadow effect
            shadow = Image.new('RGBA', (phone_img.width + 20, phone_img.height + 20), (0, 0, 0, 30))
            img.paste(shadow, (x - 10, y - 10), shadow)
            
            # Paste phone image
            img.paste(phone_img, (x, y), phone_img)
        
        return img
    
    def draw_content(self, img: Image.Image, draw: ImageDraw.ImageDraw, 
                    phone_data: dict, hook: str = ""):
        """Draw content section"""
        region = self.layout["regions"]["content"]
        x, y = region["x"], region["y"]
        
        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_BLACK
        accent_color = BRAND_GOLD
        
        # Hook text
        if hook:
            draw.text((x, y), hook, fill=accent_color, font=self.title_font)
            y += 60
        
        # Phone name
        phone_name = phone_data["name"]
        if len(phone_name) > 30:
            phone_name = phone_name[:27] + "..."
        draw.text((x, y), phone_name, fill=text_color, font=self.subtitle_font)
        y += 70
        
        # Draw 5 specific specs
        specs = [
            ("🖥️", "Screen", phone_data["specs"].get("screen", "N/A")),
            ("📸", "Camera", phone_data["specs"].get("camera", "N/A")),
            ("⚡", "RAM", phone_data["specs"].get("ram", "N/A")),
            ("💾", "Storage", phone_data["specs"].get("storage", "N/A")),
            ("🚀", "Chipset", phone_data["specs"].get("chipset", "N/A")),
        ]
        
        for icon, label, value in specs:
            if value != "N/A" and value != "Check details":
                # Draw icon
                draw.text((x, y), icon, fill=accent_color, font=self.body_font)
                
                # Draw spec
                spec_text = f"{label}: {value}"
                draw.text((x + 35, y), spec_text, fill=text_color, font=self.body_font)
                y += 45
    
    def draw_price(self, img: Image.Image, draw: ImageDraw.ImageDraw, price: str = ""):
        """Draw price badge"""
        region = self.layout["regions"]["price"]
        x, y = region["x"], region["y"]
        
        # Format price
        formatted_price = format_price(price)
        
        # Create price badge
        badge_width = region["width"]
        badge_height = region["height"]
        
        # Draw background
        price_bg_color = self.hex_to_rgb(BRAND_GOLD) if self.platform in ["facebook", "instagram"] else self.hex_to_rgb(BRAND_MAROON)
        draw.rounded_rectangle(
            [x, y, x + badge_width, y + badge_height],
            radius=20,
            fill=price_bg_color
        )
        
        # Draw price text - Just the formatted number
        price_text = formatted_price
        
        bbox = draw.textbbox((0, 0), price_text, font=self.price_font)
        text_width = bbox[2] - bbox[0]
        text_x = x + (badge_width - text_width) // 2
        text_y = y + (badge_height - (bbox[3] - bbox[1])) // 2
        
        text_color = BRAND_MAROON if self.platform in ["facebook", "instagram"] else BRAND_WHITE
        draw.text((text_x, text_y), price_text, fill=text_color, font=self.price_font)
    
    def draw_cta_button(self, img: Image.Image, draw: ImageDraw.ImageDraw, cta: str = ""):
        """Draw CTA button"""
        region = self.layout["regions"]["cta"]
        x, y = region["x"], region["y"]
        width, height = region["width"], region["height"]
        
        button_text = cta if cta else ("SHOP NOW" if self.platform == "facebook" else "ORDER NOW")
        
        # Draw button with gradient
        for i in range(height):
            r = 255 - int(i * 0.2)
            g = 215 - int(i * 0.2)
            b = 0
            draw.rectangle(
                [x, y + i, x + width, y + i + 1],
                fill=(r, g, b)
            )
        
        # Add border
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=15,
            outline=self.hex_to_rgb(BRAND_MAROON),
            width=3
        )
        
        # Draw text
        bbox = draw.textbbox((0, 0), button_text, font=self.subtitle_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2
        
        draw.text(
            (text_x, text_y),
            button_text,
            fill=self.hex_to_rgb(BRAND_MAROON),
            font=self.subtitle_font
        )
    
    def draw_contact_info(self, img: Image.Image, draw: ImageDraw.ImageDraw):
        """Draw contact information with separate icons"""
        region = self.layout["regions"]["contact"]
        x, y = region["x"], region["y"]
        
        # Background
        contact_bg = self.hex_to_rgb(LIGHT_BG) if self.platform == "whatsapp" else (255, 255, 255, 180)
        draw.rounded_rectangle(
            [x, y, x + region["width"], y + region["height"]],
            radius=10,
            fill=contact_bg
        )
        
        # Text color
        text_color = BRAND_MAROON
        
        # Draw simple text (fallback if icons fail)
        if self.platform == "whatsapp":
            contact_text = f"📞 {TRIPPLEK_PHONE}\n💬 {TRIPPLEK_WHATSAPP}"
        else:
            contact_text = f"Contact: {TRIPPLEK_PHONE}"
        
        draw.text((x + 10, y + 10), contact_text, fill=text_color, font=self.small_font)
    
    def draw_footer(self, img: Image.Image, draw: ImageDraw.ImageDraw, hashtags: str = ""):
        """Draw footer with website and hashtags"""
        region = self.layout["regions"]["footer"]
        x, y = region["x"], region["y"]
        
        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_BLACK
        
        # Website
        website_text = f"🌐 {TRIPPLEK_URL}"
        draw.text((x, y), website_text, fill=text_color, font=self.small_font)
        
        # Location
        location_y = y + 25
        location_text = f"📍 {TRIPPLEK_LOCATION}"
        draw.text((x, location_y), location_text, fill=text_color, font=self.small_font)
        
        # Hashtags
        if hashtags:
            hashtag_y = location_y + 25
            hashtag_lines = hashtags.split('\n')
            for line in hashtag_lines:
                if line.strip():
                    draw.text((x, hashtag_y), line.strip(), fill=BRAND_GOLD, font=self.small_font)
                    hashtag_y += 25
    
    def generate(self, phone_data: dict, phone_img_url: str = None, 
                hook: str = "", cta: str = "", price: str = "",
                badges: List[str] = None, hashtags: str = "") -> Image.Image:
        """Generate complete ad"""
        # Create base image
        img = self.create_base_image()
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Draw all components
        img = self.draw_logo(img)
        self.draw_badges(img, draw, badges or [])
        
        if phone_img_url:
            img = self.draw_phone_image(img, phone_img_url)
        
        self.draw_content(img, draw, phone_data, hook)
        self.draw_price(img, draw, price)
        self.draw_cta_button(img, draw, cta)
        self.draw_contact_info(img, draw)
        self.draw_footer(img, draw, hashtags)
        
        return img

# ==========================================
# SOCIAL POST GENERATOR
# ==========================================

def generate_social_posts(phone_data: dict, content: dict, price: str, badges: List[str]) -> Dict[str, str]:
    """Generate ready-to-paste social media posts"""
    
    # Format specs - using 5 specific specs
    specs = phone_data["specs"]
    specs_text = ""
    
    # Show 5 specific specs
    spec_items = [
        ("Screen", specs.get("screen", "N/A")),
        ("Camera", specs.get("camera", "N/A")),
        ("RAM", specs.get("ram", "N/A")),
        ("Storage", specs.get("storage", "N/A")),
        ("Chipset", specs.get("chipset", "N/A")),
    ]
    
    for label, value in spec_items:
        if value != "N/A" and value != "Check details":
            specs_text += f"• {label}: {value}\n"
    
    # Format badges text
    badges_text = ""
    if badges:
        for badge_key in badges:
            if badge_key in BADGE_OPTIONS:
                badges_text += f"{BADGE_OPTIONS[badge_key]['icon']} "
        badges_text = badges_text.strip()
    
    # Format price
    formatted_price = format_price(price)
    
    # Get CTA
    cta = content.get('cta', 'SHOP NOW')
    
    # WhatsApp Post
    whatsapp_post = f"""📱 *{phone_data['name']}*

{content.get('hook', 'Available Now at Tripple K!')}

{specs_text}
💰 *Price: KES {formatted_price}*

{content.get('description', 'Get this amazing phone at Tripple K Communications!')}

{'' if not badges_text else badges_text + '\n\n'}

📞 Call: {TRIPPLEK_PHONE}
💬 WhatsApp: {TRIPPLEK_WHATSAPP}
📍 Location: {TRIPPLEK_LOCATION}
🌐 {TRIPPLEK_URL}

{content.get('hashtags', '#TrippleK #Smartphones')}"""
    
    # Facebook Post
    facebook_post = f"""{phone_data['name']}

{content.get('hook', 'Now Available at Tripple K Communications!')}

{specs_text}
Price: KES {formatted_price}

{content.get('description', 'Visit us today and get the best deal!')}

{'' if not badges_text else badges_text}

📞 Contact: {TRIPPLEK_PHONE}
📍 Location: {TRIPPLEK_LOCATION}
🌐 {TRIPPLEK_URL}

{content.get('hashtags', '#TrippleK #Smartphones #PhoneDeals')}"""
    
    # TikTok/Instagram Post
    tiktok_post = f"""{phone_data['name']} 🔥

{content.get('hook', 'Check out this amazing phone!')}

{specs_text}
💸 KES {formatted_price}

{content.get('description', 'Available at Tripple K Communications')}

{'' if not badges_text else badges_text}

📞 {TRIPPLEK_PHONE}
📍 {TRIPPLEK_LOCATION}

{content.get('hashtags', '#TrippleK #Phone #Tech')}"""
    
    return {
        "whatsapp": whatsapp_post,
        "facebook": facebook_post,
        "tiktok": tiktok_post
    }

# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    # Header
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    st.markdown('<h1 style="margin:0;">📱 Tripple K Phone Marketing Suite</h1>', unsafe_allow_html=True)
    st.markdown('<p style="margin:0.5rem 0 0 0; opacity:0.9;">Professional AI-Powered Marketing Platform</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Initialize session state
    if "current_phone" not in st.session_state:
        st.session_state.current_phone = None
    if "phone_images" not in st.session_state:
        st.session_state.phone_images = []
    if "selected_image_index" not in st.session_state:
        st.session_state.selected_image_index = 0
    if "ad_image_index" not in st.session_state:
        st.session_state.ad_image_index = 0
    if "marketing_content" not in st.session_state:
        st.session_state.marketing_content = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "selected_phone_index" not in st.session_state:
        st.session_state.selected_phone_index = -1
    if "phone_price" not in st.session_state:
        st.session_state.phone_price = "99,999"
    if "selected_badges" not in st.session_state:
        st.session_state.selected_badges = ["new_arrival", "official_warranty"]
    if "ad_badges" not in st.session_state:
        st.session_state.ad_badges = st.session_state.selected_badges.copy()
    if "social_posts" not in st.session_state:
        st.session_state.social_posts = None

    # Tabs
    tabs = st.tabs(["🔍 Find Phone", "📝 Create Content & Posts", "🎨 Generate Ads"])

    # TAB 1: FIND PHONE
    with tabs[0]:
        st.subheader("Search Phone Database")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Enter phone name:", 
                                placeholder="e.g., Poco X3 Pro, iPhone 14, Samsung S23",
                                key="search_input")
        with col2:
            search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_btn and query:
            with st.spinner("Searching phones..."):
                try:
                    results = search_phones(query)
                    
                    if results:
                        st.success(f"✅ Found {len(results)} phones")
                        st.session_state.search_results = results
                        st.session_state.selected_phone_index = -1
                        st.rerun()
                    else:
                        st.error("❌ No phones found. Try a different search term.")
                        st.session_state.search_results = []
                        
                except Exception as e:
                    st.error(f"❌ Search error: {str(e)}")
        
        # Display search results
        if st.session_state.search_results:
            st.markdown("### 📱 Select a Phone")
            
            results = st.session_state.search_results
            num_cols = min(2, len(results))
            cols = st.columns(num_cols)
            
            for idx, phone in enumerate(results):
                with cols[idx % num_cols]:
                    phone_name = phone.get("name", "Unknown Phone")
                    phone_image = phone.get("image", "")
                    phone_id = phone.get("id", "")
                    
                    # Create phone card
                    is_selected = idx == st.session_state.selected_phone_index
                    card_class = "phone-card-selected" if is_selected else ""
                    
                    st.markdown(f"""
                    <div class="phone-card {card_class}">
                        <strong>{phone_name}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display phone image thumbnail
                    if phone_image:
                        try:
                            thumb_img = download_image_safe(phone_image)
                            if thumb_img:
                                thumb_img.thumbnail((200, 200))
                                st.image(thumb_img, use_container_width=True)
                        except:
                            pass
                    
                    # Selection button
                    if st.button(f"Select {phone_name}", key=f"select_{idx}", use_container_width=True):
                        with st.spinner("Loading phone details..."):
                            st.session_state.selected_phone_index = idx
                            
                            # Get detailed phone info
                            detailed_info = get_phone_details(phone_id)
                            
                            if detailed_info:
                                # Parse specs from detailed info
                                phone_data = parse_phone_specs_from_detailed_info(detailed_info, phone)
                                st.session_state.current_phone = phone_data
                                
                                # Get images
                                image_id = extract_image_id_from_search_result(phone)
                                images = get_phone_images(image_id)
                                
                                # Include the main image from search result
                                if phone_image and phone_image not in images:
                                    images.insert(0, phone_image)
                                
                                st.session_state.phone_images = images
                                st.session_state.selected_image_index = 0
                                st.session_state.ad_image_index = 0
                                st.session_state.marketing_content = None
                                st.session_state.social_posts = None
                                
                                st.success(f"✅ {phone_name} loaded successfully!")
                                st.rerun()
                            else:
                                st.error(f"❌ Could not load details for {phone_name}")
        
        # Display selected phone details
        if st.session_state.current_phone and st.session_state.selected_phone_index >= 0:
            phone_data = st.session_state.current_phone
            images = st.session_state.phone_images
            
            st.markdown("---")
            st.markdown(f"## 📱 {phone_data['name']}")
            
            col_img, col_specs = st.columns([1, 1])
            
            with col_img:
                st.markdown("### 📸 Phone Images")
                
                if images:
                    # Show image selection
                    st.markdown("**Select an image to view:**")
                    
                    # Display images in a grid
                    for i in range(0, min(8, len(images)), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            idx = i + j
                            if idx < len(images):
                                with cols[j]:
                                    try:
                                        thumb = download_image_safe(images[idx])
                                        if thumb:
                                            thumb.thumbnail((100, 100))
                                            st.image(thumb, use_container_width=True)
                                            
                                            # Show selection indicator
                                            if idx == st.session_state.selected_image_index:
                                                st.success("✓ Selected")
                                            else:
                                                if st.button(f"Select", key=f"img_select_{idx}", use_container_width=True):
                                                    st.session_state.selected_image_index = idx
                                                    st.rerun()
                                    except:
                                        st.button(f"Image {idx+1}", key=f"img_btn_{idx}", disabled=True, use_container_width=True)
                    
                    # Show selected image preview
                    selected_idx = st.session_state.selected_image_index
                    if selected_idx < len(images):
                        try:
                            phone_img = download_image_safe(images[selected_idx])
                            if phone_img:
                                st.markdown(f"**Preview (Image {selected_idx+1}):**")
                                st.image(phone_img, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error loading image: {e}")
                else:
                    st.info("📷 No images available for this phone.")
                    
                    if phone_data.get("image_url"):
                        try:
                            phone_img = download_image_safe(phone_data["image_url"])
                            if phone_img:
                                st.image(phone_img, use_container_width=True, caption="Main Phone Image")
                        except:
                            pass
            
            with col_specs:
                st.markdown("### 📋 Key Specifications")
                st.markdown('<div class="specs-container">', unsafe_allow_html=True)
                
                # Display 5 specific specs
                display_specs = [
                    ("🖥️ Screen", phone_data["specs"].get('screen', 'N/A')),
                    ("📸 Camera", phone_data["specs"].get('camera', 'N/A')),
                    ("⚡ RAM", phone_data["specs"].get('ram', 'N/A')),
                    ("💾 Storage", phone_data["specs"].get('storage', 'N/A')),
                    ("🚀 Chipset", phone_data["specs"].get('chipset', 'N/A')),
                ]
                
                specs_displayed = 0
                for label, value in display_specs:
                    if value != "N/A" and value != "Check details":
                        st.markdown(f'''
                        <div class="spec-item">
                            <span class="spec-label">{label}:</span> 
                            <span class="spec-value">{value}</span>
                        </div>
                        ''', unsafe_allow_html=True)
                        specs_displayed += 1
                        
                        if specs_displayed >= 5:  # Stop after showing 5 specs
                            break
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Price input for this phone
                st.markdown("### 💰 Set Price for Ads")
                price = st.text_input("Enter price (e.g., 45,999):", 
                                    value=st.session_state.phone_price,
                                    placeholder="e.g., 45,999 or 45999",
                                    key="tab1_price")
                
                if st.button("💰 Update Price", key="update_price_btn", use_container_width=True):
                    if price:
                        st.session_state.phone_price = price
                        formatted_price = format_price(price)
                        st.success(f"✅ Price updated to {formatted_price}")
                        st.rerun()
                    else:
                        st.warning("Please enter a valid price")
                
                # Show current price
                if st.session_state.phone_price:
                    formatted_price = format_price(st.session_state.phone_price)
                    st.markdown(f'<div class="price-display">KES {formatted_price}</div>', unsafe_allow_html=True)

    # TAB 2: CREATE CONTENT & POSTS
    with tabs[1]:
        st.subheader("Create Marketing Content & Social Posts")
        
        if not st.session_state.current_phone:
            st.info("👈 First search and select a phone from the Find Phone tab")
        else:
            phone_data = st.session_state.current_phone
            
            st.markdown(f"**Selected Phone:** {phone_data['name']}")
            
            # Price section
            st.markdown("### 💰 Pricing")
            price_col1, price_col2 = st.columns([2, 1])
            with price_col1:
                price = st.text_input("Phone Price (e.g., 45,999):", 
                                    value=st.session_state.phone_price,
                                    placeholder="Enter price e.g., 45,999 or 45999",
                                    key="content_price")
            with price_col2:
                if st.button("💾 Update Price", key="update_content_price", use_container_width=True):
                    if price:
                        st.session_state.phone_price = price
                        formatted_price = format_price(price)
                        st.success(f"✅ Price updated to {formatted_price}")
                        st.rerun()
            
            # Show current price
            if st.session_state.phone_price:
                formatted_price = format_price(st.session_state.phone_price)
                st.markdown(f'<div class="price-display">KES {formatted_price}</div>', unsafe_allow_html=True)
            
            # Badge selection
            st.markdown("### 🏷️ Select Badges")
            st.markdown('<div class="badge-selection">', unsafe_allow_html=True)
            
            cols = st.columns(4)
            badge_keys = list(BADGE_OPTIONS.keys())
            
            for idx, badge_key in enumerate(badge_keys):
                badge = BADGE_OPTIONS[badge_key]
                with cols[idx % 4]:
                    is_selected = badge_key in st.session_state.selected_badges
                    if st.checkbox(f"{badge['icon']} {badge['text']}", 
                                 value=is_selected,
                                 key=f"badge_{badge_key}"):
                        if badge_key not in st.session_state.selected_badges:
                            st.session_state.selected_badges.append(badge_key)
                    elif badge_key in st.session_state.selected_badges:
                        st.session_state.selected_badges.remove(badge_key)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Generate content button
            if client and st.button("🚀 Generate AI Content", type="primary", use_container_width=True):
                with st.spinner("Creating marketing content..."):
                    try:
                        # Simple AI content generation
                        prompt = f"""Create marketing content for {phone_data['name']}:

Specs:
- Screen: {phone_data['specs'].get('screen', 'N/A')}
- Camera: {phone_data['specs'].get('camera', 'N/A')}
- RAM: {phone_data['specs'].get('ram', 'N/A')}
- Storage: {phone_data['specs'].get('storage', 'N/A')}
- Chipset: {phone_data['specs'].get('chipset', 'N/A')}

Business: Tripple K Communications
Phone: {TRIPPLEK_PHONE}
Location: {TRIPPLEK_LOCATION}

Generate:
Hook: [Catchy headline, 5-7 words]
CTA: [Call to action, 2-3 words]
Description: [Short description, 1-2 sentences]
Hashtags: [5 relevant hashtags]"""

                        response = client.chat.completions.create(
                            model=MODEL,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.7,
                            max_tokens=300
                        )

                        text = response.choices[0].message.content.strip()
                        
                        # Parse content
                        content = {"hook": "", "cta": "", "description": "", "hashtags": ""}
                        lines = text.split('\n')
                        
                        for line in lines:
                            line = line.strip()
                            for key in content.keys():
                                if line.lower().startswith(f"{key}:"):
                                    content[key] = line.split(':', 1)[1].strip()
                                    break
                        
                        st.session_state.marketing_content = content
                        st.balloons()
                        st.success("✅ Content generated successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error generating content: {str(e)}")
                        # Fallback content
                        st.session_state.marketing_content = {
                            "hook": f"{phone_data['name']} - Now Available!",
                            "cta": "SHOP NOW",
                            "description": f"Get the amazing {phone_data['name']} at Tripple K Communications!",
                            "hashtags": "#TrippleK #Smartphones #Deals"
                        }
                        st.success("✅ Default content loaded!")
                        st.rerun()
            elif not client:
                st.info("⚠️ AI content generation is disabled. No API key provided.")
            
            # Edit content
            if st.session_state.marketing_content:
                content = st.session_state.marketing_content
                
                st.markdown("### 📝 Edit Content")
                
                hook = st.text_input("Hook (Headline):", 
                                   value=content.get('hook', f"{phone_data['name']} - Now Available!"),
                                   key="content_hook")
                cta = st.text_input("Call to Action:", 
                                  value=content.get('cta', 'SHOP NOW'),
                                  key="content_cta")
                description = st.text_area("Description:", 
                                         value=content.get('description', f"Get the amazing {phone_data['name']} at Tripple K Communications!"),
                                         height=100,
                                         key="content_desc")
                hashtags = st.text_input("Hashtags:", 
                                       value=content.get('hashtags', '#TrippleK #Smartphones #Deals'),
                                       key="content_tags")
                
                # Update content
                st.session_state.marketing_content = {
                    "hook": hook,
                    "cta": cta,
                    "description": description,
                    "hashtags": hashtags
                }
                
                # Generate social posts button
                if st.button("📱 Generate Social Posts", type="secondary", use_container_width=True):
                    with st.spinner("Creating social media posts..."):
                        social_posts = generate_social_posts(
                            phone_data=phone_data,
                            content=st.session_state.marketing_content,
                            price=st.session_state.phone_price,
                            badges=st.session_state.selected_badges
                        )
                        st.session_state.social_posts = social_posts
                        st.success("✅ Social posts generated!")
                        st.rerun()
                
                # Display social posts if generated
                if st.session_state.social_posts:
                    st.markdown("### 📱 Generated Social Posts")
                    
                    # WhatsApp Post
                    st.markdown('<div class="social-post">', unsafe_allow_html=True)
                    st.markdown('### 💬 WhatsApp Post')
                    st.code(st.session_state.social_posts["whatsapp"], language=None)
                    
                    if st.button("📋 Copy WhatsApp Post", key="copy_whatsapp", use_container_width=True):
                        copy_to_clipboard(st.session_state.social_posts["whatsapp"])
                        st.success("Copied to clipboard!")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Facebook Post
                    st.markdown('<div class="social-post">', unsafe_allow_html=True)
                    st.markdown('### 👤 Facebook Post')
                    st.code(st.session_state.social_posts["facebook"], language=None)
                    
                    if st.button("📋 Copy Facebook Post", key="copy_facebook", use_container_width=True):
                        copy_to_clipboard(st.session_state.social_posts["facebook"])
                        st.success("Copied to clipboard!")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # TikTok/Instagram Post
                    st.markdown('<div class="social-post">', unsafe_allow_html=True)
                    st.markdown('### 🎵 TikTok/Instagram Post')
                    st.code(st.session_state.social_posts["tiktok"], language=None)
                    
                    if st.button("📋 Copy TikTok Post", key="copy_tiktok", use_container_width=True):
                        copy_to_clipboard(st.session_state.social_posts["tiktok"])
                        st.success("Copied to clipboard!")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("Click 'Generate Social Posts' to create ready-to-paste posts.")
            
            else:
                st.info("Click 'Generate AI Content' to create marketing content or manually enter content below.")
                
                # Manual content input
                hook = st.text_input("Hook (Headline):", 
                                   value=f"{phone_data['name']} - Now Available!",
                                   key="manual_hook")
                cta = st.text_input("Call to Action:", 
                                  value="SHOP NOW",
                                  key="manual_cta")
                description = st.text_area("Description:", 
                                         value=f"Get the amazing {phone_data['name']} at Tripple K Communications!",
                                         height=100,
                                         key="manual_desc")
                hashtags = st.text_input("Hashtags:", 
                                       value="#TrippleK #Smartphones #Deals",
                                       key="manual_tags")
                
                if st.button("💾 Save Content", use_container_width=True):
                    st.session_state.marketing_content = {
                        "hook": hook,
                        "cta": cta,
                        "description": description,
                        "hashtags": hashtags
                    }
                    st.success("✅ Content saved!")
                    st.rerun()

    # TAB 3: GENERATE ADS
    with tabs[2]:
        st.subheader("Create Visual Ads")
        
        if not st.session_state.current_phone:
            st.info("👈 First search and select a phone from the Find Phone tab")
        else:
            phone_data = st.session_state.current_phone
            images = st.session_state.phone_images
            
            # Image selection for ad
            st.markdown("### 🖼️ Select Image for Ad")
            if images:
                # Create dropdown for image selection
                image_options = [f"Image {i+1}" for i in range(len(images))]
                selected_image_label = st.selectbox(
                    "Choose an image:",
                    options=image_options,
                    index=st.session_state.ad_image_index,
                    key="ad_image_selector"
                )
                
                # Get the selected index
                selected_ad_idx = image_options.index(selected_image_label)
                if selected_ad_idx != st.session_state.ad_image_index:
                    st.session_state.ad_image_index = selected_ad_idx
                    st.rerun()
                
                selected_image_url = images[selected_ad_idx] if selected_ad_idx < len(images) else None
                
                if selected_image_url:
                    st.info(f"📸 Using {selected_image_label} for ads")
                    
                    # Show preview of selected image
                    try:
                        preview_img = download_image_safe(selected_image_url)
                        if preview_img:
                            preview_img.thumbnail((200, 200))
                            st.image(preview_img, caption=f"{selected_image_label} Preview", use_container_width=False)
                    except:
                        pass
            else:
                st.warning("⚠️ No images available for this phone.")
                selected_image_url = phone_data.get("image_url")
            
            # Platform selection
            st.markdown("### 🎯 Select Platform")
            platform = st.radio("Choose platform:", 
                              ["Facebook", "WhatsApp", "Instagram"],
                              horizontal=True,
                              label_visibility="collapsed")
            
            # Badge selection for ads
            st.markdown("### 🏷️ Select Badges for Ad")
            st.markdown('<div class="badge-selection">', unsafe_allow_html=True)
            
            cols = st.columns(4)
            badge_keys = list(BADGE_OPTIONS.keys())
            
            for idx, badge_key in enumerate(badge_keys):
                badge = BADGE_OPTIONS[badge_key]
                with cols[idx % 4]:
                    is_selected = badge_key in st.session_state.ad_badges
                    if st.checkbox(f"{badge['icon']} {badge['text']}",
                                 value=is_selected,
                                 key=f"ad_badge_{badge_key}"):
                        if badge_key not in st.session_state.ad_badges:
                            st.session_state.ad_badges.append(badge_key)
                    elif badge_key in st.session_state.ad_badges:
                        st.session_state.ad_badges.remove(badge_key)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Content selection
            st.markdown("### 📝 Ad Content")
            content = st.session_state.marketing_content or {}
            
            col1, col2 = st.columns(2)
            with col1:
                hook = st.text_input("Ad Headline:", 
                                   value=content.get('hook', f"{phone_data['name']} - Now Available!"),
                                   key="ad_hook")
            with col2:
                cta = st.text_input("Call to Action:", 
                                  value=content.get('cta', 'SHOP NOW'),
                                  key="ad_cta")
            
            # Price display
            formatted_price = format_price(st.session_state.phone_price)
            st.markdown(f"### 💰 Price: {formatted_price}")
            
            # Generate ad button
            if st.button("✨ Generate Ad", type="primary", use_container_width=True):
                with st.spinner(f"Creating {platform} ad..."):
                    try:
                        # Create ad generator
                        platform_key = platform.lower()
                        generator = AdvancedAdGenerator(platform_key)
                        
                        # Generate ad
                        ad_image = generator.generate(
                            phone_data=phone_data,
                            phone_img_url=selected_image_url,
                            hook=hook,
                            cta=cta,
                            price=st.session_state.phone_price,
                            badges=st.session_state.ad_badges,
                            hashtags=content.get('hashtags', '#TrippleK')
                        )
                        
                        # Display ad
                        st.markdown(f"### 🖼️ {platform} Ad Preview")
                        st.image(ad_image, use_container_width=True)
                        
                        # Download button
                        buf = BytesIO()
                        ad_image.save(buf, format='PNG', quality=95)
                        
                        # Create safe filename
                        safe_name = re.sub(r'[^\w\s-]', '', phone_data['name']).strip().replace(' ', '_')
                        filename = f"tripplek_{safe_name}_{platform_key}_ad.png"
                        
                        st.download_button(
                            label="📥 Download PNG",
                            data=buf.getvalue(),
                            file_name=filename,
                            mime="image/png",
                            use_container_width=True
                        )
                        
                        st.success(f"✅ {platform} ad created successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error creating ad: {str(e)}")
                        st.error(traceback.format_exc())

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 1rem;">
        <h4>Tripple K Communications</h4>
        <p>📞 {TRIPPLEK_PHONE} | 💬 {TRIPPLEK_WHATSAPP} | 🌐 {TRIPPLEK_URL}</p>
        <p>📍 {TRIPPLEK_LOCATION}</p>
        <p style="font-size: 0.9em; color: #666;">Marketing Suite v6.0 | Powered by GSM Arena API</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
