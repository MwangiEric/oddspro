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

# Global asset cache
GLOBAL_ASSETS = {
    "logo": None,
    "fonts": {},
    "icons": {},
    "images": {}  # Cache for downloaded images
}

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

@retry_on_error(max_retries=2)
def download_image_safe(url: str) -> Optional[Image.Image]:
    """Download image safely with caching"""
    # Check if image is already cached
    if url in GLOBAL_ASSETS["images"]:
        return GLOBAL_ASSETS["images"][url].copy()

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

            # Convert to RGB to avoid issues (consistent with final_ds.py)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Cache the image
            GLOBAL_ASSETS["images"][url] = img
            return img.copy()
    except Exception as e:
        print(f"Download error for {url}: {str(e)}")
    return None

def get_logo_safe() -> Optional[Image.Image]:
    """Get logo with proper transparency handling - cached globally"""
    if GLOBAL_ASSETS["logo"] is not None:
        # Return a copy to prevent any modifications
        return GLOBAL_ASSETS["logo"].copy()

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(LOGO_URL, timeout=10, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

            # Convert to RGBA for transparency (consistent with final_ds.py)
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

            # Cache the logo globally
            GLOBAL_ASSETS["logo"] = img
            return img.copy()
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

def remove_background_smart(image: Image.Image) -> Image.Image:
    """Smart background removal that preserves phone details"""
    try:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        data = image.getdata()
        new_data = []
        
        for item in data:
            r, g, b, a = item
            # Keep most colors, only remove near-white background
            if r > 245 and g > 245 and b > 245:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        image.putdata(new_data)
        return image
    except:
        return image

def create_phone_image_for_ad(image_url: str, target_size: Tuple[int, int]) -> Optional[Image.Image]:
    """Create phone image for ad with creative white background design"""
    try:
        phone_img = download_image_safe(image_url)
        if not phone_img:
            return None

        # Create a clean copy
        phone_img = phone_img.copy()

        # Convert to RGBA for transparency
        if phone_img.mode != 'RGBA':
            phone_img = phone_img.convert('RGBA')

        # Calculate resize dimensions maintaining aspect ratio
        original_width, original_height = phone_img.size
        target_width, target_height = target_size

        # Calculate scaling factor (80% of available space for better padding)
        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        scale = min(width_ratio, height_ratio) * 0.8

        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        # Resize
        phone_img = phone_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create new image with a subtle white background that looks part of the design
        result = Image.new('RGBA', target_size, (255, 255, 255, 255))  # Fully white background

        # Add a subtle pattern or gradient to make it look more like part of the design
        draw = ImageDraw.Draw(result)

        # Add subtle corner highlights to make it look more like a design element
        corner_size = min(target_size) // 10
        highlight_color = (250, 250, 250, 255)  # Very light gray-white

        # Add subtle corner highlights
        draw.rectangle([0, 0, corner_size, corner_size], fill=highlight_color)
        draw.rectangle([target_size[0]-corner_size, 0, target_size[0], corner_size], fill=highlight_color)
        draw.rectangle([0, target_size[1]-corner_size, corner_size, target_size[1]], fill=highlight_color)
        draw.rectangle([target_size[0]-corner_size, target_size[1]-corner_size, target_size[0], target_size[1]], fill=highlight_color)

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
    
    # Remove any non-digit characters
    clean_price = re.sub(r'[^\d]', '', price_str)
    
    try:
        if clean_price:
            num = int(clean_price)
            return f"{num:,}"
    except:
        pass
    
    return "99,999"

def copy_to_clipboard(text: str):
    """Copy text to clipboard using JavaScript"""
    js_code = f"""
    <script>
    function copyToClipboard() {{
        const text = `{text}`;
        navigator.clipboard.writeText(text).then(() => {{
            alert('Copied to clipboard!');
        }});
    }}
    copyToClipboard();
    </script>
    """
    st.components.v1.html(js_code, height=0)

def remove_background_simple(image: Image.Image) -> Image.Image:
    """Simple background removal - fallback function"""
    try:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Get the data of the image
        data = image.getdata()

        # Create a new list to store the new image data
        newData = []

        for item in data:
            # If the pixel is close to white (background), make it transparent
            if item[0] > 240 and item[1] > 240 and item[2] > 240:  # RGB values close to white
                newData.append((255, 255, 255, 0))  # Transparent
            else:
                newData.append(item)  # Keep original pixel

        # Update image data
        image.putdata(newData)
        return image
    except Exception as e:
        print(f"Error in simple background removal: {e}")
        return image

def remove_background_with_rembg(image: Image.Image) -> Image.Image:
    """Remove background using rembg if available"""
    if not REMBG_AVAILABLE:
        # If rembg is not available, return the original image
        return image

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

def get_icon_safe(url: str, name: str) -> Optional[Image.Image]:
    """Get icon with caching"""
    if name in GLOBAL_ASSETS["icons"]:
        return GLOBAL_ASSETS["icons"][name].copy()

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

            # Cache the icon
            GLOBAL_ASSETS["icons"][name] = img
            return img.copy()
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

        # Load fonts with global caching
        # Try multiple font paths
        font_paths = [
            "assets/fonts/poppins.ttf",
            "poppins.ttf",
            "C:/Windows/Fonts/arial.ttf",  # Fallback on Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux fallback
        ]

        font_path = None
        for path in font_paths:
            try:
                ImageFont.truetype(path, 12)  # Test if font is available
                font_path = path
                break
            except:
                continue

        # If no font is found, use default
        if font_path is None:
            # Fallback to default fonts
            default = ImageFont.load_default()
            GLOBAL_ASSETS["fonts"][platform] = {
                "title": default,
                "subtitle": default,
                "body": default,
                "small": default,
                "price": default
            }
        else:
            # Check if fonts for this platform are already cached
            if platform not in GLOBAL_ASSETS["fonts"]:
                try:
                    # Cache different font sizes for this platform
                    GLOBAL_ASSETS["fonts"][platform] = {
                        "title": ImageFont.truetype(font_path, 42 if platform == "instagram" else 36),
                        "subtitle": ImageFont.truetype(font_path, 28 if platform == "instagram" else 24),
                        "body": ImageFont.truetype(font_path, 22 if platform == "instagram" else 18),
                        "small": ImageFont.truetype(font_path, 16 if platform == "instagram" else 14),
                        "price": ImageFont.truetype(font_path, 38 if platform == "instagram" else 32)
                    }
                except:
                    # Fallback to default fonts
                    default = ImageFont.load_default()
                    GLOBAL_ASSETS["fonts"][platform] = {
                        "title": default,
                        "subtitle": default,
                        "body": default,
                        "small": default,
                        "price": default
                    }

        # Use cached fonts
        self.title_font = GLOBAL_ASSETS["fonts"][platform]["title"]
        self.subtitle_font = GLOBAL_ASSETS["fonts"][platform]["subtitle"]
        self.body_font = GLOBAL_ASSETS["fonts"][platform]["body"]
        self.small_font = GLOBAL_ASSETS["fonts"][platform]["small"]
        self.price_font = GLOBAL_ASSETS["fonts"][platform]["price"]
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_base_image(self) -> Image.Image:
        """Create base image with gradient background"""
        base_color = self.hex_to_rgb(self.layout["background"])
        img = Image.new('RGB', (self.width, self.height), base_color)
        
        # Add subtle gradient
        draw = ImageDraw.Draw(img)
        if self.platform in ["facebook", "instagram"]:
            for y in range(self.height):
                alpha = int(255 * (y / self.height))
                color = tuple(
                    int(c * (0.7 + 0.3 * (y / self.height)))
                    for c in base_color
                )
                draw.line([(0, y), (self.width, y)], fill=color)
        
        return img
    
    def draw_logo(self, img: Image.Image) -> Image.Image:
        """Draw logo"""
        region = self.layout["regions"]["logo"]
        logo = get_logo_safe()  # This will use the cached version after first load

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
        """Draw selected badges - positioned on the right"""
        if not badges:
            return

        region = self.layout["regions"]["badges"]
        x, y = region["x"], region["y"]
        max_width = region["width"]

        # Calculate total width needed for all badges to position them on the right
        badge_widths = []
        badge_height = 40
        badge_spacing = 10

        # Calculate individual badge widths
        for badge_key in badges[:4]:  # Max 4 badges
            if badge_key in BADGE_OPTIONS:
                badge = BADGE_OPTIONS[badge_key]
                badge_text = f"{badge['icon']} {badge['text']}"

                # Calculate text size
                bbox = draw.textbbox((0, 0), badge_text, font=self.small_font)
                text_width = bbox[2] - bbox[0] + 20
                badge_widths.append(text_width)

        # Calculate total width needed
        total_badge_width = sum(badge_widths) + (len(badge_widths) - 1) * badge_spacing if badge_widths else 0

        # Position badges on the right side of the region
        current_x = x + max_width - total_badge_width  # Start from right
        if current_x < x:  # If badges are too wide, just start from x
            current_x = x

        # Draw each badge
        for i, badge_key in enumerate(badges[:4]):  # Max 4 badges
            if badge_key in BADGE_OPTIONS:
                badge = BADGE_OPTIONS[badge_key]
                badge_text = f"{badge['icon']} {badge['text']}"

                # Calculate text size
                bbox = draw.textbbox((0, 0), badge_text, font=self.small_font)
                text_width = badge_widths[i]

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
            
            # Add glow effect
            draw = ImageDraw.Draw(img, 'RGBA')
            glow_color = (255, 215, 0, 20)
            glow_radius = 30
            for i in range(3):
                draw.ellipse(
                    [x + phone_img.width//2 - glow_radius + i*5, 
                     y + phone_img.height - 10 - i*5,
                     x + phone_img.width//2 + glow_radius - i*5,
                     y + phone_img.height + 10 + i*5],
                    outline=glow_color
                )
        
        return img

    def wrap_text(self, draw, text, max_width, font):
        """Wrap text to fit within specified width"""
        lines = []

        if not text:
            return lines

        # Split text by lines first (in case there are manual line breaks)
        paragraphs = text.split('\n')

        for paragraph in paragraphs:
            words = paragraph.split(' ')
            current_line = ''

            for word in words:
                # Test if adding the word would exceed max width
                test_line = current_line + ' ' + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]

                if text_width <= max_width:
                    current_line = test_line
                else:
                    # If current line is empty, the word is too long by itself
                    if not current_line:
                        # Try to break the long word into smaller parts
                        wrapped_word = self._break_word(draw, word, max_width, font)
                        lines.extend(wrapped_word)
                    else:
                        # Add the current line and start a new one with the word
                        lines.append(current_line)
                        current_line = word

            # Add the last line if it exists
            if current_line:
                lines.append(current_line)

        return lines

    def _break_word(self, draw, word, max_width, font):
        """Break a single word into smaller parts that fit within max_width"""
        if not word:
            return []

        # If the word fits, return it as is
        bbox = draw.textbbox((0, 0), word, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return [word]

        # Break the word into characters and fit as many as possible per line
        chars = list(word)
        lines = []
        current_part = ''

        for char in chars:
            test_part = current_part + char
            bbox = draw.textbbox((0, 0), test_part, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_part = test_part
            else:
                if current_part:  # Add the current part if it's not empty
                    lines.append(current_part)
                    current_part = char  # Start new part with current character
                else:  # The single character is too wide, add it anyway
                    lines.append(char)
                    current_part = ''

        if current_part:  # Add any remaining characters
            lines.append(current_part)

        return lines

    def draw_content(self, img: Image.Image, draw: ImageDraw.ImageDraw,
                    phone_data: dict, hook: str = ""):
        """Draw content section"""
        region = self.layout["regions"]["content"]
        x, y = region["x"], region["y"]

        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_BLACK
        accent_color = BRAND_GOLD

        # Hook text with wrapping
        if hook:
            wrapped_hook = self.wrap_text(draw, hook.upper(), region["width"] - 20, self.title_font)
            for line in wrapped_hook:
                draw.text((x, y), line, fill=accent_color, font=self.title_font)
                y += self.title_font.size + 5  # Add spacing between lines
            y += 10  # Additional spacing after hook

        # Phone name with wrapping
        phone_name = phone_data["name"]
        wrapped_name = self.wrap_text(draw, phone_name, region["width"] - 20, self.subtitle_font)
        for line in wrapped_name:
            draw.text((x, y), line, fill=text_color, font=self.subtitle_font)
            y += self.subtitle_font.size + 5  # Add spacing between lines
        y += 15  # Additional spacing after name

        # Draw 6 specific specs: screen, camera, processor, ram, storage, battery
        all_specs = [
            ("🖥️", "Screen", phone_data["specs"].get("screen", "N/A")),
            ("📸", "Camera", phone_data["specs"].get("camera", "N/A")),
            ("🚀", "Processor", phone_data["specs"].get("chipset", "N/A")),
            ("⚡", "RAM", phone_data["specs"].get("ram", "N/A")),
            ("💾", "Storage", phone_data["specs"].get("storage", "N/A")),
            ("🔋", "Battery", phone_data["specs"].get("battery", "N/A")),
        ]

        specs_displayed = 0
        for icon, label, value in all_specs:
            if value != "N/A" and value != "Check details" and specs_displayed < 6:  # Now allow up to 6 specs
                # Draw spec with wrapping if needed
                spec_text = f"{label}: {value}"
                wrapped_spec = self.wrap_text(draw, spec_text, region["width"] - 60, self.body_font)

                for i, line in enumerate(wrapped_spec):
                    if i == 0:
                        # For the first line, draw the icon and the first part of the text
                        draw.text((x, y), icon, fill=accent_color, font=self.body_font)
                        draw.text((x + 35, y), line, fill=text_color, font=self.body_font)
                    else:
                        # For subsequent lines, just draw the text indented
                        draw.text((x + 35, y), line, fill=text_color, font=self.body_font)

                    y += self.body_font.size + 8  # Increased spacing between lines (was +3)

                    # Ensure we don't exceed the content region
                    if y >= region["y"] + region["height"] - (self.body_font.size + 5):
                        break

                specs_displayed += 1

                # Only continue to next spec if we have space
                if y >= region["y"] + region["height"] - (self.body_font.size + 5):
                    break
    
    def draw_price(self, img: Image.Image, draw: ImageDraw.ImageDraw, price: str = ""):
        """Draw price badge - compact version"""
        region = self.layout["regions"]["price"]
        x, y = region["x"], region["y"]

        # Format price
        formatted_price = format_price(price)

        # Create price text
        price_text = f"KES {formatted_price}"
        if self.platform == "whatsapp":
            price_text = formatted_price  # Just the number for WhatsApp

        # Calculate text dimensions to create a tight-fitting badge
        bbox = draw.textbbox((0, 0), price_text, font=self.price_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Create a smaller badge with padding
        padding_x = 15
        padding_y = 8
        badge_width = text_width + (2 * padding_x)
        badge_height = text_height + (2 * padding_y)

        # Draw background with tight fit
        price_bg_color = self.hex_to_rgb(BRAND_GOLD) if self.platform in ["facebook", "instagram"] else self.hex_to_rgb(BRAND_MAROON)
        draw.rounded_rectangle(
            [x, y, x + badge_width, y + badge_height],
            radius=10,
            fill=price_bg_color
        )

        # Draw price text centered in the tight badge
        text_x = x + padding_x
        text_y = y + padding_y

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
        """Draw contact information with proper positioning"""
        region = self.layout["regions"]["contact"]
        total_width = region["width"]
        total_height = region["height"]

        # Text color
        text_color = BRAND_MAROON
        icon_size = (24, 24)

        # Social media icons (top right)
        social_icon = None
        if self.platform == "facebook":
            social_icon = get_icon_safe(PLATFORM_INFO["facebook"]["icon_url"], "facebook_contact_icon")
        elif self.platform in ["instagram", "whatsapp"]:  # Using same icon for both
            social_icon = get_icon_safe(PLATFORM_INFO["tiktok"]["icon_url"], "tiktok_contact_icon")

        if social_icon:
            social_icon_resized = social_icon.resize(icon_size, Image.Resampling.LANCZOS)
            social_x = region["x"] + total_width - 35  # Top right
            social_y = region["y"] + 5  # Top of region
            img.paste(social_icon_resized, (social_x, social_y), social_icon_resized)

        # Call icon (a distance below CTA area)
        call_icon = get_icon_safe("https://ik.imagekit.io/ericmwangi/call.png?updatedAt=1765804033399", "call_contact")
        call_x = region["x"] + 10
        call_y = region["y"] + 40  # Below CTA area
        if call_icon:
            call_icon_resized = call_icon.resize(icon_size, Image.Resampling.LANCZOS)
            img.paste(call_icon_resized, (call_x, call_y), call_icon_resized)

        # Draw call text next to icon
        draw.text((call_x + 30, call_y + 2), f"{TRIPPLEK_PHONE}", fill=text_color, font=self.small_font)

        # WhatsApp icon (below call with good spacing)
        whatsapp_icon = get_icon_safe("https://ik.imagekit.io/ericmwangi/whatsapp.png?updatedAt=1765797099945", "whatsapp_contact")
        whatsapp_x = region["x"] + 10
        whatsapp_y = call_y + 35  # Below call with spacing
        if whatsapp_icon:
            whatsapp_icon_resized = whatsapp_icon.resize(icon_size, Image.Resampling.LANCZOS)
            img.paste(whatsapp_icon_resized, (whatsapp_x, whatsapp_y), whatsapp_icon_resized)

        # Draw WhatsApp text next to icon
        draw.text((whatsapp_x + 30, whatsapp_y + 2), f"{TRIPPLEK_WHATSAPP}", fill=text_color, font=self.small_font)
    
    def draw_footer(self, img: Image.Image, draw: ImageDraw.ImageDraw, hashtags: str = ""):
        """Draw footer with website, location, and hashtags"""
        region = self.layout["regions"]["footer"]
        x, y = region["x"], region["y"]

        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_BLACK
        total_width = region["width"]

        # Location - bottom left
        location_text = f"📍 {TRIPPLEK_LOCATION}"
        location_bbox = draw.textbbox((0, 0), location_text, font=self.small_font)
        location_x = x + 10  # Left side with margin
        location_y = y + region["height"] - 50  # Bottom area
        draw.text((location_x, location_y), location_text, fill=text_color, font=self.small_font)

        # Website - bottom middle
        website_text = f"🌐 {TRIPPLEK_URL}"
        website_bbox = draw.textbbox((0, 0), website_text, font=self.small_font)
        website_width = website_bbox[2] - website_bbox[0]
        website_x = x + (total_width - website_width) // 2  # Centered
        website_y = y + region["height"] - 50  # Same level as location
        draw.text((website_x, website_y), website_text, fill=text_color, font=self.small_font)

        # One badge - bottom right
        # Use one of the provided badges if available
        if hasattr(self, 'badges') and self.badges:
            # Use the first badge as an example
            first_badge = self.badges[0] if self.badges else None
            if first_badge and first_badge in BADGE_OPTIONS:
                badge = BADGE_OPTIONS[first_badge]
                badge_text = f"{badge['icon']} {badge['text']}"
                badge_bbox = draw.textbbox((0, 0), badge_text, font=self.small_font)
                badge_width = badge_bbox[2] - badge_bbox[0]
                badge_x = x + total_width - badge_width - 15  # Right side with margin
                badge_y = y + region["height"] - 50  # Same level
                badge_color = self.hex_to_rgb(badge['color'])

                # Draw badge background
                draw.rounded_rectangle(
                    [badge_x - 5, badge_y - 3, badge_x + badge_width + 5, badge_y + 20],
                    radius=10,
                    fill=badge_color
                )

                # Draw badge text
                draw.text((badge_x, badge_y), badge_text, fill=BRAND_WHITE, font=self.small_font)
        else:
            # If no specific badge, just show a simple "Official" badge
            badge_text = "✅ OFFICIAL"
            badge_bbox = draw.textbbox((0, 0), badge_text, font=self.small_font)
            badge_width = badge_bbox[2] - badge_bbox[0]
            badge_x = x + total_width - badge_width - 15  # Right side with margin
            badge_y = y + region["height"] - 50  # Same level
            badge_color = self.hex_to_rgb("#4CAF50")  # Green color

            # Draw badge background
            draw.rounded_rectangle(
                [badge_x - 5, badge_y - 3, badge_x + badge_width + 5, badge_y + 20],
                radius=10,
                fill=badge_color
            )

            # Draw badge text
            draw.text((badge_x, badge_y), badge_text, fill=BRAND_WHITE, font=self.small_font)

        # Hashtags - above the bottom elements
        if hashtags:
            hashtag_y = y + region["height"] - 80  # Above other elements
            hashtag_lines = hashtags.split('\n')
            for line in hashtag_lines:
                if line.strip():
                    # Check if we're approaching the footer region boundary
                    if hashtag_y <= y + 10:  # Stop if we get too high
                        break
                    draw.text((x + 10, hashtag_y), line.strip(), fill=BRAND_GOLD, font=self.small_font)
                    hashtag_y -= 25  # Move up for next line
    
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

    # Format specs
    specs = phone_data["specs"]
    specs_text = ""
    if specs.get("screen", "N/A") != "N/A":
        specs_text += f"• Screen: {specs['screen']}\n"
    if specs.get("camera", "N/A") != "N/A":
        specs_text += f"• Camera: {specs['camera']}\n"
    if specs.get("ram", "N/A") != "N/A":
        specs_text += f"• RAM: {specs['ram']}\n"
    if specs.get("storage", "N/A") != "N/A":
        specs_text += f"• Storage: {specs['storage']}\n"
    if specs.get("chipset", "N/A") != "N/A":
        specs_text += f"• Chipset: {specs['chipset']}\n"
    if specs.get("battery", "N/A") != "N/A":
        specs_text += f"• Battery: {specs['battery']}\n"

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

    # Use platform-specific content if available, otherwise use default format
    whatsapp_post = content.get('whatsapp', f"""📱 *{phone_data['name']}*

{content.get('hook', 'Available Now at Tripple K!')}

{specs_text}
💰 *Price: KES {formatted_price}*

{content.get('description', 'Get this amazing phone at Tripple K Communications!')}

{'' if not badges_text else badges_text + '\n\n'}

🚀 *{cta}* - Call: {TRIPPLEK_PHONE}
💬 WhatsApp: {TRIPPLEK_WHATSAPP}
📍 Location: {TRIPPLEK_LOCATION}
🌐 {TRIPPLEK_URL}

{content.get('hashtags', '#TrippleK #Smartphones')}""")

    # Facebook Post
    facebook_post = content.get('facebook', f"""{phone_data['name']}

{content.get('hook', 'Now Available at Tripple K Communications!')}

{specs_text}
Price: KES {formatted_price}

{content.get('description', 'Visit us today and get the best deal!')}

{'' if not badges_text else badges_text}

🚀 {cta}
📍 {TRIPPLEK_LOCATION}
📞 {TRIPPLEK_PHONE}
🌐 {TRIPPLEK_URL}

{content.get('hashtags', '#TrippleK #Smartphones #PhoneDeals')}""")

    # TikTok/Instagram Post
    tiktok_post = content.get('tiktok', f"""{phone_data['name']} 🔥

{content.get('hook', 'Check out this amazing phone!')}

{specs_text}
💸 KES {formatted_price}

{content.get('description', 'Available at Tripple K Communications')}

{'' if not badges_text else badges_text}

🚀 {cta} | 📍 {TRIPPLEK_LOCATION}
📞 {TRIPPLEK_PHONE}

{content.get('hashtags', '#TrippleK #Phone #Tech')}""")

    return {
        "whatsapp": whatsapp_post,
        "facebook": facebook_post,
        "tiktok": tiktok_post
    }

# ==========================================
# MARKETING CONTENT GENERATION
# ==========================================

def generate_marketing_content(phone_data: dict) -> dict:
    """Generate marketing content using AI or fallback"""
    if not client:
        # Fallback content when no API key is available
        return {
            "hook": f"{phone_data['name']} - Now Available!",
            "cta": "SHOP NOW",
            "description": f"Get the amazing {phone_data['name']} at Tripple K Communications! With top-notch features and official warranty.",
            "hashtags": "#TrippleK #Smartphones #Deals #Tech",
            "facebook": f"{phone_data['name']} - Now Available at Tripple K Communications! Featuring great specs and official warranty. Visit us in CBD Opposite MKU Towers.",
            "whatsapp": f"📱 {phone_data['name']} now available!\nGreat specs & warranty. Visit: CBD Opposite MKU Towers\nCall: {TRIPPLEK_PHONE}",
            "tiktok": f"🔥 New {phone_data['name']} just dropped!\nCheck out these specs! 💥"
        }

    try:
        # Get phone specs
        specs = phone_data.get("specs", {})
        screen = specs.get("screen", "N/A")
        camera = specs.get("camera", "N/A")
        ram = specs.get("ram", "N/A")
        storage = specs.get("storage", "N/A")
        chipset = specs.get("chipset", "N/A")
        battery = specs.get("battery", "N/A")

        # Create prompt for content generation
        prompt = f"""
        Create marketing content for {phone_data['name']}:

        Specifications:
        - Screen: {screen}
        - Camera: {camera}
        - RAM: {ram}
        - Storage: {storage}
        - Chipset: {chipset}
        - Battery: {battery}

        Company: Tripple K Communications
        Location: {TRIPPLEK_LOCATION}
        Contact: {TRIPPLEK_PHONE}
        Website: {TRIPPLEK_URL}

        Generate content in this format:
        Hook: [catchy headline under 40 characters]
        CTA: [call to action under 30 characters]
        Description: [2-3 sentences marketing description under 200 characters]
        Hashtags: [3-5 relevant hashtags separated by spaces]
        Facebook: [2-3 sentences for Facebook post, include location and contact]
        WhatsApp: [Short forwardable message with phone number and location]
        TikTok: [Trendy 1-2 lines for TikTok, focus on excitement]

        Example:
        Hook: {phone_data['name']} - Now Available!
        CTA: Shop Now
        Description: Get the amazing {phone_data['name']} at Tripple K Communications! With top-notch features and official warranty.
        Hashtags: #TrippleK #Smartphones #Deals #Tech
        Facebook: {phone_data['name']} now available at Tripple K Communications! Visit us in {TRIPPLEK_LOCATION} for the best deals. Call {TRIPPLEK_PHONE}
        WhatsApp: 📱 {phone_data['name']} now available!\nGreat specs & warranty. Visit: {TRIPPLEK_LOCATION}\nCall: {TRIPPLEK_PHONE}
        TikTok: 🔥 New {phone_data['name']} just dropped!\nCheck out these specs! 💥
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )

        if response.choices and response.choices[0].message:
            content_text = response.choices[0].message.content.strip()

            # Parse the response
            lines = content_text.split('\n')
            content = {
                "hook": "",
                "cta": "",
                "description": "",
                "hashtags": "",
                "facebook": "",
                "whatsapp": "",
                "tiktok": ""
            }

            for line in lines:
                if line.startswith("Hook:"):
                    content["hook"] = line[5:].strip()
                elif line.startswith("CTA:"):
                    content["cta"] = line[4:].strip()
                elif line.startswith("Description:"):
                    content["description"] = line[12:].strip()
                elif line.startswith("Hashtags:"):
                    content["hashtags"] = line[9:].strip()
                elif line.startswith("Facebook:"):
                    content["facebook"] = line[9:].strip()
                elif line.startswith("WhatsApp:"):
                    content["whatsapp"] = line[11:].strip()
                elif line.startswith("TikTok:"):
                    content["tiktok"] = line[7:].strip()

            # Fill in any missing values with defaults
            if not content["hook"]:
                content["hook"] = f"{phone_data['name']} - Now Available!"
            if not content["cta"]:
                content["cta"] = "SHOP NOW"
            if not content["description"]:
                content["description"] = f"Get the amazing {phone_data['name']} at Tripple K Communications! With top-notch features and official warranty."
            if not content["hashtags"]:
                content["hashtags"] = "#TrippleK #Smartphones #Deals #Tech"
            if not content["facebook"]:
                content["facebook"] = f"{phone_data['name']} - Now Available at Tripple K Communications! Featuring great specs and official warranty. Visit us in {TRIPPLEK_LOCATION}."
            if not content["whatsapp"]:
                content["whatsapp"] = f"📱 {phone_data['name']} now available!\nGreat specs & warranty. Visit: {TRIPPLEK_LOCATION}\nCall: {TRIPPLEK_PHONE}"
            if not content["tiktok"]:
                content["tiktok"] = f"🔥 New {phone_data['name']} just dropped!\nCheck out these specs! 💥"

            return content
        else:
            # Fallback content
            return {
                "hook": f"{phone_data['name']} - Now Available!",
                "cta": "SHOP NOW",
                "description": f"Get the amazing {phone_data['name']} at Tripple K Communications! With top-notch features and official warranty.",
                "hashtags": "#TrippleK #Smartphones #Deals #Tech",
                "facebook": f"{phone_data['name']} - Now Available at Tripple K Communications! Featuring great specs and official warranty. Visit us in {TRIPPLEK_LOCATION}.",
                "whatsapp": f"📱 {phone_data['name']} now available!\nGreat specs & warranty. Visit: {TRIPPLEK_LOCATION}\nCall: {TRIPPLEK_PHONE}",
                "tiktok": f"🔥 New {phone_data['name']} just dropped!\nCheck out these specs! 💥"
            }

    except Exception as e:
        print(f"Error generating content: {e}")
        # Fallback content
        return {
            "hook": f"{phone_data['name']} - Now Available!",
            "cta": "SHOP NOW",
            "description": f"Get the amazing {phone_data['name']} at Tripple K Communications! With top-notch features and official warranty.",
            "hashtags": "#TrippleK #Smartphones #Deals #Tech",
            "facebook": f"{phone_data['name']} - Now Available at Tripple K Communications! Featuring great specs and official warranty. Visit us in {TRIPPLEK_LOCATION}.",
            "whatsapp": f"📱 {phone_data['name']} now available!\nGreat specs & warranty. Visit: {TRIPPLEK_LOCATION}\nCall: {TRIPPLEK_PHONE}",
            "tiktok": f"🔥 New {phone_data['name']} just dropped!\nCheck out these specs! 💥"
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
    if "generated_ads" not in st.session_state:
        st.session_state.generated_ads = {}
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

            # Create a dropdown for phone selection
            phone_names = [phone.get("name", "Unknown Phone") for phone in results]
            selected_phone_name = st.selectbox(
                "Choose a phone:",
                options=phone_names,
                key="phone_selector"
            )

            # Find the selected phone in results
            selected_idx = next((i for i, phone in enumerate(results) if phone.get("name") == selected_phone_name), -1)

            if selected_idx != -1 and selected_idx != st.session_state.selected_phone_index:
                with st.spinner("Loading phone details..."):
                    st.session_state.selected_phone_index = selected_idx
                    phone = results[selected_idx]

                    phone_name = phone.get("name", "Unknown Phone")
                    phone_id = phone.get("id", "")

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
                        if phone.get("image") and phone.get("image") not in images:
                            images.insert(0, phone.get("image"))

                        st.session_state.phone_images = images
                        st.session_state.selected_image_index = 1 if len(images) > 1 else 0  # Use image 2 as default (index 1)
                        st.session_state.ad_image_index = 1 if len(images) > 1 else 0  # Use image 2 as default (index 1)
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
                    # Show image selection for viewing
                    st.markdown("**Select an image to view:**")
                    
                    # Create a grid of thumbnails
                    cols = st.columns(4)
                    for idx in range(min(8, len(images))):
                        with cols[idx % 4]:
                            try:
                                thumb = download_image_safe(images[idx])
                                if thumb:
                                    thumb.thumbnail((80, 80))
                                    st.image(thumb, use_container_width=True)
                                    if st.button(f"View", key=f"view_img_{idx}", use_container_width=True):
                                        st.session_state.selected_image_index = idx
                                        st.rerun()
                            except:
                                st.button(f"Img {idx+1}", key=f"img_btn_{idx}", disabled=True, use_container_width=True)
                    
                    # Show selected image
                    selected_idx = st.session_state.selected_image_index
                    if selected_idx < len(images):
                        try:
                            phone_img = download_image_safe(images[selected_idx])
                            if phone_img:
                                st.markdown(f"**Selected Image {selected_idx+1}:**")
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

                # Display more specific specs: screen, camera, processor, ram, storage, battery
                display_specs = [
                    ("🖥️ Screen", phone_data["specs"].get('screen', 'N/A')),
                    ("📸 Camera", phone_data["specs"].get('camera', 'N/A')),
                    ("🚀 Processor", phone_data["specs"].get('chipset', 'N/A')),
                    ("⚡ RAM", phone_data["specs"].get('ram', 'N/A')),
                    ("💾 Storage", phone_data["specs"].get('storage', 'N/A')),
                    ("🔋 Battery", phone_data["specs"].get('battery', 'N/A')),
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

                        if specs_displayed >= 6:  # Stop after showing 6 specs
                            break

                st.markdown('</div>', unsafe_allow_html=True)
                
                # Price input
                st.markdown("### 💰 Set Price")
                price = st.text_input("Enter price (e.g., 45,999):",
                                    value=st.session_state.phone_price,
                                    placeholder="e.g., 45,999 or 45999",
                                    key="tab1_price")

                if st.button("💰 Set Price", key="set_price_btn", use_container_width=True):
                    if price:
                        st.session_state.phone_price = price
                        formatted_price = format_price(price)
                        st.success(f"✅ Price set to KES {formatted_price}")
                        st.rerun()
                    else:
                        st.warning("Please enter a valid price")

                # Show current price
                if st.session_state.phone_price:
                    formatted_price = format_price(st.session_state.phone_price)
                    st.markdown(f'<div class="price-display">Current Price: KES {formatted_price}</div>', unsafe_allow_html=True)

    # TAB 2: CREATE CONTENT
    with tabs[1]:
        st.subheader("Create Marketing Content & Social Posts")

        if not st.session_state.current_phone:
            st.info("👈 First search and select a phone from the Find Phone tab")
        else:
            phone_data = st.session_state.current_phone

            st.markdown(f"**Selected Phone:** {phone_data['name']}")

            # Show current price
            formatted_price = format_price(st.session_state.phone_price)
            st.markdown(f"### 💰 Current Price: KES {formatted_price}")

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
            if st.button("🚀 Generate AI Content", type="primary", disabled=not client, use_container_width=True):
                with st.spinner("Creating marketing content..."):
                    content = generate_marketing_content(phone_data)

                    if content:
                        st.session_state.marketing_content = content
                        st.balloons()
                        st.success("✅ Content generated successfully!")
                        st.rerun()

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
                                       value=content.get('hashtags', '#TrippleK #Smartphones #Deals #Tech'),
                                       key="content_tags")

                # Platform-specific content
                st.markdown("### 📱 Platform-Specific Content")

                facebook_post = st.text_area("Facebook Post:",
                                           value=content.get('facebook', f"{phone_data['name']} - Now Available at Tripple K Communications! Featuring great specs and official warranty."),
                                           height=100,
                                           key="facebook_post")
                whatsapp_post = st.text_area("WhatsApp Message:",
                                           value=content.get('whatsapp', f"📱 {phone_data['name']} now available!"),
                                           height=100,
                                           key="whatsapp_post")
                tiktok_post = st.text_area("TikTok Caption:",
                                         value=content.get('tiktok', f"🔥 New {phone_data['name']} just dropped!"),
                                         height=100,
                                         key="tiktok_post")

                # Update content
                st.session_state.marketing_content = {
                    "hook": hook,
                    "cta": cta,
                    "description": description,
                    "hashtags": hashtags,
                    "facebook": facebook_post,
                    "whatsapp": whatsapp_post,
                    "tiktok": tiktok_post
                }

                # Preview
                st.markdown("### 👁️ Content Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Hook:**
                    {hook}

                    **Call to Action:**
                    {cta}
                    """)
                with col2:
                    st.markdown(f"""
                    **Description:**
                    {description}

                    **Hashtags:**
                    {hashtags}
                    """)

                # Generate social posts button
                if st.button("📱 Generate Social Posts", type="secondary", use_container_width=True):
                    with st.spinner("Creating social media posts..."):
                        social_posts = generate_social_posts(
                            phone_data=phone_data,
                            content=content,
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
                    # Note: WhatsApp doesn't have a specific icon in PLATFORM_INFO, so using default emoji
                    st.markdown('### 💬 WhatsApp Post')
                    st.code(st.session_state.social_posts["whatsapp"], language=None)

                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        if st.button("📋 Copy WhatsApp Post", key="copy_whatsapp", use_container_width=True, type="secondary"):
                            copy_to_clipboard(st.session_state.social_posts["whatsapp"])
                    with col2:
                        st.download_button(
                            label="📥 Download",
                            data=st.session_state.social_posts["whatsapp"],
                            file_name="whatsapp_post.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with col3:
                        # Create WhatsApp sharing link
                        whatsapp_text = st.session_state.social_posts["whatsapp"].replace("\n", "%0A")
                        whatsapp_url = f"https://wa.me/?text={whatsapp_text}"
                        st.link_button("📤 Share on WhatsApp", whatsapp_url, use_container_width=True, type="primary")
                    st.markdown('</div>', unsafe_allow_html=True)

                    # Facebook Post
                    st.markdown('<div class="social-post">', unsafe_allow_html=True)
                    st.markdown(f'### 👤 {PLATFORM_INFO["facebook"]["name"]} Post')
                    st.code(st.session_state.social_posts["facebook"], language=None)

                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        if st.button("📋 Copy Facebook Post", key="copy_facebook", use_container_width=True, type="secondary"):
                            copy_to_clipboard(st.session_state.social_posts["facebook"])
                    with col2:
                        st.download_button(
                            label="📥 Download",
                            data=st.session_state.social_posts["facebook"],
                            file_name="facebook_post.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with col3:
                        # Create Facebook sharing link
                        facebook_text = st.session_state.social_posts["facebook"].replace("\n", "%0A")
                        facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={requests.utils.quote(TRIPPLEK_URL)}&t={facebook_text}"
                        st.link_button("📤 Share on Facebook", facebook_url, use_container_width=True, type="primary")
                    st.markdown('</div>', unsafe_allow_html=True)

                    # TikTok/Instagram Post
                    st.markdown('<div class="social-post">', unsafe_allow_html=True)
                    st.markdown(f'### 🎵 {PLATFORM_INFO["tiktok"]["name"]} Post')
                    st.code(st.session_state.social_posts["tiktok"], language=None)

                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        if st.button("📋 Copy TikTok Post", key="copy_tiktok", use_container_width=True, type="secondary"):
                            copy_to_clipboard(st.session_state.social_posts["tiktok"])
                    with col2:
                        st.download_button(
                            label="📥 Download",
                            data=st.session_state.social_posts["tiktok"],
                            file_name="tiktok_post.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with col3:
                        # Create Instagram sharing link
                        st.link_button("📤 Share on Instagram", "https://www.instagram.com/create/", use_container_width=True, type="primary")
                    with col4:
                        # Create TikTok sharing link
                        st.link_button("📤 Share on TikTok", "https://www.tiktok.com/upload", use_container_width=True, type="primary")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Click 'Generate AI Content' or manually enter content below.")

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

            # Image selection for ad using dropdown
            st.markdown("### 🖼️ Select Image for Ad")
            if images:
                # Create dropdown for image selection
                image_options = [f"Image {i+1}" for i in range(len(images))]
                selected_image_label = st.selectbox(
                    "Choose an image:",
                    options=image_options,
                    index=st.session_state.ad_image_index,  # Use image 2 as default (index 1)
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
            else:
                st.warning("⚠️ No images available. Using default.")
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

                        # Download and share buttons
                        buf = BytesIO()
                        ad_image.save(buf, format='PNG', quality=95)

                        # Create safe filename
                        safe_name = re.sub(r'[^\w\s-]', '', phone_data['name']).strip().replace(' ', '_')
                        filename = f"tripplek_{safe_name}_{platform_key}_ad.png"

                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.download_button(
                                label="📥 Download PNG",
                                data=buf.getvalue(),
                                file_name=filename,
                                mime="image/png",
                                use_container_width=True
                            )
                        with col2:
                            # Share on Facebook
                            facebook_share_url = f"https://www.facebook.com/sharer/sharer.php?u={requests.utils.quote(TRIPPLEK_URL)}"
                            st.link_button("📤 Share on Facebook", facebook_share_url, use_container_width=True, type="secondary")
                        with col3:
                            # Share on WhatsApp
                            whatsapp_share_url = f"https://wa.me/?text=Check%20out%20this%20amazing%20{requests.utils.quote(phone_data['name'])}%20available%20at%20Tripple%20K!"
                            st.link_button("📤 Share on WhatsApp", whatsapp_share_url, use_container_width=True, type="secondary")
                        with col4:
                            # Share on Instagram
                            st.link_button("📤 Share on Instagram", "https://www.instagram.com/create/", use_container_width=True, type="secondary")

                        st.success(f"✅ {platform} ad created successfully!")

                    except Exception as e:
                        st.error(f"❌ Error creating ad: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 1rem;">
        <h4>Tripple K Communications</h4>
        <p>📞 {TRIPPLEK_PHONE} | 💬 {TRIPPLEK_WHATSAPP} | 🌐 {TRIPPLEK_URL}</p>
        <p>📍 {TRIPPLEK_LOCATION}</p>
        <p style="font-size: 0.9em; color: #666;">Marketing Suite v5.0 | Powered by GSM Arena API</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
