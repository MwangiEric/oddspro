import streamlit as st
import requests
import re
from dateutil import parser
from datetime import datetime, timedelta
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import Optional, Tuple, Dict, Any, List
import time
import random

# ----------------------------
# CONFIGURATION
# ----------------------------
GROQ_KEY = st.secrets.get("groq_key", "")
if GROQ_KEY:
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    MODEL = "llama-3.3-70b-versatile"
else:
    client = None

BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
BRAND_ACCENT = "#FF6B35"
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# Rate limiting
RATE_LIMIT_CALLS = 5  # Max API calls per minute
RATE_LIMIT_WINDOW = 60  # Seconds

st.set_page_config(page_title="Tripple K Phone Specs & Ads", layout="centered")

# CSS Styling
st.markdown(f"""
<style>
    .specs-box {{
        border: 2px solid {BRAND_MAROON};
        border-radius: 10px;
        padding: 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        font-family: 'Courier New', monospace;
        font-size: 15px;
        line-height: 1.8;
        margin: 15px 0;
        white-space: pre-wrap;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .phone-title {{
        color: {BRAND_MAROON};
        margin-bottom: 10px;
        font-size: 1.8em;
        font-weight: bold;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }}
    .post-box {{
        border: 2px solid {BRAND_MAROON};
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        background: white;
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }}
    .post-box:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }}
    .post-platform {{
        color: {BRAND_MAROON};
        font-weight: bold;
        font-size: 1.3em;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 3px solid {BRAND_GOLD};
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .element-box {{
        border-left: 4px solid {BRAND_ACCENT};
        padding: 15px;
        margin: 10px 0;
        background: linear-gradient(135deg, #fff8e1 0%, #ffe082 100%);
        border-radius: 8px;
    }}
    .stButton>button {{
        background: linear-gradient(135deg, {BRAND_MAROON} 0%, #9a0000 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }}
    .stButton>button:hover {{
        background: linear-gradient(135deg, #9a0000 0%, {BRAND_MAROON} 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }}
    .tab-content {{
        padding: 25px 0;
    }}
    .ad-preview {{
        border: 3px solid {BRAND_MAROON};
        border-radius: 15px;
        padding: 15px;
        background: white;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        margin: 20px 0;
    }}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# RATE LIMITING
# ----------------------------
class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self):
        self.calls = []
    
    def can_make_call(self) -> bool:
        """Check if we can make an API call"""
        now = time.time()
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < RATE_LIMIT_WINDOW]
        return len(self.calls) < RATE_LIMIT_CALLS
    
    def record_call(self):
        """Record an API call"""
        self.calls.append(time.time())
    
    def get_wait_time(self) -> float:
        """Get time to wait before next call"""
        if not self.calls or len(self.calls) < RATE_LIMIT_CALLS:
            return 0
        oldest_call = min(self.calls)
        return max(0, RATE_LIMIT_WINDOW - (time.time() - oldest_call))

rate_limiter = RateLimiter()

# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------
@st.cache_data(ttl=3600)
def fetch_api_data(url: str) -> Tuple[Optional[dict], Optional[str]]:
    """Fetch data from API with caching"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=86400)
def download_image(url: str) -> Optional[Image.Image]:
    """Download and cache image"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            return img.convert('RGBA')
    except:
        return None
    return None

@st.cache_data(ttl=86400)
def get_logo() -> Optional[Image.Image]:
    """Get Tripple K logo"""
    return download_image(LOGO_URL)

@st.cache_data(ttl=86400)
def get_phone_images(phone_id: str) -> List[str]:
    """Get multiple phone images from API"""
    try:
        url = f"https://tkphsp2.vercel.app/gsm/images/{phone_id}"
        data, error = fetch_api_data(url)
        if data and "images" in data:
            return data["images"][:5]  # Return max 5 images
    except:
        pass
    return []

def extract_mp_value(text: str) -> str:
    """Extract MP values and add 'MP' suffix"""
    if not text or text == "N/A":
        return "N/A"
    
    # Find all numbers that are likely MP values
    numbers = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\b', str(text))
    
    if numbers:
        valid_numbers = []
        for num in numbers:
            try:
                value = float(num)
                if 2 <= value <= 200:  # Reasonable MP range
                    valid_numbers.append(f"{int(value) if value.is_integer() else value}MP")
            except:
                continue
        
        if valid_numbers:
            return " + ".join(valid_numbers[:3])
    
    return "N/A"

def parse_phone_specs(raw_data: dict) -> Dict[str, Any]:
    """Parse and format phone specifications"""
    # Camera specs with MP suffix
    main_camera_raw = raw_data.get("mainCamera", {}).get("mainModules", "N/A")
    main_camera = extract_mp_value(str(main_camera_raw))
    
    # Screen specs
    display = raw_data.get("display", {})
    screen_size = display.get("size", "N/A")
    resolution = display.get("resolution", "N/A")
    
    if screen_size != "N/A" and resolution != "N/A":
        screen = f"{screen_size}, {resolution}"
    else:
        screen = screen_size if screen_size != "N/A" else resolution
    
    # RAM and Storage
    ram = storage = "N/A"
    memory_info = raw_data.get("memory", [])
    
    for mem in memory_info:
        if isinstance(mem, dict):
            if mem.get("label") == "internal":
                val = str(mem.get("value", ""))
                
                # Extract RAM
                ram_match = re.search(r'(\d+\s*(?:GB|TB))\s+RAM', val, re.IGNORECASE)
                if ram_match:
                    ram = ram_match.group(1)
                
                # Extract storage
                if "storage" in val.lower() or "rom" in val.lower():
                    storage_match = re.search(r'(\d+\s*(?:GB|TB))', val)
                    if storage_match:
                        storage = storage_match.group(1)
                elif "gb" in val.lower() or "tb" in val.lower():
                    storage_matches = re.findall(r'(\d+\s*(?:GB|TB))', val, re.IGNORECASE)
                    if storage_matches:
                        storage_list = []
                        for i, match in enumerate(storage_matches):
                            if ram != "N/A" and i == 0:
                                continue
                            storage_list.append(match)
                        if storage_list:
                            storage = " + ".join(storage_list[:2])
    
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

def format_specs_for_display(phone_data: dict) -> str:
    """Format specs for clean display"""
    specs = [
        f"📱 Phone: {phone_data.get('name', 'N/A')}",
        f"🖥️ Screen: {phone_data.get('screen', 'N/A')}",
        f"📸 Main Camera: {phone_data.get('main_camera', 'N/A')}",
        f"⚡ RAM: {phone_data.get('ram', 'N/A')}",
        f"💾 Storage: {phone_data.get('storage', 'N/A')}",
        f"🔋 Battery: {phone_data.get('battery', 'N/A')}",
        f"🚀 Chipset: {phone_data.get('chipset', 'N/A')}",
        f"🪟 OS: {phone_data.get('os', 'N/A')}"
    ]
    return "\n".join(specs)

def get_market_info(launch_date: str) -> Tuple[str, str]:
    """Get launch date and time passed"""
    if not launch_date:
        return "Launch date: Unknown", ""
    
    date_text = str(launch_date).strip()
    
    if "Released" in date_text:
        date_text = date_text.replace("Released", "").strip()
    
    try:
        parsed_date = parser.parse(date_text, fuzzy=True)
        formatted_date = parsed_date.strftime("%B %d, %Y")
        
        today = datetime.now()
        time_passed = today - parsed_date
        days = time_passed.days
        
        if days < 0:
            time_info = f"Releases in {-days} days"
        elif days == 0:
            time_info = "Released today"
        elif days < 7:
            time_info = f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            time_info = f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif days < 365:
            months = days // 30
            time_info = f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = days // 365
            months = (days % 365) // 30
            if months > 0:
                time_info = f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''} ago"
            else:
                time_info = f"{years} year{'s' if years > 1 else ''} ago"
        
        return f"Launch date: {formatted_date}", time_info
        
    except:
        return f"Launch info: {date_text}", ""

# ----------------------------
# ENHANCED AD GENERATORS
# ----------------------------
class EnhancedAdGenerator:
    """Enhanced base class for ad generators with better visuals"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.logo = get_logo()
        
        # Load better fonts
        try:
            self.title_font = ImageFont.truetype("arialbd.ttf", int(width * 0.035))
            self.subtitle_font = ImageFont.truetype("arialbd.ttf", int(width * 0.025))
            self.body_font = ImageFont.truetype("arial.ttf", int(width * 0.02))
            self.small_font = ImageFont.truetype("arial.ttf", int(width * 0.018))
        except:
            self.title_font = ImageFont.load_default()
            self.subtitle_font = ImageFont.load_default()
            self.body_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
    
    def create_gradient_background(self, color1: str = BRAND_MAROON, color2: str = "#4a0000") -> Image.Image:
        """Create gradient background"""
        img = Image.new('RGB', (self.width, self.height), color1)
        draw = ImageDraw.Draw(img)
        
        # Create gradient effect
        for y in range(self.height):
            factor = y / self.height
            r = int(int(color1[1:3], 16) * (1 - factor) + int(color2[1:3], 16) * factor)
            g = int(int(color1[3:5], 16) * (1 - factor) + int(color2[3:5], 16) * factor)
            b = int(int(color1[5:7], 16) * (1 - factor) + int(color2[5:7], 16) * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def add_logo(self, img: Image.Image, position: str = "top-right") -> Image.Image:
        """Add Tripple K logo to image"""
        if self.logo:
            logo_size = min(self.width // 6, 200)
            self.logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            if position == "top-right":
                x = self.width - self.logo.width - 40
                y = 40
            elif position == "top-left":
                x = 40
                y = 40
            elif position == "center":
                x = (self.width - self.logo.width) // 2
                y = 40
            
            result = img.copy()
            result.paste(self.logo, (x, y), self.logo)
            return result
        return img
    
    def add_phone_images(self, base_img: Image.Image, image_urls: List[str], layout: str = "left") -> Image.Image:
        """Add phone images with proper scaling and layout"""
        if not image_urls:
            return base_img
        
        # Download and process images
        phone_images = []
        for url in image_urls[:3]:  # Use max 3 images
            img = download_image(url)
            if img:
                # Resize to fit
                max_width = int(self.width * 0.35)
                max_height = int(self.height * 0.6)
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                phone_images.append(img)
        
        if not phone_images:
            return base_img
        
        result = base_img.copy()
        draw = ImageDraw.Draw(result)
        
        if layout == "left":
            # Stack images vertically on left
            total_height = sum(img.height for img in phone_images) + (len(phone_images) - 1) * 20
            start_y = (self.height - total_height) // 2
            x = 60
            
            for img in phone_images:
                result.paste(img, (x, start_y), img)
                # Add subtle shadow
                draw.rectangle([(x-5, start_y-5), (x+img.width+5, start_y+img.height+5)], 
                             fill=(0,0,0,100))
                start_y += img.height + 20
        
        elif layout == "center":
            # Display main image in center
            main_img = phone_images[0]
            x = (self.width - main_img.width) // 2
            y = (self.height - main_img.height) // 3
            result.paste(main_img, (x, y), main_img)
            
            # Add small thumbnails at bottom
            if len(phone_images) > 1:
                thumbnail_y = y + main_img.height + 30
                thumbnail_spacing = (self.width - sum(img.width for img in phone_images[1:])) // (len(phone_images[1:]) + 1)
                
                for i, img in enumerate(phone_images[1:]):
                    thumb_x = thumbnail_spacing * (i + 1) + sum(p.width for p in phone_images[1:i+1])
                    img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    result.paste(img, (thumb_x, thumbnail_y), img)
        
        return result
    
    def add_text_with_outline(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int, 
                            font: ImageFont.ImageFont, fill: str, outline: str = "black", 
                            outline_width: int = 2, anchor: str = "lt"):
        """Add text with outline for better visibility"""
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor=anchor)
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill, anchor=anchor)
    
    def add_rounded_rectangle(self, draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, 
                            fill: str, radius: int = 20, outline: str = None, outline_width: int = 3):
        """Draw rounded rectangle"""
        # Draw rounded corners
        draw.ellipse([x1, y1, x1 + radius*2, y1 + radius*2], fill=fill)
        draw.ellipse([x2 - radius*2, y1, x2, y1 + radius*2], fill=fill)
        draw.ellipse([x1, y2 - radius*2, x1 + radius*2, y2], fill=fill)
        draw.ellipse([x2 - radius*2, y2 - radius*2, x2, y2], fill=fill)
        
        # Draw rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        
        # Add outline if specified
        if outline:
            for i in range(outline_width):
                draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=outline, width=1)

