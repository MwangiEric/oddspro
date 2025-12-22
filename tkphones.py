import streamlit as st
import requests
import re
from datetime import datetime
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import Optional, Tuple, Dict, Any, List
import time
from functools import wraps

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

# Contact info
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# API Base URLs
API_BASE = "https://tkphsp2.vercel.app"
SEARCH_ENDPOINT = f"{API_BASE}/gsm/search"
IMAGES_ENDPOINT = f"{API_BASE}/gsm/images"
INFO_ENDPOINT = f"{API_BASE}/gsm/info"

# Icon URLs - FIXED TO USE SIMPLE EMOJIS
ICON_MAP = {
    "screen": "🖥️",
    "camera": "📸",
    "memory": "⚡",
    "storage": "💾",
    "battery": "🔋",
    "processor": "🚀",
    "android": "🪟",
    "call": "📞",
    "whatsapp": "💬",
    "facebook": "👤",
    "x": "🐦",
    "instagram": "📷",
    "tiktok": "🎵"
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
    
    .image-thumbnail {{
        cursor: pointer;
        border: 2px solid transparent;
        border-radius: 8px;
        padding: 5px;
        transition: all 0.3s;
    }}
    
    .image-thumbnail:hover {{
        border-color: {BRAND_MAROON};
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
    
    .tab-content {{
        padding: 1rem 0;
    }}
    
    .error-box {{
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# UTILITY FUNCTIONS - FIXED
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
        # Add timeout and headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            
            # Always convert to RGB to avoid issues
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            return img
        else:
            print(f"Failed to download image: HTTP {response.status_code}")
    except Exception as e:
        print(f"Download error for {url}: {str(e)}")
    return None

@st.cache_data(ttl=86400)
def get_logo_safe() -> Optional[Image.Image]:
    """Get logo with proper transparency handling"""
    try:
        img = download_image_safe(LOGO_URL)
        if img:
            # Resize logo
            img = img.resize((150, 50), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"Logo error: {e}")
        return None

def get_phone_images(phone_id: str) -> List[str]:
    """Get phone images from API - FIXED according to API documentation"""
    try:
        # According to API: GET /gsm/images/:id
        # Example: /gsm/images/xiaomi_poco_x3_pro-pictures-10802.php
        url = f"{IMAGES_ENDPOINT}/{phone_id}"
        print(f"Fetching images from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Image API response keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            
            # Extract images array from response
            if isinstance(data, dict):
                if "images" in data:
                    images = data["images"]
                    if isinstance(images, list):
                        # Filter valid URLs
                        valid_images = [img for img in images if isinstance(img, str) and img.startswith('http')]
                        print(f"Found {len(valid_images)} valid images")
                        return valid_images[:10]  # Return up to 10 images
                else:
                    # Try other possible keys
                    for key in ['pictures', 'photos', 'gallery']:
                        if key in data and isinstance(data[key], list):
                            images = data[key]
                            valid_images = [img for img in images if isinstance(img, str) and img.startswith('http')]
                            print(f"Found {len(valid_images)} images in key '{key}'")
                            return valid_images[:10]
            elif isinstance(data, list):
                # Direct array of URLs
                valid_images = [img for img in data if isinstance(img, str) and img.startswith('http')]
                return valid_images[:10]
                
    except requests.exceptions.Timeout:
        st.error(f"⏰ Timeout getting images for {phone_id}")
    except Exception as e:
        st.error(f"❌ Error getting images for {phone_id}: {e}")
    
    return []

def search_phones(query: str) -> List[Dict[str, Any]]:
    """Search for phones - FIXED according to API documentation"""
    try:
        url = f"{SEARCH_ENDPOINT}?q={requests.utils.quote(query)}"
        print(f"Searching: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        
        if response.status_code == 200:
            results = response.json()
            print(f"Found {len(results) if results else 0} results")
            return results or []
        else:
            st.error(f"❌ Search failed with status: {response.status_code}")
    except Exception as e:
        st.error(f"❌ Search error: {e}")
    
    return []

def get_phone_details(phone_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed phone information from API"""
    try:
        # According to API: GET /gsm/info/:id
        url = f"{INFO_ENDPOINT}/{phone_id}"
        print(f"Fetching phone details from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Got phone details, keys: {list(data.keys())}")
            return data
        else:
            st.error(f"❌ Failed to get phone details: HTTP {response.status_code}")
    except Exception as e:
        st.error(f"❌ Error getting phone details: {e}")
    
    return None

def extract_image_id_from_search_result(phone_data: Dict[str, Any]) -> str:
    """Extract the correct image ID from search result"""
    # According to API documentation:
    # Search returns: "id": "xiaomi_poco_x3_pro-10802.php"
    # Images endpoint expects: "xiaomi_poco_x3_pro-pictures-10802.php"
    
    phone_id = phone_data.get("id", "")
    print(f"Original phone ID: {phone_id}")
    
    if phone_id and "-" in phone_id:
        # Convert "xiaomi_poco_x3_pro-10802.php" to "xiaomi_poco_x3_pro-pictures-10802.php"
        parts = phone_id.split("-")
        print(f"Parts: {parts}")
        
        if len(parts) >= 2:
            # Join all parts except the last one, add "pictures", then add the last part
            base = "-".join(parts[:-1])
            number_part = parts[-1]
            result = f"{base}-pictures-{number_part}"
            print(f"Converted image ID: {result}")
            return result
    
    print(f"Returning original ID: {phone_id}")
    return phone_id

def simple_background_removal(image: Image.Image) -> Image.Image:
    """Remove white background simply"""
    try:
        # Convert to RGBA
        img = image.convert('RGBA')
        data = img.getdata()
        
        new_data = []
        for item in data:
            # If pixel is white (or near white), make transparent
            if item[0] > 220 and item[1] > 220 and item[2] > 220:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        return img
    except:
        return image

# ==========================================
# SPEC PARSING - IMPROVED WITH DETAILED INFO
# ==========================================

def parse_phone_specs_from_detailed_info(detailed_data: dict, search_data: dict) -> Dict[str, Any]:
    """Parse phone specs from detailed API response"""
    if not detailed_data:
        # Fallback to search data
        return parse_phone_specs_from_search(search_data)
    
    print(f"Parsing detailed data with keys: {list(detailed_data.keys())}")
    
    # Extract basic info
    name = detailed_data.get("name", search_data.get("name", "Unknown Phone"))
    phone_id = search_data.get("id", "")
    image_url = search_data.get("image", "")
    
    # Extract detailed specs
    display = detailed_data.get("display", {})
    screen_size = display.get("size", "N/A")
    
    # Extract screen size in inches
    screen = "N/A"
    if screen_size and isinstance(screen_size, str):
        inches_match = re.search(r'(\d+\.?\d*)\s*inches', screen_size, re.IGNORECASE)
        if inches_match:
            screen = f"{inches_match.group(1)} inches"
        else:
            # Try to extract just the number
            num_match = re.search(r'(\d+\.?\d*)', screen_size)
            if num_match:
                screen = f"{num_match.group(1)} inches"
    
    # Extract camera
    main_camera = detailed_data.get("mainCamera", {})
    camera_specs = main_camera.get("modules", "")
    camera = "N/A"
    if camera_specs and isinstance(camera_specs, str):
        # Extract MP values
        mp_matches = re.findall(r'(\d+\.?\d*)\s*MP', camera_specs, re.IGNORECASE)
        if mp_matches:
            camera = " + ".join(mp_matches[:3])
    
    # Extract RAM and storage from memory section
    memory_info = detailed_data.get("memory", {})
    ram = "N/A"
    storage = "N/A"
    
    if isinstance(memory_info, dict):
        internal = memory_info.get("internal", "")
        if internal and isinstance(internal, str):
            # Look for RAM
            ram_match = re.search(r'(\d+)\s*GB\s*RAM', internal, re.IGNORECASE)
            if ram_match:
                ram = f"{ram_match.group(1)}GB"
            
            # Look for storage
            storage_match = re.search(r'(\d+)\s*GB\s*(?:ROM|storage|internal)', internal, re.IGNORECASE)
            if storage_match:
                storage = f"{storage_match.group(1)}GB"
    
    # Extract battery
    battery_info = detailed_data.get("battery", {})
    battery = battery_info.get("type", "N/A")
    if battery == "N/A":
        batt_type = battery_info.get("battType", "N/A")
        if batt_type and batt_type != "N/A":
            battery = batt_type
    
    # Extract chipset and OS
    platform = detailed_data.get("platform", {})
    chipset = platform.get("chipset", "N/A")
    os_info = platform.get("os", "N/A")
    
    return {
        "name": name,
        "id": phone_id,
        "image_url": image_url,
        "screen": screen,
        "camera": camera,
        "ram": ram,
        "storage": storage,
        "battery": battery,
        "chipset": chipset,
        "os": os_info,
        "detailed_data": detailed_data,  # Store the full data for reference
    }

def parse_phone_specs_from_search(phone_data: dict) -> Dict[str, Any]:
    """Parse basic phone specs from search result (fallback)"""
    if not phone_data:
        return {"name": "Unknown Phone", "id": "unknown"}
    
    # Extract basic info from search result
    name = phone_data.get("name", "Unknown Phone")
    phone_id = phone_data.get("id", "")
    image_url = phone_data.get("image", "")
    
    return {
        "name": name,
        "id": phone_id,
        "image_url": image_url,
        "screen": "Check details",
        "camera": "Check details",
        "ram": "Check details",
        "storage": "Check details",
        "battery": "Check details",
        "chipset": "Check details",
        "os": "Check details",
    }

# ==========================================
# AD LAYOUTS - PREDEFINED POSITIONS
# ==========================================

AD_LAYOUTS = {
    "facebook": {
        "size": (1200, 630),
        "background": BRAND_MAROON,
        "regions": {
            "logo": {"x": 50, "y": 30, "width": 150, "height": 50},
            "brand": {"x": 850, "y": 30, "width": 300, "height": 60},
            "phone": {"x": 50, "y": 100, "width": 500, "height": 400},
            "content": {"x": 600, "y": 100, "width": 550, "height": 400},
            "cta": {"x": 600, "y": 520, "width": 280, "height": 60},
            "contact": {"x": 50, "y": 520, "width": 500, "height": 80},
        }
    },
    "whatsapp": {
        "size": (1080, 1080),
        "background": BRAND_WHITE,
        "regions": {
            "logo": {"x": 50, "y": 30, "width": 150, "height": 50},
            "brand": {"x": 220, "y": 30, "width": 300, "height": 60},
            "phone": {"x": 50, "y": 120, "width": 450, "height": 500},
            "content": {"x": 550, "y": 120, "width": 480, "height": 500},
            "cta": {"x": 390, "y": 900, "width": 300, "height": 60},
            "contact": {"x": 50, "y": 700, "width": 450, "height": 80},
        }
    },
    "instagram": {
        "size": (1080, 1350),
        "background": BRAND_MAROON,
        "regions": {
            "logo": {"x": 465, "y": 30, "width": 150, "height": 50},
            "brand": {"x": 540, "y": 90, "width": 300, "height": 40},
            "phone": {"x": 140, "y": 150, "width": 800, "height": 500},
            "content": {"x": 100, "y": 680, "width": 880, "height": 400},
            "cta": {"x": 390, "y": 1100, "width": 300, "height": 60},
            "contact": {"x": 100, "y": 1200, "width": 880, "height": 80},
        }
    }
}

# ==========================================
# AD GENERATOR - FIXED
# ==========================================

class SimpleAdGenerator:
    """Simple ad generator with fixed layouts"""
    
    def __init__(self, platform: str = "facebook"):
        self.platform = platform
        self.layout = AD_LAYOUTS[platform]
        self.width, self.height = self.layout["size"]
        
        # Try to load Poppins font, fallback to default
        try:
            # Try with the exact filename
            self.title_font = ImageFont.truetype("poppins.ttf", 36 if platform == "facebook" else 42)
            self.subtitle_font = ImageFont.truetype("poppins.ttf", 24 if platform == "facebook" else 28)
            self.body_font = ImageFont.truetype("poppins.ttf", 18 if platform == "facebook" else 20)
            self.small_font = ImageFont.truetype("poppins.ttf", 14 if platform == "facebook" else 16)
        except:
            try:
                # Try with Arial as fallback
                self.title_font = ImageFont.truetype("arialbd.ttf", 36 if platform == "facebook" else 42)
                self.subtitle_font = ImageFont.truetype("arialbd.ttf", 24 if platform == "facebook" else 28)
                self.body_font = ImageFont.truetype("arial.ttf", 18 if platform == "facebook" else 20)
                self.small_font = ImageFont.truetype("arial.ttf", 14 if platform == "facebook" else 16)
            except:
                # Fallback to default font
                default = ImageFont.load_default()
                self.title_font = self.subtitle_font = self.body_font = self.small_font = default
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_base_image(self) -> Image.Image:
        """Create base image with background color"""
        bg_color = self.hex_to_rgb(self.layout["background"])
        return Image.new('RGB', (self.width, self.height), bg_color)
    
    def draw_logo(self, img: Image.Image) -> Image.Image:
        """Draw logo in designated region"""
        region = self.layout["regions"]["logo"]
        logo = get_logo_safe()
        
        if logo:
            # Center logo in region
            x = region["x"] + (region["width"] - logo.width) // 2
            y = region["y"] + (region["height"] - logo.height) // 2
            img.paste(logo, (x, y))
        
        return img
    
    def draw_brand_text(self, img: Image.Image, draw: ImageDraw.ImageDraw):
        """Draw brand name and tagline"""
        region = self.layout["regions"]["brand"]
        
        # Brand name
        brand_text = "TRIPPLE K COMMUNICATIONS"
        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_MAROON
        
        draw.text(
            (region["x"], region["y"]),
            brand_text,
            fill=text_color,
            font=self.subtitle_font
        )
        
        # Tagline
        tagline_text = "100% Genuine | Official Warranty"
        draw.text(
            (region["x"], region["y"] + 30),
            tagline_text,
            fill=BRAND_GOLD,
            font=self.small_font
        )
    
    def draw_phone_image(self, img: Image.Image, phone_img_url: str) -> Image.Image:
        """Draw phone image in designated region"""
        if not phone_img_url:
            return img
        
        region = self.layout["regions"]["phone"]
        phone_img = download_image_safe(phone_img_url)
        
        if phone_img:
            # Resize to fit region
            phone_img.thumbnail((region["width"], region["height"]), Image.Resampling.LANCZOS)
            
            # Center in region
            x = region["x"] + (region["width"] - phone_img.width) // 2
            y = region["y"] + (region["height"] - phone_img.height) // 2
            
            # Add white border
            border_size = 5
            bordered = Image.new('RGB', 
                               (phone_img.width + border_size*2, 
                                phone_img.height + border_size*2), 
                               self.hex_to_rgb(BRAND_WHITE))
            bordered.paste(phone_img, (border_size, border_size))
            
            img.paste(bordered, (x, y))
        
        return img
    
    def draw_content(self, img: Image.Image, draw: ImageDraw.ImageDraw, 
                    phone_data: dict, hook: str = "", cta: str = ""):
        """Draw content in designated region"""
        region = self.layout["regions"]["content"]
        x, y = region["x"], region["y"]
        max_width = region["width"]
        
        # Text color based on platform
        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_BLACK
        
        # Hook text (if provided)
        if hook:
            draw.text((x, y), hook, fill=BRAND_GOLD, font=self.title_font)
            y += 50
        
        # Phone name
        draw.text((x, y), phone_data["name"], fill=text_color, font=self.title_font)
        y += 60
        
        # Specs with emoji icons
        specs = [
            ("screen", "Screen", phone_data.get("screen", "N/A")),
            ("camera", "Camera", phone_data.get("camera", "N/A")),
            ("memory", "RAM", phone_data.get("ram", "N/A")),
            ("storage", "Storage", phone_data.get("storage", "N/A")),
            ("battery", "Battery", phone_data.get("battery", "N/A")),
        ]
        
        for icon_key, label, value in specs:
            if value != "N/A" and value != "Check details":
                # Draw emoji icon
                icon = ICON_MAP.get(icon_key, "•")
                draw.text((x, y), icon, fill=text_color, font=self.body_font)
                
                # Draw spec text
                spec_text = f"{label}: {value}"
                draw.text((x + 30, y), spec_text, fill=text_color, font=self.body_font)
                y += 40
    
    def draw_cta_button(self, img: Image.Image, draw: ImageDraw.ImageDraw, cta: str = ""):
        """Draw CTA button"""
        region = self.layout["regions"]["cta"]
        x, y = region["x"], region["y"]
        width, height = region["width"], region["height"]
        
        # Button text
        button_text = cta if cta else ("SHOP NOW" if self.platform == "facebook" else "ORDER NOW")
        
        # Draw button background
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=10,
            fill=self.hex_to_rgb(BRAND_GOLD)
        )
        
        # Draw button text
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
        """Draw contact information"""
        region = self.layout["regions"]["contact"]
        x, y = region["x"], region["y"]
        
        # Text color
        text_color = BRAND_WHITE if self.platform in ["facebook", "instagram"] else BRAND_BLACK
        
        # Contact heading
        draw.text(
            (x, y),
            "Contact Tripple K:",
            fill=text_color,
            font=self.body_font
        )
        
        # Phone and WhatsApp
        contact_text = f"📞 {TRIPPLEK_PHONE}   💬 {TRIPPLEK_PHONE}"
        draw.text(
            (x, y + 30),
            contact_text,
            fill=text_color,
            font=self.body_font
        )
        
        # Website
        draw.text(
            (x, y + 60),
            f"🌐 {TRIPPLEK_URL}",
            fill=text_color,
            font=self.body_font
        )
    
    def generate(self, phone_data: dict, phone_img_url: str = None, 
                hook: str = "", cta: str = "") -> Image.Image:
        """Generate complete ad"""
        # Create base image
        img = self.create_base_image()
        draw = ImageDraw.Draw(img)
        
        # Draw all components
        img = self.draw_logo(img)
        self.draw_brand_text(img, draw)
        
        if phone_img_url:
            img = self.draw_phone_image(img, phone_img_url)
        
        self.draw_content(img, draw, phone_data, hook, cta)
        self.draw_cta_button(img, draw, cta)
        self.draw_contact_info(img, draw)
        
        return img

# ==========================================
# GROQ API FUNCTIONS
# ==========================================

class RateLimiter:
    """Simple rate limiter"""
    def __init__(self):
        self.calls = []

    def can_make_call(self) -> bool:
        now = time.time()
        self.calls = [t for t in self.calls if now - t < RATE_LIMIT_WINDOW]
        return len(self.calls) < RATE_LIMIT_CALLS

    def record_call(self):
        self.calls.append(time.time())

rate_limiter = RateLimiter()

def generate_marketing_content(phone_data: dict) -> Optional[Dict[str, str]]:
    """Generate marketing content"""
    if not client:
        return None

    if not rate_limiter.can_make_call():
        st.error("⏳ Please wait before making another request")
        return None

    try:
        prompt = f"""Create marketing content for {phone_data['name']}:

Specs:
- Screen: {phone_data.get('screen', 'N/A')}
- Camera: {phone_data.get('camera', 'N/A')}
- RAM: {phone_data.get('ram', 'N/A')}
- Storage: {phone_data.get('storage', 'N/A')}

Business: Tripple K Communications
Phone: {TRIPPLEK_PHONE}

Generate:
Hook: [Catchy headline, 5-7 words]
CTA: [Call to action, 2-3 words]
Description: [Short description, 1-2 sentences]
Hashtags: [5 relevant hashtags]"""

        rate_limiter.record_call()

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )

        text = response.choices[0].message.content.strip()
        
        # Simple parsing
        content = {"hook": "", "cta": "", "description": "", "hashtags": ""}
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            for key in content.keys():
                if line.lower().startswith(f"{key}:"):
                    content[key] = line.split(':', 1)[1].strip()
                    break
        
        return content

    except Exception as e:
        st.error(f"❌ Error generating content: {str(e)}")
        return None

# ==========================================
# MAIN APPLICATION - COMPLETELY REVISED
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
    if "marketing_content" not in st.session_state:
        st.session_state.marketing_content = None
    if "generated_ads" not in st.session_state:
        st.session_state.generated_ads = {}
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "selected_phone_index" not in st.session_state:
        st.session_state.selected_phone_index = -1

    # Tabs
    tabs = st.tabs(["🔍 Find Phone", "📝 Create Content", "🎨 Generate Ads"])

    # TAB 1: FIND PHONE - COMPLETELY REVISED
    with tabs[0]:
        st.subheader("Search Phone Database")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Enter phone name:", 
                                placeholder="e.g., Poco X3 Pro, iPhone 14, Samsung S23")
        with col2:
            search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_btn and query:
            with st.spinner("Searching phones..."):
                try:
                    results = search_phones(query)
                    
                    if results:
                        st.success(f"✅ Found {len(results)} phones")
                        st.session_state.search_results = results
                        st.session_state.selected_phone_index = -1  # Reset selection
                        st.rerun()
                    else:
                        st.error("❌ No phones found. Try a different search term.")
                        st.session_state.search_results = []
                        
                except Exception as e:
                    st.error(f"❌ Search error: {str(e)}")
        
        # Display search results
        if st.session_state.search_results:
            st.markdown("### 📱 Select a Phone")
            
            # Create a grid for results
            results = st.session_state.search_results
            num_cols = min(2, len(results))
            cols = st.columns(num_cols)
            
            for idx, phone in enumerate(results):
                with cols[idx % num_cols]:
                    phone_name = phone.get("name", "Unknown Phone")
                    phone_image = phone.get("image", "")
                    phone_id = phone.get("id", "")
                    
                    # Create phone card with better styling
                    is_selected = idx == st.session_state.selected_phone_index
                    card_class = "phone-card-selected" if is_selected else ""
                    
                    st.markdown(f"""
                    <div class="phone-card {card_class}">
                        <strong>{phone_name}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display phone image thumbnail if available
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
                            # Store the selected phone index
                            st.session_state.selected_phone_index = idx
                            
                            # Get detailed phone info
                            detailed_info = get_phone_details(phone_id)
                            
                            if detailed_info:
                                # Parse specs from detailed info
                                phone_data = parse_phone_specs_from_detailed_info(detailed_info, phone)
                                st.session_state.current_phone = phone_data
                                
                                # Get images using the correct image ID format
                                image_id = extract_image_id_from_search_result(phone)
                                images = get_phone_images(image_id)
                                
                                # Also include the main image from search result
                                if phone_image and phone_image not in images:
                                    images.insert(0, phone_image)
                                
                                st.session_state.phone_images = images
                                st.session_state.selected_image_index = 0
                                st.session_state.marketing_content = None  # Reset marketing content
                                
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
                    # Show thumbnail selection
                    st.markdown("**Select an image:**")
                    
                    # Create a grid for thumbnails
                    num_thumb_cols = min(4, len(images))
                    thumb_cols = st.columns(num_thumb_cols)
                    
                    for idx, img_url in enumerate(images[:num_thumb_cols*2]):  # Show up to 8 images
                        col_idx = idx % num_thumb_cols
                        with thumb_cols[col_idx]:
                            # Display thumbnail
                            try:
                                thumb = download_image_safe(img_url)
                                if thumb:
                                    thumb.thumbnail((100, 100))
                                    if st.image(thumb, use_container_width=True):
                                        pass
                                    
                                    if st.button(f"Select", key=f"select_img_{idx}", use_container_width=True):
                                        st.session_state.selected_image_index = idx
                                        st.rerun()
                            except:
                                st.button(f"Image {idx+1}", key=f"img_btn_{idx}", disabled=True, use_container_width=True)
                    
                    # Show selected image
                    selected_idx = st.session_state.selected_image_index
                    if selected_idx < len(images):
                        try:
                            phone_img = download_image_safe(images[selected_idx])
                            if phone_img:
                                st.markdown(f"**Selected Image {selected_idx+1}:**")
                                st.image(phone_img, use_container_width=True)
                            else:
                                st.warning("⚠️ Could not load selected image")
                        except Exception as e:
                            st.error(f"Error loading image: {e}")
                else:
                    st.info("📷 No images available for this phone.")
                    # Try to use the main image from search result
                    if phone_data.get("image_url"):
                        try:
                            phone_img = download_image_safe(phone_data["image_url"])
                            if phone_img:
                                st.image(phone_img, use_container_width=True, caption="Main Phone Image")
                        except:
                            pass
                    
                    # Refresh images button
                    if st.button("🔄 Try Loading Images Again", use_container_width=True):
                        if phone_data.get("id"):
                            image_id = extract_image_id_from_search_result({"id": phone_data["id"]})
                            images = get_phone_images(image_id)
                            st.session_state.phone_images = images
                            st.rerun()
            
            with col_specs:
                st.markdown("### 📋 Specifications")
                st.markdown('<div class="specs-container">', unsafe_allow_html=True)
                
                # Display specs
                display_specs = [
                    ("🖥️ Screen", phone_data.get('screen', 'N/A')),
                    ("📸 Camera", phone_data.get('camera', 'N/A')),
                    ("⚡ RAM", phone_data.get('ram', 'N/A')),
                    ("💾 Storage", phone_data.get('storage', 'N/A')),
                    ("🔋 Battery", phone_data.get('battery', 'N/A')),
                    ("🚀 Processor", phone_data.get('chipset', 'N/A')),
                    ("🪟 OS", phone_data.get('os', 'N/A')),
                ]
                
                for label, value in display_specs:
                    if value != "N/A" and value != "Check details":
                        st.markdown(f'''
                        <div class="spec-item">
                            <span class="spec-label">{label}:</span> 
                            <span class="spec-value">{value}</span>
                        </div>
                        ''', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show more details if available
                if phone_data.get('detailed_data'):
                    if st.button("📊 Show More Details", use_container_width=True):
                        detailed = phone_data['detailed_data']
                        with st.expander("Full Phone Details"):
                            for key, value in detailed.items():
                                if isinstance(value, dict):
                                    st.write(f"**{key}:**")
                                    for k, v in value.items():
                                        st.write(f"  - {k}: {v}")
                                else:
                                    st.write(f"**{key}:** {value}")

    # TAB 2: CREATE CONTENT
    with tabs[1]:
        st.subheader("Generate Marketing Content")
        
        if not st.session_state.current_phone:
            st.info("👈 First search and select a phone from the Find Phone tab")
        else:
            phone_data = st.session_state.current_phone
            
            st.markdown(f"**Selected Phone:** {phone_data['name']}")
            
            # Generate content button
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🚀 Generate AI Content", type="primary", disabled=not client, use_container_width=True):
                    with st.spinner("Creating marketing content..."):
                        content = generate_marketing_content(phone_data)
                        
                        if content:
                            st.session_state.marketing_content = content
                            st.balloons()
                            st.success("✅ Content generated successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to generate content. Please try again.")
            
            # Edit content
            if st.session_state.marketing_content:
                st.markdown("### 📝 Edit Content")
                
                content = st.session_state.marketing_content
                
                # Editable fields
                hook = st.text_input("Hook (Headline):", 
                                   value=content.get('hook', f"{phone_data['name']} - Now Available!"),
                                   placeholder="Catchy headline for your ad")
                cta = st.text_input("Call to Action:", 
                                  value=content.get('cta', 'SHOP NOW'),
                                  placeholder="e.g., SHOP NOW, ORDER TODAY")
                description = st.text_area("Description:", 
                                         value=content.get('description', f"Get the amazing {phone_data['name']} at Tripple K Communications!"),
                                         height=100,
                                         placeholder="Product description")
                hashtags = st.text_input("Hashtags:", 
                                       value=content.get('hashtags', '#TrippleK #Smartphones #Deals'),
                                       placeholder="#Hashtags separated by spaces")
                
                # Update content
                updated_content = {
                    "hook": hook,
                    "cta": cta,
                    "description": description,
                    "hashtags": hashtags
                }
                
                st.session_state.marketing_content = updated_content
                
                # Preview
                st.markdown("### 👁️ Content Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Hook:**  
                    {updated_content['hook']}
                    
                    **Call to Action:**  
                    {updated_content['cta']}
                    """)
                with col2:
                    st.markdown(f"""
                    **Description:**  
                    {updated_content['description']}
                    
                    **Hashtags:**  
                    {updated_content['hashtags']}
                    """)
            else:
                st.info("Click 'Generate AI Content' to create marketing content or manually enter content below.")
                
                # Manual content input
                st.markdown("### 📝 Manual Content Creation")
                hook = st.text_input("Hook (Headline):", 
                                   value=f"{phone_data['name']} - Now Available!",
                                   placeholder="Catchy headline for your ad")
                cta = st.text_input("Call to Action:", 
                                  value="SHOP NOW",
                                  placeholder="e.g., SHOP NOW, ORDER TODAY")
                description = st.text_area("Description:", 
                                         value=f"Get the amazing {phone_data['name']} at Tripple K Communications!",
                                         height=100,
                                         placeholder="Product description")
                hashtags = st.text_input("Hashtags:", 
                                       value="#TrippleK #Smartphones #Deals",
                                       placeholder="#Hashtags separated by spaces")
                
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
            
            # Get selected image
            selected_image_url = None
            if st.session_state.phone_images:
                selected_idx = st.session_state.selected_image_index
                if selected_idx < len(st.session_state.phone_images):
                    selected_image_url = st.session_state.phone_images[selected_idx]
            elif phone_data.get("image_url"):
                selected_image_url = phone_data["image_url"]
            
            if selected_image_url:
                st.success(f"✅ Using selected image")
            else:
                st.warning("⚠️ No image available for this phone.")
            
            # Platform selection
            st.markdown("### 🎯 Select Platform")
            platform = st.radio("Choose social media platform:", 
                              ["Facebook", "WhatsApp", "Instagram"],
                              horizontal=True,
                              label_visibility="collapsed")
            
            # Content selection
            st.markdown("### 📝 Ad Content")
            content = st.session_state.marketing_content or {}
            
            col1, col2 = st.columns(2)
            with col1:
                hook = st.text_input("Ad Headline:", 
                                   value=content.get('hook', f"{phone_data['name']} - Now Available!"))
            with col2:
                cta = st.text_input("Call to Action:", 
                                  value=content.get('cta', 'SHOP NOW'))
            
            # Generate ad button
            if st.button("✨ Generate Ad", type="primary", use_container_width=True):
                with st.spinner(f"Creating {platform} ad..."):
                    try:
                        # Create ad generator
                        platform_key = platform.lower()
                        generator = SimpleAdGenerator(platform_key)
                        
                        # Generate ad
                        ad_image = generator.generate(
                            phone_data=phone_data,
                            phone_img_url=selected_image_url,
                            hook=hook,
                            cta=cta
                        )
                        
                        # Display ad
                        st.markdown(f"### 🖼️ {platform} Ad Preview")
                        st.image(ad_image, use_container_width=True)
                        
                        # Download button
                        buf = BytesIO()
                        ad_image.save(buf, format='PNG', quality=95)
                        
                        # Create safe filename
                        safe_name = re.sub(r'[^\w\s-]', '', phone_data['name']).strip().replace(' ', '_')
                        filename = f"tripplek_{safe_name}_{platform_key}.png"
                        
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

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 1rem;">
        <h4>Tripple K Communications</h4>
        <p>📞 {TRIPPLEK_PHONE} | 💬 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}</p>
        <p style="font-size: 0.9em; color: #666;">Marketing Suite v3.0 | Powered by GSM Arena API</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()