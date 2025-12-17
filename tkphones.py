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

# Contact info
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# Enhanced icon URLs
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
    "x": "https://ik.imagekit.io/ericmwangi/x.png",
    "instagram": "https://ik.imagekit.io/ericmwangi/instagram.png",
    "tiktok": "https://ik.imagekit.io/ericmwangi/tiktok.png",
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
        transition: all 0.3s;
        border-left: 4px solid {BRAND_MAROON};
        background: #f8f9fa;
    }}
    
    .spec-item:hover {{
        background: rgba(139, 0, 0, 0.05);
        transform: translateX(5px);
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
    
    .image-selector {{
        display: flex;
        gap: 15px;
        margin-top: 20px;
        flex-wrap: wrap;
    }}
    
    .contact-section {{
        display: flex;
        justify-content: center;
        gap: 40px;
        margin-top: 20px;
        flex-wrap: wrap;
    }}
    
    .contact-item {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 20px;
        background: {BRAND_WHITE};
        border-radius: 10px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
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
    
    .metric-card {{
        background: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        border-top: 3px solid {BRAND_GOLD};
    }}
    
    .metric-value {{
        font-size: 2em;
        font-weight: bold;
        color: {BRAND_MAROON};
    }}
    
    .metric-label {{
        color: #666;
        font-size: 0.9em;
        margin-top: 0.3rem;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# UTILITY FUNCTIONS
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

@st.cache_data(ttl=86400)
@retry_on_error(max_retries=2)
def fetch_api_data(url: str) -> Tuple[Optional[dict], Optional[str]]:
    """Fetch data from API with retry logic"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=86400)
@retry_on_error(max_retries=2)
def download_image(url: str) -> Optional[Image.Image]:
    """Download and cache image - SIMPLIFIED VERSION"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Convert to RGB to avoid transparency issues
            if img.mode in ('RGBA', 'LA', 'P'):
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

@st.cache_data(ttl=86400)
def get_icon(icon_name: str, size: int = 40) -> Optional[Image.Image]:
    """Get and cache icon"""
    if icon_name not in ICON_URLS:
        return create_fallback_icon(icon_name, size)
    
    img = download_image(ICON_URLS[icon_name])
    if img:
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        return img
    
    return create_fallback_icon(icon_name, size)

def create_fallback_icon(name: str, size: int) -> Image.Image:
    """Create fallback colored circle icon"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    colors = {
        "processor": "#4CAF50", "battery": "#FF9800", "android": "#3DDC84",
        "camera": "#2196F3", "memory": "#9C27B0", "storage": "#9C27B0",
        "screen": "#2196F3", "call": "#25D366", "whatsapp": "#25D366",
        "facebook": "#1877F2", "x": "#000000", "instagram": "#E4405F",
        "tiktok": "#000000"
    }
    
    color = colors.get(name, BRAND_MAROON)
    draw.ellipse([0, 0, size, size], fill=color)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    
    letter = name[0].upper()
    draw.text((size//2, size//2), letter, fill="white", font=font, anchor="mm")
    
    return img

@st.cache_data(ttl=86400)
def get_logo() -> Optional[Image.Image]:
    """Get Tripple K logo"""
    img = download_image(LOGO_URL)
    return img

def get_phone_images(phone_id: str) -> List[str]:
    """Get all phone images"""
    try:
        url = f"https://tkphsp2.vercel.app/gsm/images/{phone_id}"
        data, error = fetch_api_data(url)
        if data and "images" in data and data["images"]:
            return data["images"]
    except:
        pass
    return []

def remove_background(image: Image.Image) -> Image.Image:
    """Remove background from image using simple color-based approach"""
    try:
        # Simple background removal for white/light backgrounds
        img = image.convert('RGBA')
        data = img.getdata()
        
        new_data = []
        for item in data:
            # If pixel is close to white, make it transparent
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        return img
    except:
        return image

# ==========================================
# ENHANCED SPEC PARSING
# ==========================================

def extract_mp_value(text: str) -> str:
    """Extract MP values robustly"""
    if not text or text == "N/A":
        return "N/A"
    
    numbers = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\s*MP', str(text), re.IGNORECASE)
    
    if numbers:
        valid_mp = []
        for num in numbers:
            try:
                value = float(num)
                if 2 <= value <= 200:
                    mp_str = f"{int(value)}MP" if value == int(value) else f"{value}MP"
                    valid_mp.append(mp_str)
            except:
                continue
        
        if valid_mp:
            return " + ".join(valid_mp[:3])
    
    return "N/A"

def parse_ram_storage(memory_info: List[Dict]) -> Tuple[str, str]:
    """Enhanced RAM/Storage parser"""
    ram = "N/A"
    storage = "N/A"
    
    for mem in memory_info:
        if not isinstance(mem, dict) or mem.get("label") != "internal":
            continue
        
        val = str(mem.get("value", ""))
        
        # RAM patterns
        ram_match = re.search(r'(\d+)\s*GB\s+RAM', val, re.IGNORECASE)
        if ram_match:
            ram = f"{ram_match.group(1)}GB"
        
        # Storage patterns
        storage_match = re.search(r'(\d+)\s*GB\s+(?:ROM|storage)', val, re.IGNORECASE)
        if storage_match:
            storage = f"{storage_match.group(1)}GB"
        
        # Combo patterns
        combo_match = re.search(r'(\d+)\s*GB?\s*/\s*(\d+)\s*GB', val, re.IGNORECASE)
        if combo_match:
            ram = f"{combo_match.group(1)}GB" if ram == "N/A" else ram
            storage = f"{combo_match.group(2)}GB" if storage == "N/A" else storage
        
        # Multiple storage options
        if storage == "N/A" or "/" in val:
            all_storage = re.findall(r'(\d+)\s*(?:GB|TB)', val, re.IGNORECASE)
            if all_storage and len(all_storage) > 1:
                storage_vals = all_storage[1:] if ram != "N/A" else all_storage
                storage = "/".join([f"{s}GB" for s in storage_vals[:3]])
    
    return ram, storage

def parse_screen_specs(display: Dict) -> str:
    """Parse screen specs"""
    size = display.get("size", "")
    resolution = display.get("resolution", "")
    
    inches_match = re.search(r'(\d+\.?\d*)\s*(?:inches|")', str(size), re.IGNORECASE)
    inches = inches_match.group(1) if inches_match else ""
    
    res_match = re.search(r'(\d+)\s*x\s*(\d+)', str(resolution), re.IGNORECASE)
    pixels = f"{res_match.group(1)} x {res_match.group(2)}" if res_match else ""
    
    if inches and pixels:
        return f"{inches} inches, {pixels} pixels"
    elif inches:
        return f"{inches} inches"
    elif pixels:
        return f"{pixels} pixels"
    
    return "N/A"

def parse_phone_specs(raw_data: dict) -> Dict[str, Any]:
    """Enhanced phone spec parser"""
    # Camera
    main_camera_raw = raw_data.get("mainCamera", {}).get("mainModules", "N/A")
    main_camera = extract_mp_value(str(main_camera_raw))
    
    # Screen
    display = raw_data.get("display", {})
    screen = parse_screen_specs(display)
    
    # RAM and Storage
    memory_info = raw_data.get("memory", [])
    ram, storage = parse_ram_storage(memory_info)
    
    # Launch date
    launch_info = raw_data.get("launced", {})
    launch_date = launch_info.get("announced", "") or launch_info.get("status", "")
    
    return {
        "name": raw_data.get("name", "Unknown Phone"),
        "cover": (raw_data.get("image") or raw_data.get("cover", "")).strip(),
        "id": raw_data.get("id", ""),
        "screen": screen,
        "ram": ram,
        "storage": storage,
        "battery": raw_data.get("battery", {}).get("battType", "N/A"),
        "chipset": raw_data.get("platform", {}).get("chipset", "N/A"),
        "main_camera": main_camera,
        "os": raw_data.get("platform", {}).get("os", "N/A"),
        "launch_date": launch_date,
        "raw": raw_data
    }

# ==========================================
# TEXT WRAPPING UTILITIES
# ==========================================

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, xy: Tuple[int, int],
                      font: ImageFont.FreeTypeFont, fill: str, max_width: int,
                      line_spacing: int = 12) -> int:
    """Draw wrapped text and return final y position"""
    x, y = xy
    lines = wrap_text(text, font, max_width)
    
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        bbox = font.getbbox(line)
        y += (bbox[3] - bbox[1]) + line_spacing
    
    return y

# ==========================================
# AD GENERATOR BASE CLASS WITH IMPROVEMENTS
# ==========================================

class AdGenerator:
    """Base class for all ad generators"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.logo = get_logo()
        
        # Load fonts
        try:
            self.title_font = ImageFont.truetype("arialbd.ttf", int(width * 0.04))
            self.subtitle_font = ImageFont.truetype("arialbd.ttf", int(width * 0.028))
            self.body_font = ImageFont.truetype("arial.ttf", int(width * 0.022))
            self.small_font = ImageFont.truetype("arial.ttf", int(width * 0.018))
            self.badge_font = ImageFont.truetype("arialbd.ttf", int(width * 0.025))
        except:
            default = ImageFont.load_default()
            self.title_font = self.subtitle_font = self.body_font = default
            self.small_font = self.badge_font = default
    
    def create_gradient_background(self, color1: str, color2: str) -> Image.Image:
        """Create smooth gradient background"""
        img = Image.new('RGB', (self.width, self.height), color1)
        draw = ImageDraw.Draw(img)
        
        for y in range(self.height):
            factor = y / self.height
            r = int(int(color1[1:3], 16) * (1 - factor) + int(color2[1:3], 16) * factor)
            g = int(int(color1[3:5], 16) * (1 - factor) + int(color2[3:5], 16) * factor)
            b = int(int(color1[5:7], 16) * (1 - factor) + int(color2[5:7], 16) * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def create_geometric_background(self, base_color: str) -> Image.Image:
        """Create modern geometric background"""
        img = Image.new('RGBA', (self.width, self.height), base_color)
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        import random
        random.seed(42)
        
        for _ in range(15):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(50, 200)
            
            shape_type = random.choice(['circle', 'square'])
            color = (*[random.randint(200, 255) for _ in range(3)], 30)
            
            if shape_type == 'circle':
                draw.ellipse([x, y, x+size, y+size], fill=color)
            else:
                draw.rectangle([x, y, x+size, y+size], fill=color)
        
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=20))
        img.paste(overlay, (0, 0), overlay)
        
        return img
    
    def add_logo(self, img: Image.Image, position: str = "top-right") -> Image.Image:
        """Add logo at full size"""
        if not self.logo:
            return img
        
        if position == "top-right":
            x = self.width - self.logo.width - 30
            y = 30
        elif position == "top-left":
            x = 30
            y = 30
        elif position == "center":
            x = (self.width - self.logo.width) // 2
            y = 30
        else:
            x, y = 30, 30
        
        result = img.copy()
        result.paste(self.logo, (x, y), self.logo)
        return result
    
    def draw_badge(self, img: Image.Image, text: str, x: int, y: int,
                   bg_color: str = BRAND_GOLD, text_color: str = BRAND_MAROON) -> Image.Image:
        """Draw badge"""
        draw = ImageDraw.Draw(img)
        
        bbox = self.badge_font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        padding = 15
        badge_width = text_width + padding * 2
        badge_height = text_height + padding
        
        draw.rounded_rectangle(
            [x, y, x + badge_width, y + badge_height],
            radius=10,
            fill=bg_color,
            outline=text_color,
            width=2
        )
        
        text_x = x + padding
        text_y = y + padding // 2
        draw.text((text_x, text_y), text, fill=text_color, font=self.badge_font)
        
        return img
    
    def draw_cta_button(self, img: Image.Image, text: str, x: int, y: int,
                       width: int = 250) -> Image.Image:
        """Draw CTA button"""
        draw = ImageDraw.Draw(img)
        
        height = 70
        
        for i in range(height):
            factor = i / height
            r = int(139 * (1 - factor * 0.3))
            g = int(0 * (1 - factor * 0.3))
            b = int(0 * (1 - factor * 0.3))
            draw.line([(x, y + i), (x + width, y + i)], fill=(r, g, b))
        
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=15,
            outline=BRAND_GOLD,
            width=3
        )
        
        bbox = self.subtitle_font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_x = x + (width - text_width) // 2
        text_y = y + (height - (bbox[3] - bbox[1])) // 2
        
        draw.text((text_x, text_y), text, fill="white", font=self.subtitle_font)
        
        return img
    
    def draw_spec_with_icon(self, img: Image.Image, draw: ImageDraw.ImageDraw,
                           icon_name: str, text: str, x: int, y: int,
                           icon_size: int = 35, max_width: int = 400) -> int:
        """Draw spec with icon - FIXED ALIGNMENT"""
        # Get icon
        icon = get_icon(icon_name, icon_size)
        
        # Calculate positions for proper alignment
        icon_y = y
        text_x = x + icon_size + 20  # Increased spacing for better alignment
        
        # Draw icon centered vertically
        if icon:
            img.paste(icon, (x, icon_y - icon_size // 2), icon)
        
        # Draw text with proper vertical alignment
        try:
            # Get font metrics
            ascent, descent = self.body_font.getmetrics()
            font_height = ascent + descent
            text_y = icon_y - font_height // 2 + ascent
        except:
            text_y = icon_y - 10
        
        # Draw wrapped text
        final_y = draw_wrapped_text(
            draw, text, (text_x, text_y),
            self.body_font, "white", max_width,
            line_spacing=10
        )
        
        # Return the maximum bottom position
        icon_bottom = icon_y + icon_size // 2
        return max(final_y, icon_bottom) + 15
    
    def add_contact_section_separate(self, img: Image.Image, y_pos: int) -> Image.Image:
        """Add contact section with separate WhatsApp and Phone"""
        draw = ImageDraw.Draw(img)
        
        # Contact heading
        draw.text((self.width // 2, y_pos), "Contact Tripple K",
                 fill=BRAND_GOLD, font=self.subtitle_font, anchor="mm")
        
        y_pos += 50
        
        # Phone section - LEFT
        phone_x = self.width // 2 - 200
        
        # WhatsApp section - RIGHT
        whatsapp_x = self.width // 2 + 50
        
        # Phone icon and text
        call_icon = get_icon("call", 35)
        if call_icon:
            img.paste(call_icon, (phone_x, y_pos), call_icon)
        draw.text((phone_x + 45, y_pos + 17), f"Call: {TRIPPLEK_PHONE}",
                 fill="white", font=self.small_font, anchor="lm")
        
        # WhatsApp icon and text
        whatsapp_icon = get_icon("whatsapp", 35)
        if whatsapp_icon:
            img.paste(whatsapp_icon, (whatsapp_x, y_pos), whatsapp_icon)
        draw.text((whatsapp_x + 45, y_pos + 17), f"Chat: {TRIPPLEK_PHONE}",
                 fill="white", font=self.small_font, anchor="lm")
        
        return img
    
    def add_social_icons(self, img: Image.Image, y_pos: int,
                        icons: List[str] = None) -> Image.Image:
        """Add social media icons"""
        if icons is None:
            icons = ["facebook", "x", "instagram", "tiktok"]
        
        icon_size = 40
        spacing = 25
        total_width = len(icons) * (icon_size + spacing) - spacing
        start_x = (self.width - total_width) // 2
        
        for i, icon_name in enumerate(icons):
            icon = get_icon(icon_name, icon_size)
            if icon:
                x = start_x + i * (icon_size + spacing)
                img.paste(icon, (x, y_pos), icon)
        
        return img

# ==========================================
# FACEBOOK AD GENERATOR WITH FIXED ALIGNMENT
# ==========================================

class FacebookAdGenerator(AdGenerator):
    """Facebook ad generator (1200x630)"""
    
    def __init__(self):
        super().__init__(1200, 630)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None, selected_image_url: str = None) -> Image.Image:
        if ad_elements is None:
            ad_elements = {}
        
        # Create geometric background
        img = self.create_geometric_background(BRAND_MAROON)
        img = self.add_logo(img, "top-left")
        draw = ImageDraw.Draw(img)
        
        # Add NEW badge
        self.draw_badge(img, "NEW", self.width - 200, 30)
        
        # Get phone image
        phone_img_url = selected_image_url
        if not phone_img_url and phone_data.get("id"):
            images = get_phone_images(phone_data["id"])
            if images:
                phone_img_url = images[0]
        if not phone_img_url:
            phone_img_url = phone_data.get("cover")
        
        # Add phone image
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                # Remove background and resize
                phone_img = remove_background(phone_img)
                phone_img = phone_img.resize((400, 500), Image.Resampling.LANCZOS)
                x = 70
                y = (self.height - phone_img.height) // 2 + 50
                img.paste(phone_img, (x, y), phone_img)
        
        draw = ImageDraw.Draw(img)
        
        # Content area
        content_x = 550
        content_y = 80
        max_width = self.width - content_x - 50
        
        # Hook
        if ad_elements.get('hook'):
            content_y = draw_wrapped_text(
                draw, ad_elements['hook'], (content_x, content_y),
                self.subtitle_font, BRAND_GOLD, max_width
            ) + 20
        
        # Phone name
        content_y = draw_wrapped_text(
            draw, phone_data.get("name", "New Phone"), (content_x, content_y),
            self.title_font, "white", max_width
        ) + 30
        
        # Specs with icons - FIXED ALIGNMENT
        specs = [
            ("screen", phone_data.get('screen', 'N/A')),
            ("camera", phone_data.get('main_camera', 'N/A')),
            ("memory", phone_data.get('ram', 'N/A')),
            ("storage", phone_data.get('storage', 'N/A')),
            ("battery", phone_data.get('battery', 'N/A')),
        ]
        
        for icon_name, spec_text in specs:
            if spec_text != "N/A":
                content_y = self.draw_spec_with_icon(
                    img, draw, icon_name, spec_text,
                    content_x, content_y, 30, max_width
                )
        
        # CTA button
        cta_text = ad_elements.get('cta', 'SHOP NOW')
        self.draw_cta_button(img, cta_text, content_x, self.height - 130, 280)
        
        # Contact section with separate WhatsApp and Phone
        img = self.add_contact_section_separate(img, self.height - 180)
        
        # Social icons
        self.add_social_icons(img, self.height - 50)
        
        return img

# ==========================================
# WHATSAPP AD GENERATOR WITH IMAGE LEFT, SPECS RIGHT
# ==========================================

class WhatsAppAdGenerator(AdGenerator):
    """WhatsApp ad generator (1080x1080) - Image left, specs right"""
    
    def __init__(self):
        super().__init__(1080, 1080)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None, selected_image_url: str = None) -> Image.Image:
        if ad_elements is None:
            ad_elements = {}
        
        # Clean white background
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Add colored header
        for y in range(150):
            factor = y / 150
            r = int(139 * (1 - factor) + 255 * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, 0, 0))
        
        # Add logo
        if self.logo:
            img.paste(self.logo, (40, 40), self.logo)
        
        draw = ImageDraw.Draw(img)
        
        # Brand name
        draw.text((320, 50), "TRIPPLE K COMMUNICATIONS",
                 fill="white", font=self.title_font)
        draw.text((320, 90), "100% Genuine | Official Warranty",
                 fill=BRAND_GOLD, font=self.small_font)
        
        # Add badges
        self.draw_badge(img, "BEST SELLER", self.width - 220, 50)
        self.draw_badge(img, "OFFER", self.width - 220, 110, bg_color=BRAND_ACCENT)
        
        # Get phone image for left side
        phone_img_url = selected_image_url
        if not phone_img_url and phone_data.get("id"):
            images = get_phone_images(phone_data["id"])
            if images:
                phone_img_url = images[0]
        if not phone_img_url:
            phone_img_url = phone_data.get("cover")
        
        # LEFT COLUMN: Phone Image
        left_col_x = 40
        left_col_y = 180
        
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                # Remove background and resize
                phone_img = remove_background(phone_img)
                phone_img = phone_img.resize((400, 500), Image.Resampling.LANCZOS)
                img.paste(phone_img, (left_col_x, left_col_y), phone_img)
        
        # RIGHT COLUMN: Specs
        right_col_x = 500
        right_col_y = 180
        
        # Phone name
        right_col_y = draw_wrapped_text(
            draw, phone_data.get("name", ""), (right_col_x, right_col_y),
            self.title_font, BRAND_MAROON, self.width - right_col_x - 40, line_spacing=10
        ) + 30
        
        # Specs with icons
        specs = [
            ("screen", phone_data.get('screen', 'N/A')),
            ("camera", phone_data.get('main_camera', 'N/A')),
            ("memory", phone_data.get('ram', 'N/A')),
            ("storage", phone_data.get('storage', 'N/A')),
            ("battery", phone_data.get('battery', 'N/A')),
        ]
        
        for icon_name, spec_text in specs:
            if spec_text != "N/A":
                right_col_y = self.draw_spec_with_icon(
                    img, draw, icon_name, spec_text,
                    right_col_x, right_col_y, 30, 350
                )
                # Change text color for right column
                draw = ImageDraw.Draw(img)  # Refresh draw object
        
        # CTA button
        cta_text = ad_elements.get('cta', 'ORDER NOW')
        self.draw_cta_button(img, cta_text, (self.width - 300) // 2, max(right_col_y, 700), 300)
        
        # Contact section with separate WhatsApp and Phone
        img = self.add_contact_section_separate(img, self.height - 180)
        
        # Social icons
        img = self.add_social_icons(img, self.height - 80)
        
        return img

# ==========================================
# INSTAGRAM AD GENERATOR
# ==========================================

class InstagramAdGenerator(AdGenerator):
    """Instagram ad generator (1080x1350)"""
    
    def __init__(self):
        super().__init__(1080, 1350)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None, selected_image_url: str = None) -> Image.Image:
        if ad_elements is None:
            ad_elements = {}
        
        # Modern gradient background
        img = self.create_gradient_background("#0c2461", "#1e3799")
        img = self.add_logo(img, "top-right")
        
        # Add DISCOUNT badge
        self.draw_badge(img, "DISCOUNT", 40, 40, bg_color=BRAND_ACCENT)
        
        draw = ImageDraw.Draw(img)
        
        # Get phone image
        content_y = 220
        phone_img_url = selected_image_url
        if not phone_img_url and phone_data.get("id"):
            images = get_phone_images(phone_data["id"])
            if images:
                phone_img_url = images[0]
        if not phone_img_url:
            phone_img_url = phone_data.get("cover")
        
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                # Remove background
                phone_img = remove_background(phone_img)
                phone_img = phone_img.resize((550, 550), Image.Resampling.LANCZOS)
                
                # Create shadow
                shadow = Image.new('RGBA', (phone_img.width + 20, phone_img.height + 20), (0,0,0,80))
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
                
                x = (self.width - phone_img.width) // 2
                img.paste(shadow, (x - 10, content_y + 20), shadow)
                img.paste(phone_img, (x, content_y), phone_img)
                content_y += phone_img.height + 50
        
        draw = ImageDraw.Draw(img)
        
        # Hook
        if ad_elements.get('hook'):
            content_y = draw_wrapped_text(
                draw, ad_elements['hook'], (self.width // 2, content_y),
                self.subtitle_font, BRAND_GOLD, self.width - 100
            ) + 20
        
        # Phone name
        content_y = draw_wrapped_text(
            draw, phone_data.get("name", ""), (self.width // 2, content_y),
            self.title_font, "white", self.width - 100
        ) + 40
        
        # Featured specs
        featured_specs = [
            ("camera", phone_data.get('main_camera', 'N/A').split('+')[0]),
            ("processor", phone_data.get('chipset', 'N/A')[:15] + "..."),
            ("memory", phone_data.get('ram', 'N/A')),
            ("battery", phone_data.get('battery', 'N/A')),
        ]
        
        featured_specs = [(icon, text) for icon, text in featured_specs if text != "N/A"]
        
        if featured_specs:
            num_specs = len(featured_specs)
            spec_spacing = self.width // (num_specs + 1)
            
            for i, (icon_name, spec_text) in enumerate(featured_specs):
                x_pos = spec_spacing * (i + 1)
                
                icon = get_icon(icon_name, 60)
                if icon:
                    img.paste(icon, (x_pos - 30, content_y - 30), icon)
                
                lines = wrap_text(spec_text, self.small_font, 100)
                text_y = content_y + 40
                for line in lines:
                    draw.text((x_pos, text_y), line, fill="white", font=self.small_font, anchor="mm")
                    text_y += 20
            
            content_y += 120
        
        # CTA button
        cta_text = ad_elements.get('cta', 'BUY NOW')
        self.draw_cta_button(img, cta_text, (self.width - 350) // 2, content_y, 350)
        
        # Contact section with separate WhatsApp and Phone
        img = self.add_contact_section_separate(img, self.height - 200)
        
        # Social icons
        img = self.add_social_icons(img, self.height - 120)
        
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
    
    def get_wait_time(self) -> float:
        if not self.calls or len(self.calls) < RATE_LIMIT_CALLS:
            return 0
        oldest = min(self.calls)
        return max(0, RATE_LIMIT_WINDOW - (time.time() - oldest))

rate_limiter = RateLimiter()

def generate_marketing_content(phone_data: dict, persona: str, tone: str) -> Optional[Dict[str, str]]:
    """Generate marketing content"""
    if not client:
        return None
    
    if not rate_limiter.can_make_call():
        wait_time = rate_limiter.get_wait_time()
        st.error(f"⏳ Rate limit: Wait {int(wait_time)}s before next request")
        return None
    
    try:
        prompt = f"""Create marketing content for {phone_data['name']} targeting {persona} with {tone} tone.

Phone Specs:
- Screen: {phone_data.get('screen', 'N/A')}
- Camera: {phone_data.get('main_camera', 'N/A')}
- RAM: {phone_data.get('ram', 'N/A')}
- Storage: {phone_data.get('storage', 'N/A')}
- Battery: {phone_data.get('battery', 'N/A')}

Business: Tripple K Communications Kenya
Contact: {TRIPPLEK_PHONE}
Website: {TRIPPLEK_URL}

Generate:
Hook: [Catchy headline, max 10 words]
CTA: [Clear action, max 5 words]
Urgency: [Limited offer message]
TikTok: [80-100 chars, engaging]
WhatsApp: [2-3 lines, easy to forward]
Facebook: [3-4 sentences with benefits]
Instagram: [2-3 stylish lines]
Hashtags: [7-10 relevant hashtags]"""
        
        rate_limiter.record_call()
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=800,
            timeout=25
        )
        
        text = response.choices[0].message.content.strip()
        return parse_marketing_response(text)
        
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Access denied" in error_msg:
            st.error("🚫 API Access Denied")
        elif "429" in error_msg:
            st.error("⏱️ Rate limit exceeded")
        else:
            st.error(f"❌ Error: {error_msg}")
        return None

def parse_marketing_response(text: str) -> Dict[str, str]:
    """Parse AI response"""
    content = {
        "hook": "", "cta": "", "urgency": "",
        "tiktok": "", "whatsapp": "", "facebook": "",
        "instagram": "", "hashtags": ""
    }
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        for key in content.keys():
            pattern = f"{key}:"
            if pattern.lower() in line.lower():
                content[key] = line.split(':', 1)[1].strip()
                break
    
    return content

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
    if "marketing_content" not in st.session_state:
        st.session_state.marketing_content = None
    if "generated_ads" not in st.session_state:
        st.session_state.generated_ads = {}
    
    # Tabs
    tabs = st.tabs(["🔍 Find Phone", "📱 Create Campaign", "🎨 Generate Ads"])
    
    # TAB 1: FIND PHONE
    with tabs[0]:
        st.subheader("Search Phone Specifications")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Phone name:", placeholder="e.g., Samsung Galaxy S23")
        with col2:
            search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_btn and query:
            with st.spinner("Searching..."):
                url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(query)}"
                results, error = fetch_api_data(url)
                
                if error or not results:
                    st.error("No results found")
                elif results:
                    st.success(f"✅ Found {len(results)} phones")
                    
                    names = [r.get("name", "Unknown") for r in results]
                    selected = st.selectbox("Select phone:", names)
                    
                    if selected:
                        phone_raw = next(r for r in results if r.get("name") == selected)
                        
                        # Get details
                        details_url = f"https://tkphsp2.vercel.app/gsm/info/{phone_raw.get('id')}"
                        details, _ = fetch_api_data(details_url)
                        
                        if details:
                            phone_data = parse_phone_specs(details)
                            st.session_state.current_phone = phone_data
                            
                            # Get all phone images
                            images = get_phone_images(phone_data["id"])
                            st.session_state.phone_images = images
                            
                            # Display in two columns
                            col_img, col_specs = st.columns([1, 1])
                            
                            with col_img:
                                if images:
                                    st.markdown("### Phone Image")
                                    # Let Streamlit handle the image display
                                    st.image(images[0], use_container_width=True, caption=phone_data['name'])
                            with col_specs:
                                st.markdown('<div class="specs-container">', unsafe_allow_html=True)
                                st.markdown(f"### {phone_data['name']}")
                                
                                # Display each spec on its own line
                                spec_items = [
                                    ("🖥️ Screen", phone_data['screen']),
                                    ("📸 Camera", phone_data['main_camera']),
                                    ("⚡ RAM", phone_data['ram']),
                                    ("💾 Storage", phone_data['storage']),
                                    ("🔋 Battery", phone_data['battery']),
                                    ("🚀 Chipset", phone_data['chipset']),
                                    ("🪟 OS", phone_data['os']),
                                    ("📅 Launch Date", phone_data['launch_date']),
                                ]
                                
                                for icon, (label, value) in enumerate(spec_items):
                                    if value != "N/A":
                                        st.markdown(f'''
                                        <div class="spec-item">
                                            <div class="spec-label">{label}</div>
                                            <div class="spec-value">{value}</div>
                                        </div>
                                        ''', unsafe_allow_html=True)
                                
                                st.markdown('</div>', unsafe_allow_html=True)
    
    # TAB 2: CREATE CAMPAIGN
    with tabs[1]:
        st.subheader("Create Marketing Campaign")
        
        if not st.session_state.current_phone:
            st.info("👈 Select a phone first")
        elif not client:
            st.warning("⚠️ Groq API not configured")
        else:
            phone_data = st.session_state.current_phone
            
            col1, col2 = st.columns(2)
            with col1:
                persona = st.selectbox("Target Audience", 
                    ["General Consumers", "Tech Enthusiasts", "Students", "Professionals"])
            with col2:
                tone = st.selectbox("Brand Tone",
                    ["Professional", "Friendly", "Excited", "Urgent"])
            
            if st.button("🚀 Generate Campaign", type="primary", use_container_width=True):
                with st.spinner("Creating content..."):
                    content = generate_marketing_content(phone_data, persona, tone)
                    
                    if content:
                        st.session_state.marketing_content = content
                        st.balloons()
                        st.success("✅ Campaign generated!")
                        
                        # Display content
                        st.markdown("### 🎯 Ad Elements")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if content.get("hook"):
                                st.info(f"**Hook:** {content['hook']}")
                        with col2:
                            if content.get("cta"):
                                st.success(f"**CTA:** {content['cta']}")
                        with col3:
                            if content.get("urgency"):
                                st.warning(f"**Urgency:** {content['urgency']}")
                        
                        st.markdown("### 📱 Social Posts")
                        for platform in ["TikTok", "WhatsApp", "Facebook", "Instagram"]:
                            key = platform.lower()
                            if content.get(key):
                                with st.expander(f"📌 {platform}"):
                                    st.text(content[key])
                        
                        if content.get("hashtags"):
                            st.markdown("### 🏷️ Hashtags")
                            st.code(content["hashtags"])
    
    # TAB 3: GENERATE ADS
    with tabs[2]:
        st.subheader("Generate Marketing Ads")
        
        if not st.session_state.current_phone:
            st.info("👈 Select a phone first")
        else:
            phone_data = st.session_state.current_phone
            
            # Get selected image
            selected_image_url = None
            if st.session_state.phone_images and st.session_state.selected_image_index < len(st.session_state.phone_images):
                selected_image_url = st.session_state.phone_images[st.session_state.selected_image_index]
            
            st.info(f"Using first available image")
            
            ad_types = st.multiselect("Select ad formats:",
                ["Facebook Ad (1200x630)", "WhatsApp Ad (1080x1080)", "Instagram Ad (1080x1350)"],
                default=["Facebook Ad (1200x630)"])
            
            if st.button("✨ Generate Ads", type="primary", use_container_width=True):
                generated = {}
                
                with st.spinner("Creating ads..."):
                    for ad_type in ad_types:
                        try:
                            if "Facebook" in ad_type:
                                gen = FacebookAdGenerator()
                                ad_img = gen.generate(phone_data, st.session_state.marketing_content or {}, selected_image_url)
                            elif "WhatsApp" in ad_type:
                                gen = WhatsAppAdGenerator()
                                ad_img = gen.generate(phone_data, st.session_state.marketing_content or {}, selected_image_url)
                            elif "Instagram" in ad_type:
                                gen = InstagramAdGenerator()
                                ad_img = gen.generate(phone_data, st.session_state.marketing_content or {}, selected_image_url)
                            else:
                                continue
                            
                            buf = BytesIO()
                            ad_img.save(buf, format='PNG', quality=95)
                            generated[ad_type] = buf.getvalue()
                            
                        except Exception as e:
                            st.error(f"Failed to create {ad_type}: {e}")
                    
                    st.session_state.generated_ads = generated
                    st.success(f"✅ Generated {len(generated)} ad(s)!")
            
            # Display generated ads
            if st.session_state.generated_ads:
                st.markdown("---")
                st.subheader("📱 Generated Ads")
                
                for ad_type, img_bytes in st.session_state.generated_ads.items():
                    with st.expander(f"{ad_type}", expanded=True):
                        if "Instagram" in ad_type:
                            st.image(img_bytes, width=400)
                        else:
                            st.image(img_bytes, use_container_width=True)
                        
                        filename = f"tripplek_{ad_type.split()[0].lower()}_ad.png"
                        st.download_button(
                            f"📥 Download {ad_type.split()[0]} Ad",
                            img_bytes,
                            filename,
                            "image/png",
                            key=f"dl_{ad_type}"
                        )
    
    # Footer with separate contact info
    st.divider()
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 1rem;">
        <h3>Tripple K Communications</h3>
        <div class="contact-section">
            <div class="contact-item">
                <img src="{ICON_URLS['call']}" width="24" height="24">
                <span><strong>Call:</strong> {TRIPPLEK_PHONE}</span>
            </div>
            <div class="contact-item">
                <img src="{ICON_URLS['whatsapp']}" width="24" height="24">
                <span><strong>WhatsApp:</strong> {TRIPPLEK_PHONE}</span>
            </div>
            <div class="contact-item">
                <span><strong>Website:</strong> {TRIPPLEK_URL}</span>
            </div>
        </div>
        <p style="font-size: 0.9em; color: #666; margin-top: 1rem;">Professional Phone Marketing Suite v4.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()