class FacebookAdGenerator(EnhancedAdGenerator):
    """Enhanced Facebook ad generator (1200x630)"""
    
    def __init__(self):
        super().__init__(1200, 630)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        """Generate Facebook ad with marketing elements"""
        if ad_elements is None:
            ad_elements = {}
        
        # Create gradient background
        img = self.create_gradient_background(BRAND_MAROON, "#5a0000")
        draw = ImageDraw.Draw(img)
        
        # Add logo
        img = self.add_logo(img, "top-left")
        
        # Get phone images
        phone_images = []
        if phone_data.get("id"):
            phone_images = get_phone_images(phone_data["id"])
        if not phone_images and phone_data.get("cover"):
            phone_images = [phone_data["cover"]]
        
        # Add phone images
        img = self.add_phone_images(img, phone_images, "left")
        draw = ImageDraw.Draw(img)
        
        # Content area
        content_x = int(self.width * 0.55)
        content_y = 80
        
        # Add hook/banner
        if ad_elements.get('hook'):
            self.add_text_with_outline(draw, ad_elements['hook'], content_x, content_y, 
                                     self.subtitle_font, BRAND_GOLD, anchor="lt")
            content_y += 60
        
        # Add phone name
        phone_name = phone_data.get("name", "New Phone")
        self.add_text_with_outline(draw, phone_name, content_x, content_y, 
                                 self.title_font, "white", anchor="lt")
        content_y += 80
        
        # Add key specs in rounded boxes
        specs = [
            f"📱 {phone_data.get('screen', 'N/A')}",
            f"📸 {phone_data.get('main_camera', 'N/A')}",
            f"⚡ {phone_data.get('ram', 'N/A')} RAM",
            f"💾 {phone_data.get('storage', 'N/A')} Storage",
            f"🔋 {phone_data.get('battery', 'N/A')}",
            f"🚀 {phone_data.get('os', 'N/A')}"
        ]
        
        for spec in specs:
            box_height = 50
            self.add_rounded_rectangle(draw, content_x, content_y, 
                                     content_x + 400, content_y + box_height,
                                     fill=(255, 255, 255, 180), radius=15,
                                     outline=BRAND_GOLD)
            
            draw.text((content_x + 20, content_y + box_height//2), spec, 
                     fill=BRAND_MAROON, font=self.body_font, anchor="lm")
            content_y += box_height + 15
        
        # Add CTA button
        if ad_elements.get('cta'):
            content_y += 20
            cta_text = ad_elements['cta']
            cta_width = draw.textlength(cta_text, font=self.subtitle_font) + 40
            cta_height = 60
            
            self.add_rounded_rectangle(draw, content_x, content_y, 
                                     content_x + cta_width, content_y + cta_height,
                                     fill=BRAND_GOLD, radius=25, outline=BRAND_MAROON)
            
            draw.text((content_x + cta_width//2, content_y + cta_height//2), cta_text,
                     fill=BRAND_MAROON, font=self.subtitle_font, anchor="mm")
            content_y += cta_height + 30
        
        # Add urgency
        if ad_elements.get('urgency'):
            content_y += 10
            draw.text((content_x, content_y), f"🔥 {ad_elements['urgency']}", 
                     fill="#FF6B6B", font=self.body_font, anchor="lt")
            content_y += 50
        
        # Add contact info
        contact_y = self.height - 80
        draw.text((self.width//2, contact_y), f"📞 Call/WhatsApp: {TRIPPLEK_PHONE}", 
                 fill="white", font=self.body_font, anchor="mm")
        draw.text((self.width//2, contact_y + 40), f"🌐 Visit: {TRIPPLEK_URL}", 
                 fill=BRAND_GOLD, font=self.small_font, anchor="mm")
        
        return img

class WhatsAppAdGenerator(EnhancedAdGenerator):
    """Enhanced WhatsApp ad generator (1080x1080) - Square format"""
    
    def __init__(self):
        super().__init__(1080, 1080)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        """Generate WhatsApp ad"""
        if ad_elements is None:
            ad_elements = {}
        
        # Create clean white background with subtle pattern
        img = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add header with gradient
        header_height = 120
        for y in range(header_height):
            factor = y / header_height
            r = int(139 * (1 - factor) + 255 * factor)
            g = int(0 * (1 - factor) + 255 * factor)
            b = int(0 * (1 - factor) + 255 * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        # Add logo and brand name
        if self.logo:
            self.logo.thumbnail((80, 80), Image.Resampling.LANCZOS)
            img.paste(self.logo, (50, 20), self.logo)
        
        draw.text((150, 30), "TRIPPLE K COMMUNICATIONS", 
                 fill="white", font=self.title_font)
        draw.text((150, 80), "100% Genuine | Official Warranty", 
                 fill=BRAND_GOLD, font=self.small_font)
        
        # Get phone images
        phone_images = []
        if phone_data.get("id"):
            phone_images = get_phone_images(phone_data["id"])
        if not phone_images and phone_data.get("cover"):
            phone_images = [phone_data["cover"]]
        
        # Add main phone image
        if phone_images:
            main_img = download_image(phone_images[0])
            if main_img:
                main_img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                x = (self.width - main_img.width) // 2
                y = 150
                img.paste(main_img, (x, y), main_img)
                draw = ImageDraw.Draw(img)
        
        # Content area
        content_y = 150 + (500 if phone_images else 0)
        
        # Add hook
        if ad_elements.get('hook'):
            self.add_text_with_outline(draw, ad_elements['hook'], self.width//2, content_y,
                                     self.subtitle_font, BRAND_MAROON, anchor="mm")
            content_y += 60
        
        # Add phone name
        phone_name = phone_data.get("name", "")
        self.add_text_with_outline(draw, phone_name, self.width//2, content_y,
                                 self.title_font, BRAND_MAROON, anchor="mm")
        content_y += 80
        
        # Add specs in two columns
        col1_x = self.width // 4
        col2_x = 3 * self.width // 4
        
        specs = [
            (col1_x, f"📱 {phone_data.get('screen', 'N/A')}"),
            (col1_x, f"📸 {phone_data.get('main_camera', 'N/A')}"),
            (col1_x, f"⚡ {phone_data.get('ram', 'N/A')}"),
            (col2_x, f"💾 {phone_data.get('storage', 'N/A')}"),
            (col2_x, f"🔋 {phone_data.get('battery', 'N/A')}"),
            (col2_x, f"🚀 {phone_data.get('os', 'N/A')}")
        ]
        
        for x_pos, spec in specs:
            draw.text((x_pos, content_y), spec, fill="#333", font=self.body_font, anchor="mm")
            content_y += 40
        
        # Add CTA
        if ad_elements.get('cta'):
            content_y += 40
            cta_box_y = content_y
            cta_box_height = 70
            cta_box_width = self.width - 200
            
            self.add_rounded_rectangle(draw, (self.width - cta_box_width)//2, cta_box_y,
                                     (self.width + cta_box_width)//2, cta_box_y + cta_box_height,
                                     fill=BRAND_MAROON, radius=20, outline=BRAND_GOLD)
            
            draw.text((self.width//2, cta_box_y + cta_box_height//2), ad_elements['cta'],
                     fill="white", font=self.subtitle_font, anchor="mm")
            content_y += cta_box_height + 30
        
        # Add contact info
        contact_y = self.height - 100
        draw.text((self.width//2, contact_y), f"📱 Call/WhatsApp: {TRIPPLEK_PHONE}", 
                 fill=BRAND_MAROON, font=self.body_font, anchor="mm")
        draw.text((self.width//2, contact_y + 40), f"🌐 {TRIPPLEK_URL}", 
                 fill="#666", font=self.small_font, anchor="mm")
        
        return img

class InstagramAdGenerator(EnhancedAdGenerator):
    """Instagram ad generator (1080x1350) - Instagram post format"""
    
    def __init__(self):
        super().__init__(1080, 1350)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        """Generate Instagram ad"""
        if ad_elements is None:
            ad_elements = {}
        
        # Create modern gradient background
        img = self.create_gradient_background("#0c2461", "#1e3799")
        draw = ImageDraw.Draw(img)
        
        # Add logo
        img = self.add_logo(img, "top-right")
        
        # Get phone images
        phone_images = []
        if phone_data.get("id"):
            phone_images = get_phone_images(phone_data["id"])
        if not phone_images and phone_data.get("cover"):
            phone_images = [phone_data["cover"]]
        
        # Add phone images in creative layout
        if phone_images:
            main_img = download_image(phone_images[0])
            if main_img:
                # Create floating phone effect
                main_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                x = (self.width - main_img.width) // 2
                y = 200
                
                # Add shadow
                shadow = Image.new('RGBA', (main_img.width + 20, main_img.height + 20), (0,0,0,100))
                img.paste(shadow, (x-10, y+20), shadow)
                
                # Add phone
                img.paste(main_img, (x, y), main_img)
                draw = ImageDraw.Draw(img)
        
        # Add hook at top
        if ad_elements.get('hook'):
            draw.text((self.width//2, 100), ad_elements['hook'], 
                     fill=BRAND_GOLD, font=self.subtitle_font, anchor="mm")
        
        # Content area below phone
        content_y = 200 + (600 if phone_images else 0) + 50
        
        # Add phone name with style
        phone_name = phone_data.get("name", "")
        self.add_text_with_outline(draw, phone_name, self.width//2, content_y,
                                 self.title_font, "white", anchor="mm")
        content_y += 100
        
        # Add featured specs in stylish layout
        featured_specs = [
            ("📸", phone_data.get('main_camera', 'N/A').split('+')[0]),
            ("⚡", phone_data.get('ram', 'N/A')),
            ("💾", phone_data.get('storage', 'N/A'))
        ]
        
        spec_spacing = self.width // 4
        for i, (icon, spec) in enumerate(featured_specs):
            x_pos = spec_spacing * (i + 1)
            
            # Draw spec circle
            circle_radius = 80
            draw.ellipse([x_pos - circle_radius, content_y - circle_radius,
                         x_pos + circle_radius, content_y + circle_radius],
                        fill=(255, 255, 255, 50), outline=BRAND_GOLD, width=3)
            
            # Draw icon
            draw.text((x_pos, content_y - 20), icon, 
                     fill=BRAND_GOLD, font=self.title_font, anchor="mm")
            
            # Draw spec text
            draw.text((x_pos, content_y + 30), spec, 
                     fill="white", font=self.small_font, anchor="mm")
        
        content_y += 200
        
        # Add CTA
        if ad_elements.get('cta'):
            cta_box_y = content_y
            cta_box_height = 80
            cta_box_width = self.width - 150
            
            self.add_rounded_rectangle(draw, (self.width - cta_box_width)//2, cta_box_y,
                                     (self.width + cta_box_width)//2, cta_box_y + cta_box_height,
                                     fill=BRAND_GOLD, radius=30, outline="white")
            
            draw.text((self.width//2, cta_box_y + cta_box_height//2), ad_elements['cta'],
                     fill=BRAND_MAROON, font=self.title_font, anchor="mm")
            content_y += cta_box_height + 50
        
        # Add urgency
        if ad_elements.get('urgency'):
            draw.text((self.width//2, content_y), f"⏰ {ad_elements['urgency']}", 
                     fill="#FF6B6B", font=self.body_font, anchor="mm")
            content_y += 50
        
        # Add branding at bottom
        bottom_y = self.height - 80
        draw.text((self.width//2, bottom_y), "Available at Tripple K Communications", 
                 fill=BRAND_GOLD, font=self.subtitle_font, anchor="mm")
        draw.text((self.width//2, bottom_y + 40), f"Contact: {TRIPPLEK_PHONE}", 
                 fill="white", font=self.small_font, anchor="mm")
        
        return img

# ----------------------------
# SOCIAL POST GENERATION
# ----------------------------
def create_marketing_prompt(phone_data: dict, persona: str, tone: str) -> str:
    """Create prompt for marketing content generation"""
    specs_summary = format_specs_for_display(phone_data)
    
    return f"""Generate COMPLETE marketing campaign for this smartphone for Tripple K Communications in Kenya.

PHONE SPECIFICATIONS:
{specs_summary}

BUSINESS INFO:
- Tripple K Communications - Leading phone retailer in Kenya
- 100% genuine phones with manufacturer warranty
- Pay on delivery available
- Fast Nairobi delivery
- Contact: {TRIPPLEK_PHONE}
- Website: {TRIPPLEK_URL}

TARGET AUDIENCE: {persona}
BRAND TONE: {tone}

REQUIRED OUTPUT FORMAT:

=== AD CREATIVE ELEMENTS ===
Hook/Banner: [Attention-grabbing headline for ads - max 10 words]
CTA: [Clear call-to-action - tell users what to do]
Urgency: [Create urgency message - limited time/stock offer]

=== SOCIAL MEDIA POSTS ===
TikTok: [Video caption - 80-100 chars, engaging for short videos, include trending elements]
WhatsApp: [Message - 2-3 lines, includes key specs and contact, easy to forward]
Facebook: [Post - 3-4 sentences, detailed benefits, includes emojis]
Instagram: [Caption - 2-3 stylish lines, visual-focused, influencer style]

=== HASHTAGS ===
[7-10 relevant hashtags for Kenya phone market, include brand hashtags]

Make content platform-specific, highlight unique features, and include emotional triggers."""

def parse_marketing_content(text: str) -> Dict[str, str]:
    """Parse marketing content from AI response"""
    content = {
        # Ad elements
        "hook": "",
        "cta": "",
        "urgency": "",
        # Social posts
        "tiktok": "",
        "whatsapp": "",
        "facebook": "",
        "instagram": "",
        "hashtags": ""
    }
    
    current_section = None
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for section headers
        if "=== AD CREATIVE ELEMENTS ===" in line:
            current_section = "ad_elements"
            continue
        elif "=== SOCIAL MEDIA POSTS ===" in line:
            current_section = "social_posts"
            continue
        elif "=== HASHTAGS ===" in line:
            current_section = "hashtags"
            continue
        
        # Parse content based on current section
        if current_section == "ad_elements":
            if "Hook/Banner:" in line:
                content["hook"] = line.split("Hook/Banner:")[1].strip()
            elif "CTA:" in line:
                content["cta"] = line.split("CTA:")[1].strip()
            elif "Urgency:" in line:
                content["urgency"] = line.split("Urgency:")[1].strip()
        
        elif current_section == "social_posts":
            if "TikTok:" in line:
                content["tiktok"] = line.split("TikTok:")[1].strip()
            elif "WhatsApp:" in line:
                content["whatsapp"] = line.split("WhatsApp:")[1].strip()
            elif "Facebook:" in line:
                content["facebook"] = line.split("Facebook:")[1].strip()
            elif "Instagram:" in line:
                content["instagram"] = line.split("Instagram:")[1].strip()
        
        elif current_section == "hashtags":
            if line and not line.startswith("==="):
                content["hashtags"] = line.strip()
    
    return content

def generate_marketing_content(phone_data: dict, persona: str, tone: str) -> Optional[Dict[str, str]]:
    """Generate marketing content with rate limiting"""
    if not client:
        st.error("Groq API not configured")
        return None
    
    # Check rate limit
    if not rate_limiter.can_make_call():
        wait_time = rate_limiter.get_wait_time()
        st.error(f"Rate limit exceeded. Please wait {int(wait_time)} seconds.")
        return None
    
    try:
        prompt = create_marketing_prompt(phone_data, persona, tone)
        
        # Record API call
        rate_limiter.record_call()
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=1000,
            timeout=30
        )
        
        generated_text = response.choices[0].message.content.strip()
        return parse_marketing_content(generated_text)
        
    except Exception as e:
        st.error(f"Failed to generate content: {str(e)}")
        return None

def display_marketing_content(content: Dict[str, str]):
    """Display marketing content in organized sections"""
    
    # Ad Elements
    if any(content.get(key) for key in ["hook", "cta", "urgency"]):
        st.subheader("🎯 Ad Creative Elements")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if content.get("hook"):
                st.markdown(f'<div class="element-box">', unsafe_allow_html=True)
                st.markdown("**🎨 Hook/Banner**")
                st.info(content['hook'])
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if content.get("cta"):
                st.markdown(f'<div class="element-box">', unsafe_allow_html=True)
                st.markdown("**📢 Call-to-Action**")
                st.success(content['cta'])
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            if content.get("urgency"):
                st.markdown(f'<div class="element-box">', unsafe_allow_html=True)
                st.markdown("**⏰ Urgency**")
                st.warning(content['urgency'])
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Social Media Posts
    st.subheader("📱 Social Media Posts")
    
    platforms = [
        ("🎵 TikTok", content.get("tiktok", "")),
        ("💬 WhatsApp", content.get("whatsapp", "")),
        ("📘 Facebook", content.get("facebook", "")),
        ("📸 Instagram", content.get("instagram", ""))
    ]
    
    for platform_name, platform_content in platforms:
        if platform_content:
            st.markdown(f'<div class="post-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="post-platform">{platform_name}</div>', unsafe_allow_html=True)
            st.text(platform_content)
            if st.button(f"📋 Copy {platform_name.split()[1]}", key=f"copy_{platform_name}"):
                st.code(platform_content)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Hashtags
    if content.get("hashtags"):
        st.markdown("---")
        st.subheader("🏷️ Hashtags")
        st.markdown(f'<div class="specs-box">{content["hashtags"]}</div>', unsafe_allow_html=True)

# ----------------------------
# MAIN APPLICATION
# ----------------------------
def main():
    st.title("📱 Tripple K Phone Marketing Suite")
    st.markdown("Create professional marketing campaigns for smartphones")
    
    # Initialize session state
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "current_phone" not in st.session_state:
        st.session_state.current_phone = None
    if "marketing_content" not in st.session_state:
        st.session_state.marketing_content = None
    if "ad_elements" not in st.session_state:
        st.session_state.ad_elements = {}
    
    # Tab navigation
    tabs = st.tabs(["🔍 Find Phone", "📝 Create Campaign", "🎨 Generate Ads"])
    
    # TAB 1: FIND PHONE
    with tabs[0]:
        st.subheader("Search Phone Specifications")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            phone_query = st.text_input("Enter phone name or model:", 
                                      placeholder="e.g., Samsung Galaxy S23, iPhone 15",
                                      key="search_input")
        with col2:
            search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_btn:
            if not phone_query.strip():
                st.warning("Please enter a phone name")
            else:
                with st.spinner("🔍 Searching database..."):
                    url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(phone_query)}"
                    results, error = fetch_api_data(url)
                    
                    if error or not results:
                        url2 = f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(phone_query)}"
                        results, error = fetch_api_data(url2)
                    
                    if error:
                        st.error(f"❌ Search failed: {error}")
                    elif not results:
                        st.info("No phones found. Try a different search term.")
                    else:
                        st.session_state.search_results = results
                        st.success(f"✅ Found {len(results)} phones")
        
        # Display search results
        if st.session_state.search_results:
            results = st.session_state.search_results
            phone_names = [r.get("name", "Unknown") for r in results]
            selected_name = st.selectbox("Select a phone:", phone_names, key="phone_select")
            
            if selected_name:
                selected = next(r for r in results if r.get("name") == selected_name)
                
                with st.spinner("📱 Loading full specifications..."):
                    details_url = f"https://tkphsp2.vercel.app/gsm/info/{selected.get('id')}"
                    details, error = fetch_api_data(details_url)
                    
                    if error or not details:
                        url2 = f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(selected_name)}"
                        search_res, _ = fetch_api_data(url2)
                        if search_res:
                            slug = search_res[0]["slug"]
                            details, error = fetch_api_data(f"https://api-mobilespecs.azharimm.dev/{slug}")
                    
                    if error:
                        st.error(f"❌ Could not load specs: {error}")
                    else:
                        phone_data = parse_phone_specs(details)
                        st.session_state.current_phone = phone_data
                        
                        # Display phone info
                        st.markdown(f'<h2 class="phone-title">{phone_data["name"]}</h2>', 
                                  unsafe_allow_html=True)
                        
                        # Launch date info
                        launch_date, time_passed = get_market_info(phone_data["launch_date"])
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.caption(f"📅 {launch_date}")
                        with col_info2:
                            if time_passed:
                                st.caption(f"⏰ {time_passed}")
                        
                        # Two column layout
                        col_img, col_specs = st.columns([1, 1])
                        
                        with col_img:
                            # Get and display phone images
                            if phone_data.get("id"):
                                phone_images = get_phone_images(phone_data["id"])
                                if phone_images:
                                    # Create tabs for multiple images
                                    img_tabs = st.tabs([f"Image {i+1}" for i in range(min(3, len(phone_images)))])
                                    for i, img_tab in enumerate(img_tabs):
                                        with img_tab:
                                            img = download_image(phone_images[i])
                                            if img:
                                                st.image(img, use_container_width=True)
                            elif phone_data["cover"]:
                                phone_img = download_image(phone_data["cover"])
                                if phone_img:
                                    st.image(phone_img, use_container_width=True)
                        
                        with col_specs:
                            formatted_specs = format_specs_for_display(phone_data)
                            st.markdown('<div class="specs-box">', unsafe_allow_html=True)
                            st.text(formatted_specs)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            if st.button("📋 Copy All Specs", use_container_width=True):
                                st.code(formatted_specs)
    
    # TAB 2: CREATE CAMPAIGN
    with tabs[1]:
        st.subheader("Create Marketing Campaign")
        
        if not st.session_state.current_phone:
            st.info("👈 Please search and select a phone first.")
        elif not client:
            st.warning("⚠️ Groq API key not configured. Content generation is disabled.")
        else:
            phone_data = st.session_state.current_phone
            
            # Configuration
            st.markdown("### 🎯 Campaign Settings")
            col1, col2 = st.columns(2)
            with col1:
                persona = st.selectbox(
                    "Target Audience",
                    ["General Consumers", "Tech Enthusiasts", "Students & Youth", 
                     "Working Professionals", "Content Creators", "Budget Buyers",
                     "Gamers", "Photography Lovers"],
                    index=0,
                    key="persona_select"
                )
            with col2:
                tone = st.selectbox(
                    "Brand Tone",
                    ["Professional", "Friendly & Relatable", "Excited & Energetic", 
                     "Informative & Helpful", "Urgent & Limited", "Luxury & Premium",
                     "Trendy & Modern"],
                    index=0,
                    key="tone_select"
                )
            
            if st.button("🚀 Generate Complete Campaign", type="primary", use_container_width=True):
                with st.spinner("🎨 Creating marketing campaign..."):
                    content = generate_marketing_content(phone_data, persona, tone)
                    
                    if content:
                        st.session_state.marketing_content = content
                        # Extract ad elements for use in ads
                        st.session_state.ad_elements = {
                            "hook": content.get("hook", ""),
                            "cta": content.get("cta", ""),
                            "urgency": content.get("urgency", "")
                        }
                        st.balloons()
                        st.success("✅ Marketing campaign generated successfully!")
            
            # Display generated content
            if st.session_state.marketing_content:
                display_marketing_content(st.session_state.marketing_content)
                
                # Download all content
                if st.button("📥 Download Complete Campaign", use_container_width=True):
                    all_content = "="*50 + "\n"
                    all_content += f"Marketing Campaign for {phone_data['name']}\n"
                    all_content += "="*50 + "\n\n"
                    
                    # Ad elements
                    all_content += "AD CREATIVE ELEMENTS:\n"
                    all_content += f"Hook: {st.session_state.marketing_content.get('hook', '')}\n"
                    all_content += f"CTA: {st.session_state.marketing_content.get('cta', '')}\n"
                    all_content += f"Urgency: {st.session_state.marketing_content.get('urgency', '')}\n\n"
                    
                    # Social posts
                    all_content += "SOCIAL MEDIA POSTS:\n"
                    for platform in ["tiktok", "whatsapp", "facebook", "instagram"]:
                        if content := st.session_state.marketing_content.get(platform):
                            all_content += f"\n{platform.upper()}:\n{content}\n"
                    
                    # Hashtags
                    all_content += f"\nHASHTAGS:\n{st.session_state.marketing_content.get('hashtags', '')}\n"
                    
                    st.download_button(
                        "Download",
                        all_content,
                        file_name=f"tripplek_{phone_data['name'].replace(' ', '_')}_campaign.txt",
                        mime="text/plain"
                    )
    
    # TAB 3: GENERATE ADS
    with tabs[2]:
        st.subheader("Generate Marketing Ads")
        
        if not st.session_state.current_phone:
            st.info("👈 Please search and select a phone first.")
        else:
            phone_data = st.session_state.current_phone
            
            # Show ad elements if available
            if st.session_state.ad_elements:
                st.markdown("### 🎯 Using AI-Generated Elements")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    if hook := st.session_state.ad_elements.get("hook"):
                        st.info(f"**Hook:** {hook}")
                with col_e2:
                    if cta := st.session_state.ad_elements.get("cta"):
                        st.success(f"**CTA:** {cta}")
                with col_e3:
                    if urgency := st.session_state.ad_elements.get("urgency"):
                        st.warning(f"**Urgency:** {urgency}")
            
            st.markdown("### 🖼️ Select Ad Types")
            
            # Ad type selection
            ad_types = st.multiselect(
                "Choose ad formats to generate:",
                ["Facebook Ad (1200x630)", "WhatsApp Ad (1080x1080)", "Instagram Ad (1080x1350)"],
                default=["Facebook Ad (1200x630)", "WhatsApp Ad (1080x1080)"]
            )
            
            if st.button("✨ Generate Selected Ads", type="primary", use_container_width=True):
                if not ad_types:
                    st.warning("Please select at least one ad type.")
                else:
                    generated_ads = {}
                    
                    with st.spinner("🎨 Creating ad images..."):
                        for ad_type in ad_types:
                            try:
                                if "Facebook" in ad_type:
                                    generator = FacebookAdGenerator()
                                    ad_image = generator.generate(phone_data, st.session_state.ad_elements)
                                elif "WhatsApp" in ad_type:
                                    generator = WhatsAppAdGenerator()
                                    ad_image = generator.generate(phone_data, st.session_state.ad_elements)
                                elif "Instagram" in ad_type:
                                    generator = InstagramAdGenerator()
                                    ad_image = generator.generate(phone_data, st.session_state.ad_elements)
                                
                                # Convert to bytes
                                img_bytes = BytesIO()
                                ad_image.save(img_bytes, format='PNG', quality=95)
                                img_bytes.seek(0)
                                
                                generated_ads[ad_type] = img_bytes.getvalue()
                                
                            except Exception as e:
                                st.error(f"Failed to create {ad_type}: {str(e)}")
                    
                    if generated_ads:
                        st.session_state.generated_ads = generated_ads
                        st.success(f"✅ Generated {len(generated_ads)} ad(s) successfully!")
            
            # Display and download generated ads
            if hasattr(st.session_state, 'generated_ads'):
                st.markdown("---")
                st.subheader("📱 Generated Ads")
                
                for ad_type, ad_bytes in st.session_state.generated_ads.items():
                    with st.expander(f"{ad_type}", expanded=True):
                        st.markdown('<div class="ad-preview">', unsafe_allow_html=True)
                        
                        # Display with appropriate sizing
                        if "Instagram" in ad_type:
                            # Show vertical ads with proper sizing
                            st.image(ad_bytes, width=400)
                        else:
                            st.image(ad_bytes, use_container_width=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Download button for each ad
                        ad_type_simple = ad_type.split()[0].lower()
                        file_name = f"tripplek_{ad_type_simple}_ad.png"
                        
                        st.download_button(
                            f"📥 Download {ad_type.split()[0]} Ad",
                            ad_bytes,
                            file_name=file_name,
                            mime="image/png",
                            key=f"download_{ad_type}"
                        )
    
    # Footer
    st.divider()
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 20px;">
        <h3>Tripple K Communications</h3>
        <p>📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}</p>
        <p style="font-size: 0.9em; color: #666;">Professional Phone Marketing Suite</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Rate limit status
    if rate_limiter.calls:
        calls_left = RATE_LIMIT_CALLS - len(rate_limiter.calls)
        if calls_left > 0:
            st.caption(f"📊 Rate limit: {calls_left} calls remaining this minute")
        else:
            wait_time = rate_limiter.get_wait_time()
            st.caption(f"⏳ Rate limit exceeded. Wait {int(wait_time)} seconds.")

# ----------------------------
# RUN APPLICATION
# ----------------------------
if __name__ == "__main__":
    main()
