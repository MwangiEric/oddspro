import streamlit as st
import requests
import re
from dateutil import parser
from datetime import datetime, timedelta
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Optional, Tuple, Dict, Any
import time

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
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# Rate limiting
RATE_LIMIT_CALLS = 3  # Max API calls per minute
RATE_LIMIT_WINDOW = 60  # Seconds

st.set_page_config(page_title="Tripple K Phone Specs & Ads", layout="centered")

# CSS Styling
st.markdown(f"""
<style>
    .specs-box {{
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        background: #f8f9fa;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.6;
        margin: 10px 0;
        white-space: pre-wrap;
    }}
    .phone-title {{
        color: {BRAND_MAROON};
        margin-bottom: 5px;
        font-size: 1.5em;
    }}
    .post-box {{
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin: 15px 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .post-platform {{
        color: {BRAND_MAROON};
        font-weight: bold;
        font-size: 1.2em;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid {BRAND_MAROON};
    }}
    .copy-btn {{
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 14px;
        margin-top: 10px;
        display: inline-block;
    }}
    .copy-btn:hover {{
        background-color: #45a049;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    .tab-content {{
        padding: 20px 0;
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
        # Remove calls older than the window
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
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=86400)
def download_image(url: str) -> Optional[Image.Image]:
    """Download and cache image"""
    try:
        response = requests.get(url, timeout=10)
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

def extract_mp_value(text: str) -> str:
    """Extract MP values and add 'MP' suffix"""
    if not text or text == "N/A":
        return "N/A"
    
    # Find all numbers that are likely MP values (usually 2-200)
    numbers = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\b', str(text))
    
    if numbers:
        # Filter reasonable MP values (usually between 2 and 200)
        valid_numbers = []
        for num in numbers:
            try:
                value = float(num)
                if 2 <= value <= 200:  # Reasonable MP range
                    valid_numbers.append(f"{int(value) if value.is_integer() else value}MP")
            except:
                continue
        
        if valid_numbers:
            return " + ".join(valid_numbers[:3])  # Max 3 cameras
    
    # If no valid MP found, return N/A
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
                
                # Extract storage (exclude RAM mentions)
                if "storage" in val.lower() or "rom" in val.lower():
                    storage_match = re.search(r'(\d+\s*(?:GB|TB))', val)
                    if storage_match:
                        storage = storage_match.group(1)
                elif "gb" in val.lower() or "tb" in val.lower():
                    # Find all storage mentions
                    storage_matches = re.findall(r'(\d+\s*(?:GB|TB))', val, re.IGNORECASE)
                    if storage_matches:
                        # Filter out RAM if present
                        storage_list = []
                        for i, match in enumerate(storage_matches):
                            # If we found RAM and this is the first match, skip it
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
    """Format specs for clean display (without selfie camera)"""
    specs = [
        f"Phone: {phone_data.get('name', 'N/A')}",
        f"Screen: {phone_data.get('screen', 'N/A')}",
        f"Main Camera: {phone_data.get('main_camera', 'N/A')}",
        f"RAM: {phone_data.get('ram', 'N/A')}",
        f"Storage: {phone_data.get('storage', 'N/A')}",
        f"Battery: {phone_data.get('battery', 'N/A')}",
        f"Chipset: {phone_data.get('chipset', 'N/A')}",
        f"OS: {phone_data.get('os', 'N/A')}"
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

def copy_to_clipboard(text: str, button_label: str = "Copy"):
    """Create a copy button using Streamlit's built-in functionality"""
    # Create a unique key for the button
    button_key = f"copy_{hash(text) % 10000}"
    
    # Use st.button with callback
    if st.button(button_label, key=button_key):
        st.write(f"📋 Copied to clipboard!")
        st.code(text)
        # Note: In production, you'd use javascript to actually copy
        # This is a simplified version for Streamlit

# ----------------------------
# AD GENERATORS
# ----------------------------
class AdGenerator:
    """Base class for ad generators"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.logo = get_logo()
        
        # Load fonts
        try:
            self.title_font = ImageFont.truetype("arialbd.ttf", 42)
            self.subtitle_font = ImageFont.truetype("arialbd.ttf", 28)
            self.body_font = ImageFont.truetype("arial.ttf", 24)
            self.small_font = ImageFont.truetype("arial.ttf", 20)
        except:
            # Fallback to default fonts
            self.title_font = ImageFont.load_default()
            self.subtitle_font = ImageFont.load_default()
            self.body_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
    
    def add_logo(self, img: Image.Image) -> Image.Image:
        """Add Tripple K logo to image"""
        if self.logo:
            # Resize logo
            logo_size = min(self.width // 8, 150)
            self.logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            
            # Position at top right
            x = self.width - self.logo.width - 20
            y = 20
            
            result = img.copy()
            result.paste(self.logo, (x, y), self.logo)
            return result
        return img
    
    def add_phone_image(self, base_img: Image.Image, phone_img: Image.Image) -> Image.Image:
        """Add phone image to ad, scaled to fit"""
        # Calculate size (40% of width, 70% of height)
        max_width = int(self.width * 0.4)
        max_height = int(self.height * 0.7)
        
        # Resize maintaining aspect ratio
        phone_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Position on left with some padding
        x = 40
        y = (self.height - phone_img.height) // 2
        
        result = base_img.copy()
        result.paste(phone_img, (x, y), phone_img)
        return result
    
    def add_phone_title(self, draw: ImageDraw.ImageDraw, phone_name: str, ad_elements: Dict[str, str]):
        """Add phone title in the middle after logo"""
        # Calculate center position
        center_x = self.width // 2
        
        # Add hook/banner text if provided
        if ad_elements.get('hook'):
            hook_y = 80
            draw.text((center_x, hook_y), ad_elements['hook'], 
                     fill=BRAND_MAROON, font=self.subtitle_font, anchor="mm")
        
        # Add phone name
        title_y = 130 if ad_elements.get('hook') else 80
        draw.text((center_x, title_y), phone_name, 
                 fill=BRAND_MAROON, font=self.title_font, anchor="mm")
        
        return title_y + 80  # Return Y position for next element

class FacebookAdGenerator(AdGenerator):
    """Facebook ad generator (1200x630)"""
    
    def __init__(self):
        super().__init__(1200, 630)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        """Generate Facebook ad with marketing elements"""
        if ad_elements is None:
            ad_elements = {}
        
        # Create background
        img = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add logo
        img = self.add_logo(img)
        draw = ImageDraw.Draw(img)
        
        # Download phone image
        phone_img = None
        if phone_data.get("cover"):
            phone_img = download_image(phone_data["cover"])
        
        # Add phone image if available
        if phone_img:
            img = self.add_phone_image(img, phone_img)
            draw = ImageDraw.Draw(img)
        
        # Add phone title and banner
        next_y = self.add_phone_title(draw, phone_data.get("name", ""), ad_elements)
        
        # Add specs on right side
        x_start = int(self.width * 0.55)
        y = next_y
        
        # Key specs
        specs = [
            f"Screen: {phone_data.get('screen', 'N/A')}",
            f"Camera: {phone_data.get('main_camera', 'N/A')}",
            f"RAM: {phone_data.get('ram', 'N/A')}",
            f"Storage: {phone_data.get('storage', 'N/A')}",
            f"Battery: {phone_data.get('battery', 'N/A')}",
            f"OS: {phone_data.get('os', 'N/A')}"
        ]
        
        for spec in specs:
            draw.text((x_start, y), spec, fill="black", font=self.body_font)
            y += 35
        
        # Add CTA if provided
        if ad_elements.get('cta'):
            y += 20
            draw.text((x_start, y), ad_elements['cta'], 
                     fill=BRAND_MAROON, font=self.subtitle_font)
            y += 40
        
        # Add contact info
        draw.text((x_start, y), f"📞 {TRIPPLEK_PHONE}", 
                 fill="#333", font=self.body_font)
        y += 35
        draw.text((x_start, y), f"🌐 {TRIPPLEK_URL}", 
                 fill="#666", font=self.small_font)
        
        # Add urgency if provided
        if ad_elements.get('urgency'):
            y += 50
            draw.text((x_start, y), f"⚠️ {ad_elements['urgency']}", 
                     fill="#D32F2F", font=self.body_font)
        
        return img

class WhatsAppAdGenerator(AdGenerator):
    """WhatsApp ad generator (800x800)"""
    
    def __init__(self):
        super().__init__(800, 800)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        """Generate WhatsApp ad"""
        if ad_elements is None:
            ad_elements = {}
        
        # Create background
        img = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add header with logo
        draw.rectangle([(0, 0), (self.width, 100)], fill=BRAND_MAROON)
        
        # Add logo to header
        if self.logo:
            self.logo.thumbnail((60, 60), Image.Resampling.LANCZOS)
            img.paste(self.logo, (20, 20), self.logo)
        
        # Header text
        draw.text((100, 30), "TRIPPLE K COMMUNICATIONS", 
                 fill="white", font=self.subtitle_font)
        draw.text((100, 65), "100% Genuine Phones | Official Warranty", 
                 fill=BRAND_GOLD, font=self.small_font)
        
        # Download phone image
        phone_img = None
        if phone_data.get("cover"):
            phone_img = download_image(phone_data["cover"])
        
        # Add phone image
        if phone_img:
            # Position phone image below header
            phone_img.thumbnail((350, 350), Image.Resampling.LANCZOS)
            x = (self.width - phone_img.width) // 2
            y = 120
            img.paste(phone_img, (x, y), phone_img)
            draw = ImageDraw.Draw(img)
            
            # Add phone name below image
            phone_name_y = y + phone_img.height + 20
            draw.text((self.width//2, phone_name_y), phone_data.get("name", ""), 
                     fill=BRAND_MAROON, font=self.title_font, anchor="mm")
            
            # Start specs below phone name
            next_y = phone_name_y + 60
        else:
            # If no image, start specs lower
            next_y = 150
        
        # Key specs in two columns
        col1_x = 50
        col2_x = self.width // 2 + 50
        
        specs = [
            (col1_x, f"Screen: {phone_data.get('screen', 'N/A')}"),
            (col1_x, f"Camera: {phone_data.get('main_camera', 'N/A')}"),
            (col1_x, f"RAM: {phone_data.get('ram', 'N/A')}"),
            (col2_x, f"Storage: {phone_data.get('storage', 'N/A')}"),
            (col2_x, f"Battery: {phone_data.get('battery', 'N/A')}"),
            (col2_x, f"OS: {phone_data.get('os', 'N/A')}")
        ]
        
        y_offset = next_y
        for x_pos, spec in specs:
            draw.text((x_pos, y_offset), spec, fill="black", font=self.body_font)
            y_offset += 35
        
        # Add CTA and contact
        cta_y = y_offset + 30
        if ad_elements.get('cta'):
            draw.text((self.width//2, cta_y), ad_elements['cta'], 
                     fill=BRAND_MAROON, font=self.subtitle_font, anchor="mm")
            cta_y += 40
        
        draw.text((self.width//2, cta_y), f"📱 Call/WhatsApp: {TRIPPLEK_PHONE}", 
                 fill="#2E7D32", font=self.body_font, anchor="mm")
        
        # Footer
        draw.text((self.width//2, self.height - 40), f"🌐 {TRIPPLEK_URL}", 
                 fill="#666", font=self.small_font, anchor="mm")
        
        return img

class TikTokAdGenerator(AdGenerator):
    """TikTok ad generator (1080x1920) - Vertical format"""
    
    def __init__(self):
        super().__init__(1080, 1920)
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        """Generate TikTok ad"""
        if ad_elements is None:
            ad_elements = {}
        
        # Create gradient background
        img = Image.new('RGB', (self.width, self.height), color='black')
        draw = ImageDraw.Draw(img)
        
        # Add gradient
        for y in range(self.height):
            # Purple to blue gradient
            r = int(138 * (1 - y/self.height))
            g = int(43 * (1 - y/self.height))
            b = int(226 - (100 * y/self.height))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        # Add logo at top
        if self.logo:
            self.logo.thumbnail((100, 100), Image.Resampling.LANCZOS)
            img.paste(self.logo, (self.width - 120, 40), self.logo)
        
        # Download phone image
        phone_img = None
        if phone_data.get("cover"):
            phone_img = download_image(phone_data["cover"])
        
        if phone_img:
            # Resize phone image
            max_width = int(self.width * 0.8)
            max_height = int(self.height * 0.5)
            phone_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Center the phone image
            x = (self.width - phone_img.width) // 2
            y = 200
            
            img.paste(phone_img, (x, y), phone_img)
            draw = ImageDraw.Draw(img)
            
            # Add hook/banner
            if ad_elements.get('hook'):
                hook_y = y + phone_img.height + 30
                draw.text((self.width//2, hook_y), ad_elements['hook'], 
                         fill="#FFD700", font=self.subtitle_font, anchor="mm")
                hook_y += 50
            else:
                hook_y = y + phone_img.height + 80
            
            # Add phone name
            draw.text((self.width//2, hook_y), phone_data.get("name", ""), 
                     fill="white", font=self.title_font, anchor="mm")
            
            # Add key feature
            feature_y = hook_y + 70
            key_feature = f"📸 {phone_data.get('main_camera', '').split('+')[0]}"  # First camera
            if key_feature != "📸 N/A":
                draw.text((self.width//2, feature_y), key_feature, 
                         fill="#FFD700", font=self.subtitle_font, anchor="mm")
            
            # Add CTA
            cta_y = feature_y + 80
            if ad_elements.get('cta'):
                draw.text((self.width//2, cta_y), ad_elements['cta'], 
                         fill="white", font=self.subtitle_font, anchor="mm")
                cta_y += 50
            
            # Add urgency
            if ad_elements.get('urgency'):
                draw.text((self.width//2, cta_y), f"🔥 {ad_elements['urgency']}", 
                         fill="#FF6B6B", font=self.body_font, anchor="mm")
                cta_y += 50
            
            # Add contact at bottom
            bottom_y = self.height - 150
            draw.text((self.width//2, bottom_y), "Available at", 
                     fill="white", font=self.small_font, anchor="mm")
            draw.text((self.width//2, bottom_y + 40), "Tripple K Communications", 
                     fill="#FFD700", font=self.body_font, anchor="mm")
            draw.text((self.width//2, bottom_y + 80), f"📞 {TRIPPLEK_PHONE}", 
                     fill="white", font=self.small_font, anchor="mm")
        
        return img

# ----------------------------
# SOCIAL POST GENERATION
# ----------------------------
def create_marketing_prompt(phone_data: dict, persona: str, tone: str) -> str:
    """Create prompt for marketing content generation"""
    specs_summary = format_specs_for_display(phone_data)
    
    return f"""Generate complete marketing content for this phone for Tripple K Communications in Kenya.

PHONE SPECIFICATIONS:
{specs_summary}

TRIPPLE K SELLING POINTS:
- 100% genuine phones with official warranty
- Pay on delivery available
- Fast Nairobi delivery
- Contact: {TRIPPLEK_PHONE}
- Website: {TRIPPLEK_URL}

TARGET AUDIENCE: {persona}
BRAND TONE: {tone}

REQUIRED OUTPUT FORMAT:

=== AD ELEMENTS ===
Hook/Banner: [Short attention-grabbing headline for ads]
CTA: [Clear call-to-action text]
Urgency: [Create urgency message e.g., "Limited Stock!"]

=== SOCIAL MEDIA POSTS ===
TikTok: [Video caption - max 100 chars, engaging for short videos]
WhatsApp: [Message - 2-3 lines, includes contact info]
Facebook: [Detailed post - 3-4 sentences, includes benefits]
Instagram: [Stylish caption - 2-3 lines, visual-focused]

=== HASHTAGS ===
[5-7 relevant hashtags for Kenya phone market]

Make content platform-specific, focused on phone features, and include emotional triggers."""

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
        if line.startswith("=== AD ELEMENTS ==="):
            current_section = "ad_elements"
            continue
        elif line.startswith("=== SOCIAL MEDIA POSTS ==="):
            current_section = "social_posts"
            continue
        elif line.startswith("=== HASHTAGS ==="):
            current_section = "hashtags"
            continue
        
        # Parse content based on current section
        if current_section == "ad_elements":
            if "Hook/Banner:" in line:
                content["hook"] = line.replace("Hook/Banner:", "").strip()
            elif "CTA:" in line:
                content["cta"] = line.replace("CTA:", "").strip()
            elif "Urgency:" in line:
                content["urgency"] = line.replace("Urgency:", "").strip()
        
        elif current_section == "social_posts":
            if "TikTok:" in line:
                content["tiktok"] = line.replace("TikTok:", "").strip()
            elif "WhatsApp:" in line:
                content["whatsapp"] = line.replace("WhatsApp:", "").strip()
            elif "Facebook:" in line:
                content["facebook"] = line.replace("Facebook:", "").strip()
            elif "Instagram:" in line:
                content["instagram"] = line.replace("Instagram:", "").strip()
        
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
            temperature=0.85,
            max_tokens=800,
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
        st.subheader("🎯 Ad Elements")
        
        if content.get("hook"):
            st.info(f"**Hook/Banner:** {content['hook']}")
        
        if content.get("cta"):
            st.success(f"**CTA:** {content['cta']}")
        
        if content.get("urgency"):
            st.warning(f"**Urgency:** {content['urgency']}")
        
        st.markdown("---")
    
    # Social Media Posts
    st.subheader("📱 Social Media Posts")
    
    platforms = [
        ("TikTok", content.get("tiktok", "")),
        ("WhatsApp", content.get("whatsapp", "")),
        ("Facebook", content.get("facebook", "")),
        ("Instagram", content.get("instagram", ""))
    ]
    
    for platform_name, platform_content in platforms:
        if platform_content:
            with st.expander(f"{platform_name}", expanded=True):
                st.text(platform_content)
                if st.button(f"Copy {platform_name}", key=f"copy_{platform_name}"):
                    st.code(platform_content)
    
    # Hashtags
    if content.get("hashtags"):
        st.markdown("---")
        st.subheader("🏷️ Hashtags")
        st.text(content["hashtags"])

# ----------------------------
# MAIN APPLICATION
# ----------------------------
def main():
    st.title("📱 Tripple K Phone Specs & Ads")
    
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
    tabs = st.tabs(["🔍 Phone Specs", "📝 Generate Content", "🎨 Create Ads"])
    
    # TAB 1: PHONE SPECS
    with tabs[0]:
        st.subheader("Find Phone Specifications")
        
        phone_query = st.text_input("Enter phone name or model:", 
                                  placeholder="e.g., Samsung Galaxy S23",
                                  key="search_input")
        
        if st.button("🔍 Search", type="primary", key="search_btn"):
            if not phone_query.strip():
                st.warning("Please enter a phone name")
            else:
                with st.spinner("Searching..."):
                    url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(phone_query)}"
                    results, error = fetch_api_data(url)
                    
                    if error or not results:
                        url2 = f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(phone_query)}"
                        results, error = fetch_api_data(url2)
                    
                    if error:
                        st.error(f"Search failed: {error}")
                    elif not results:
                        st.info("No phones found. Try a different search term.")
                    else:
                        st.session_state.search_results = results
                        st.success(f"Found {len(results)} phones")
        
        # Display search results
        if st.session_state.search_results:
            results = st.session_state.search_results
            phone_names = [r.get("name", "Unknown") for r in results]
            selected_name = st.selectbox("Select a phone:", phone_names, key="phone_select")
            
            if selected_name:
                selected = next(r for r in results if r.get("name") == selected_name)
                
                with st.spinner("Loading details..."):
                    details_url = f"https://tkphsp2.vercel.app/gsm/info/{selected.get('id')}"
                    details, error = fetch_api_data(details_url)
                    
                    if error or not details:
                        url2 = f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(selected_name)}"
                        search_res, _ = fetch_api_data(url2)
                        if search_res:
                            slug = search_res[0]["slug"]
                            details, error = fetch_api_data(f"https://api-mobilespecs.azharimm.dev/{slug}")
                    
                    if error:
                        st.error(f"Could not load specs: {error}")
                    else:
                        phone_data = parse_phone_specs(details)
                        st.session_state.current_phone = phone_data
                        
                        # Display phone info
                        st.markdown(f'<h2 class="phone-title">{phone_data["name"]}</h2>', 
                                  unsafe_allow_html=True)
                        
                        # Launch date info
                        launch_date, time_passed = get_market_info(phone_data["launch_date"])
                        st.caption(f"📅 {launch_date}")
                        if time_passed:
                            st.caption(f"⏰ {time_passed}")
                        
                        # Two column layout
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            if phone_data["cover"]:
                                phone_img = download_image(phone_data["cover"])
                                if phone_img:
                                    st.image(phone_img, use_container_width=True)
                        
                        with col2:
                            formatted_specs = format_specs_for_display(phone_data)
                            st.markdown('<div class="specs-box">', unsafe_allow_html=True)
                            st.text(formatted_specs)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            copy_to_clipboard(formatted_specs, "📋 Copy Specifications")
    
    # TAB 2: GENERATE CONTENT
    with tabs[1]:
        st.subheader("Generate Marketing Content")
        
        if not st.session_state.current_phone:
            st.info("👈 Please search and select a phone in the 'Phone Specs' tab first.")
        elif not client:
            st.warning("⚠️ Groq API key not configured. Content generation is disabled.")
        else:
            phone_data = st.session_state.current_phone
            
            # Configuration
            col1, col2 = st.columns(2)
            with col1:
                persona = st.selectbox(
                    "🎯 Target Audience",
                    ["General Consumers", "Tech Enthusiasts", "Students & Youth", 
                     "Working Professionals", "Content Creators", "Budget-Conscious Buyers"],
                    index=0,
                    key="persona_select"
                )
            with col2:
                tone = st.selectbox(
                    "🎨 Brand Tone",
                    ["Professional", "Friendly & Relatable", "Excited & Energetic", 
                     "Informative & Helpful", "Urgent & Limited"],
                    index=0,
                    key="tone_select"
                )
            
            if st.button("🚀 Generate Marketing Content", type="primary", use_container_width=True):
                with st.spinner("Creating marketing content with AI..."):
                    content = generate_marketing_content(phone_data, persona, tone)
                    
                    if content:
                        st.session_state.marketing_content = content
                        # Extract ad elements for use in ads
                        st.session_state.ad_elements = {
                            "hook": content.get("hook", ""),
                            "cta": content.get("cta", ""),
                            "urgency": content.get("urgency", "")
                        }
                        st.success("✅ Marketing content generated successfully!")
            
            # Display generated content
            if st.session_state.marketing_content:
                display_marketing_content(st.session_state.marketing_content)
                
                # Download all content
                if st.button("📥 Download All Content", use_container_width=True):
                    all_content = ""
                    for key, value in st.session_state.marketing_content.items():
                        if value:
                            all_content += f"{key.upper()}:\n{value}\n\n"
                    
                    st.download_button(
                        "Download",
                        all_content,
                        file_name=f"{phone_data['name'].replace(' ', '_')}_marketing.txt",
                        mime="text/plain"
                    )
    
    # TAB 3: CREATE ADS
    with tabs[2]:
        st.subheader("Create Marketing Images")
        
        if not st.session_state.current_phone:
            st.info("👈 Please search and select a phone in the 'Phone Specs' tab first.")
        else:
            phone_data = st.session_state.current_phone
            
            # Ad type selection
            ad_type = st.selectbox(
                "🖼️ Select Ad Type:",
                ["Facebook Ad (1200x630)", "WhatsApp Ad (800x800)", "TikTok Ad (1080x1920)"],
                index=0,
                key="ad_type_select"
            )
            
            # Show ad elements if available
            if st.session_state.ad_elements:
                with st.expander("🎯 Ad Elements (AI Generated)", expanded=True):
                    for key, value in st.session_state.ad_elements.items():
                        if value:
                            st.text(f"{key}: {value}")
            
            if st.button("✨ Generate Ad Image", type="primary", use_container_width=True):
                with st.spinner("Creating ad image..."):
                    try:
                        # Create appropriate generator
                        if "Facebook" in ad_type:
                            generator = FacebookAdGenerator()
                        elif "WhatsApp" in ad_type:
                            generator = WhatsAppAdGenerator()
                        else:
                            generator = TikTokAdGenerator()
                        
                        # Generate image with ad elements
                        ad_image = generator.generate(phone_data, st.session_state.ad_elements)
                        
                        # Convert to bytes
                        img_bytes = BytesIO()
                        ad_image.save(img_bytes, format='PNG', quality=95)
                        img_bytes.seek(0)
                        
                        # Store in session state
                        st.session_state.generated_ad = img_bytes.getvalue()
                        st.session_state.current_ad_type = ad_type
                        
                        st.success("✅ Ad created successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Failed to create ad: {str(e)}")
            
            # Display and download
            if hasattr(st.session_state, 'generated_ad'):
                st.markdown("---")
                st.subheader("📱 Generated Ad")
                
                # Display with appropriate sizing
                if "TikTok" in st.session_state.current_ad_type:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.image(st.session_state.generated_ad, width=400)
                else:
                    st.image(st.session_state.generated_ad, use_container_width=True)
                
                # Download button
                ad_type_simple = st.session_state.current_ad_type.split()[0].lower()
                file_name = f"tripplek_{ad_type_simple}_ad.png"
                
                st.download_button(
                    "📥 Download Image",
                    st.session_state.generated_ad,
                    file_name=file_name,
                    mime="image/png",
                    use_container_width=True
                )
    
    # Footer
    st.divider()
    st.caption(f"© Tripple K Communications | 📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}")
    
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
