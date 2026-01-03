"""
Professional Phone Ad Generator - Streamlined Version
With Config Panel, rembg, Poppins Font, RGBA, Layout Dictionary, Real Video
"""

import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageSequence, ImageEnhance
from io import BytesIO
from typing import Optional, Dict, List
import re
import os

# Try to import rembg
try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("⚠️ rembg not installed. Using fallback background removal.")

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG = {
    "brand": {
        "maroon": "#8B0000",
        "gold": "#FFD700",
        "accent": "#FF6B35",
        "mint": "#3EB489",  # Added mint color
        "white": "#FFFFFF",
        "black": "#333333",
    },
    "contact": {
        "phone": "+254700123456",
        "url": "www.tripplek.co.ke",  # Removed https://
        "location": "CBD Opposite MKU Towers"
    },
    "assets": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107",
        "whatsapp_icon": "https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg",
        "icons": {
            "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
            "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
            "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
            "storage": "https://ik.imagekit.io/ericmwangi/memory.png",
            "battery": "https://ik.imagekit.io/ericmwangi/battery.png",
        }
    },
    "api": {
        "base": "https://tkphsp2.vercel.app"
    },
    "fonts": {
        "title": 56,
        "subtitle": 38,
        "body": 34,
        "price": 52,
        "small": 26
    }
}

# Layout Dictionary with larger logo sizes
LAYOUTS = {
    "facebook": {
        "size": (1200, 630),
        "logo": {"x": 40, "y": 30, "w": 250, "h": 90},  # Increased size
        "phone": {"x": 80, "y": 140, "w": 500, "h": 500},
        "content": {"x": 650, "y": 140},
        "specs": {"start_y": 220, "spacing": 70, "icon_size": 52},
        "price": {"x": 650, "y": 490, "w": 380, "h": 85},  # Adjusted size
        "footer": {"y": 580},
        "bg_colors": ("#8B0000", "#4a0000")
    },
    "whatsapp": {
        "size": (1080, 1080),
        "logo": {"x": 50, "y": 40, "w": 250, "h": 90},  # Increased size
        "phone": {"x": 240, "y": 220, "w": 600, "h": 600},
        "content": {"x": 540, "y": 850},
        "specs": {"col1_x": 270, "col2_x": 810, "start_y": 850, "spacing": 65, "icon_size": 48},
        "price": {"x": 315, "y": 980, "w": 420, "h": 85},  # Adjusted size
        "footer": {"y": 1020},
        "bg_colors": ("#FFFFFF", "#FFFFFF"),
        "header_gradient": True
    },
    "instagram": {
        "size": (1080, 1350),
        "logo": {"x": 415, "y": 30, "w": 250, "h": 90},  # Increased size
        "phone": {"x": 190, "y": 150, "w": 700, "h": 700},
        "content": {"x": 540, "y": 900},
        "specs": {"start_x": 140, "y": 920, "spacing": 220, "icon_size": 65},
        "price": {"x": 290, "y": 1050, "w": 450, "h": 85},  # Adjusted size
        "footer": {"y": 1290},
        "bg_colors": ("#0c2461", "#1e3799")
    }
}

st.set_page_config(page_title="Phone Ad Generator", layout="wide", page_icon="📱")

# Minimal CSS
st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);}
    .stButton>button {
        background: linear-gradient(135deg, #8B0000 0%, #6b0000 100%);
        color: white; border: none; padding: 10px 20px; border-radius: 8px;
        font-weight: 600; transition: all 0.3s;
    }
    .stButton>button:hover {transform: translateY(-2px); box-shadow: 0 4px 12px rgba(139, 0, 0, 0.4);}
</style>
""", unsafe_allow_html=True)

# ==========================================
# API & UTILITIES
# ==========================================

@st.cache_data(ttl=3600)
def api_request(endpoint: str) -> Optional[Dict]:
    """Generic API request"""
    try:
        url = f"{CONFIG['api']['base']}{endpoint}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def search_phone(query: str) -> List[Dict]:
    """Search phones"""
    return api_request(f"/gsm/search?q={requests.utils.quote(query)}") or []

def get_phone_details(phone_id: str) -> Optional[Dict]:
    """Get phone details"""
    return api_request(f"/gsm/info/{phone_id}")

def get_phone_image(phone_id: str) -> Optional[str]:
    """Get first phone image"""
    data = api_request(f"/gsm/images/{phone_id}")
    if data and isinstance(data, dict) and "images" in data:
        images = data["images"]
        if images and len(images) > 0:
            return images[0]
    return None

@st.cache_data(ttl=86400)
def download_image(url: str) -> Optional[Image.Image]:
    """Download image"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            return img.convert('RGBA')
    except:
        pass
    return None

def remove_background(img: Image.Image) -> Image.Image:
    """Improved background removal - gentler on phone images"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Simple but effective: remove white/light backgrounds only
    data = img.getdata()
    new_data = []
    
    for item in data:
        r, g, b, a = item
        
        # Keep the phone image, remove only very light backgrounds
        if r > 245 and g > 245 and b > 245:  # Very white
            new_data.append((255, 255, 255, 0))
        elif r > 230 and g > 230 and b > 230:  # Light gray
            new_data.append((255, 255, 255, 50))  # Slightly transparent
        else:
            # Keep phone pixels as is
            new_data.append(item)
    
    img.putdata(new_data)
    return img

@st.cache_data(ttl=86400)
def get_icon(name: str, size: int) -> Image.Image:
    """Get or create icon"""
    url = CONFIG['assets']['icons'].get(name)
    if url:
        img = download_image(url)
        if img:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return img
    
    # Fallback
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    colors = {"screen": "#2196F3", "camera": "#FF5722", "memory": "#9C27B0",
              "storage": "#673AB7", "battery": "#FF9800"}
    color = colors.get(name, CONFIG['brand']['maroon'])
    draw.ellipse([0, 0, size, size], fill=color)
    try:
        font = ImageFont.truetype("poppins.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    draw.text((size//2, size//2), name[0].upper(), fill="white", font=font, anchor="mm")
    return img

def get_whatsapp_icon(size: int = 30) -> Image.Image:
    """Get WhatsApp icon"""
    icon = download_image(CONFIG['assets']['whatsapp_icon'])
    if icon:
        icon = icon.resize((size, size), Image.Resampling.LANCZOS)
        # Make it green
        data = icon.getdata()
        new_data = []
        for item in data:
            if item[3] > 0:  # Not transparent
                new_data.append((37, 211, 102, item[3]))  # WhatsApp green
            else:
                new_data.append(item)
        icon.putdata(new_data)
        return icon
    
    # Fallback
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill="#25D366")  # WhatsApp green
    return img

# ==========================================
# SPEC PARSING
# ==========================================

def extract_specs(details: Dict) -> Dict[str, str]:
    """Extract 5 key specs"""
    specs = {}
    
    # Screen
    display = details.get("display", {})
    screen_size = display.get("size", "")
    if screen_size:
        match = re.search(r'(\d+\.?\d*)\s*inches', str(screen_size), re.IGNORECASE)
        specs["Screen"] = f"{match.group(1)}″ Display" if match else "N/A"
    else:
        specs["Screen"] = "N/A"
    
    # Camera
    camera = details.get("mainCamera", {})
    modules = camera.get("mainModules", "")
    if modules:
        mp_matches = re.findall(r'(\d+)\s*MP', str(modules), re.IGNORECASE)
        specs["Camera"] = " + ".join(mp_matches[:2]) + "MP" if mp_matches else "N/A"
    else:
        specs["Camera"] = "N/A"
    
    # RAM & Storage
    memory = details.get("memory", [])
    specs["RAM"] = "N/A"
    specs["Storage"] = "N/A"
    
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            value = str(mem.get("value", ""))
            
            ram_match = re.search(r'(\d+)\s*GB\s+RAM', value, re.IGNORECASE)
            if ram_match:
                specs["RAM"] = f"{ram_match.group(1)}GB RAM"
            
            storage_match = re.search(r'(\d+)\s*GB\s+(?:ROM|storage|internal)', value, re.IGNORECASE)
            if storage_match:
                specs["Storage"] = f"{storage_match.group(1)}GB"
            
            if specs["Storage"] == "N/A":
                all_gb = re.findall(r'(\d+)\s*GB', value, re.IGNORECASE)
                if len(all_gb) >= 2:
                    specs["Storage"] = f"{all_gb[1]}GB"
                elif len(all_gb) == 1 and specs["RAM"] == "N/A":
                    specs["Storage"] = f"{all_gb[0]}GB"
            
            break
    
    # Battery
    battery = details.get("battery", {})
    batt_type = battery.get("battType", "")
    if batt_type:
        mah_match = re.search(r'(\d+)\s*mAh', str(batt_type), re.IGNORECASE)
        specs["Battery"] = f"{mah_match.group(1)}mAh" if mah_match else "N/A"
    else:
        specs["Battery"] = "N/A"
    
    return specs

def format_price(price_str: str) -> str:
    """Format price"""
    clean = re.sub(r'[^\d]', '', price_str or "99999")
    try:
        return f"{int(clean):,}"
    except:
        return "99,999"

# ==========================================
# AD GENERATOR WITH LAYOUT DICTIONARY
# ==========================================

class AdGenerator:
    """Generate ads using layout dictionary"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.layout = LAYOUTS[platform]
        self.width, self.height = self.layout["size"]
        
        # Load fonts with fallbacks
        self.fonts = {}
        try:
            self.fonts["title"] = ImageFont.truetype("poppins.ttf", CONFIG['fonts']['title'])
            self.fonts["subtitle"] = ImageFont.truetype("poppins.ttf", CONFIG['fonts']['subtitle'])
            self.fonts["body"] = ImageFont.truetype("poppins.ttf", CONFIG['fonts']['body'])
            self.fonts["price"] = ImageFont.truetype("poppins.ttf", CONFIG['fonts']['price'])
            self.fonts["small"] = ImageFont.truetype("poppins.ttf", CONFIG['fonts']['small'])
        except:
            default = ImageFont.load_default()
            self.fonts = {k: default for k in ["title", "subtitle", "body", "price", "small"]}
    
    def create_gradient(self, color1: str, color2: str) -> Image.Image:
        """Create gradient background"""
        img = Image.new('RGBA', (self.width, self.height), color1 + "FF")
        draw = ImageDraw.Draw(img)
        
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        
        for y in range(self.height):
            factor = y / self.height
            r = int(r1 * (1 - factor) + r2 * factor)
            g = int(g1 * (1 - factor) + g2 * factor)
            b = int(b1 * (1 - factor) + b2 * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))
        
        return img
    
    def wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def generate(self, phone_name: str, specs: Dict, price: str, phone_img_url: str) -> Image.Image:
        """Generate ad using layout dictionary"""
        
        # Background
        if self.platform == "whatsapp":
            img = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 255))
            if self.layout.get("header_gradient"):
                draw = ImageDraw.Draw(img)
                for y in range(180):
                    factor = y / 180
                    r = int(139 * (1 - factor) + 255 * factor)
                    draw.line([(0, y), (self.width, y)], fill=(r, 0, 0, 255))
        else:
            img = self.create_gradient(*self.layout["bg_colors"])
        
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Logo (larger size)
        logo = download_image(CONFIG['assets']['logo'])
        if logo:
            logo_cfg = self.layout["logo"]
            logo.thumbnail((logo_cfg["w"], logo_cfg["h"]), Image.Resampling.LANCZOS)
            img.paste(logo, (logo_cfg["x"], logo_cfg["y"]), logo)
        
        # Phone name centered after logo
        logo_cfg = self.layout["logo"]
        name_y = logo_cfg["y"] + logo_cfg["h"] + 20
        
        # Wrap phone name to fit canvas width
        max_name_width = self.width - 80  # 40px margin on each side
        wrapped_name = self.wrap_text(phone_name[:40], self.fonts["title"], max_name_width)
        
        # Draw each line centered
        name_lines = wrapped_name.split('\n')
        for i, line in enumerate(name_lines):
            bbox = draw.textbbox((0, 0), line, font=self.fonts["title"])
            line_width = bbox[2] - bbox[0]
            x = (self.width - line_width) // 2
            y = name_y + (i * (CONFIG['fonts']['title'] + 5))
            text_color = (255, 255, 255, 255) if self.platform != "whatsapp" else (51, 51, 51, 255)
            draw.text((x, y), line, fill=text_color, font=self.fonts["title"])
        
        # Adjust phone position based on name height
        name_height = len(name_lines) * (CONFIG['fonts']['title'] + 5)
        phone_y_adjust = name_y + name_height + 30
        
        # Phone image
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                # Only remove background if it's mostly white
                phone_img = remove_background(phone_img)
                phone_cfg = self.layout["phone"]
                phone_img.thumbnail((phone_cfg["w"], phone_cfg["h"]), Image.Resampling.LANCZOS)
                
                x = phone_cfg["x"] + (phone_cfg["w"] - phone_img.width) // 2
                y = phone_y_adjust
                
                # Shadow
                shadow = Image.new('RGBA', (phone_img.width + 30, phone_img.height + 30), (0, 0, 0, 100))
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
                img.paste(shadow, (x - 15, y + 15), shadow)
                img.paste(phone_img, (x, y), phone_img)
                
                # Update content position for specs
                content_y = y + phone_img.height + 40
            else:
                content_y = phone_y_adjust + 100
        else:
            content_y = phone_y_adjust + 100
        
        # Content
        text_color = (255, 255, 255, 255) if self.platform != "whatsapp" else (51, 51, 51, 255)
        accent_color = tuple(int(CONFIG['brand']['gold'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        mint_color = tuple(int(CONFIG['brand']['mint'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        
        content_cfg = self.layout["content"]
        
        # Specs
        spec_cfg = self.layout["specs"]
        spec_list = [(k, v) for k, v in specs.items() if v != "N/A"]
        
        if self.platform == "whatsapp":
            # Two columns
            for i, (name, value) in enumerate(spec_list[:5]):
                col_x = spec_cfg["col1_x"] if i < 3 else spec_cfg["col2_x"]
                y = content_y + (i if i < 3 else i - 3) * spec_cfg["spacing"]
                
                icon_name = ["screen", "camera", "memory", "storage", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                img.paste(icon, (col_x - 55, y), icon)
                draw.text((col_x, y + 10), value, fill=text_color, font=self.fonts["body"], anchor="lm")
        
        elif self.platform == "instagram":
            # Horizontal
            for i, (name, value) in enumerate(spec_list[:4]):
                x = spec_cfg["start_x"] + i * spec_cfg["spacing"]
                icon_name = ["screen", "camera", "memory", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                img.paste(icon, (x, content_y), icon)
                draw.text((x + spec_cfg["icon_size"] // 2, content_y + spec_cfg["icon_size"] + 15),
                         value, fill=text_color, font=self.fonts["small"], anchor="mm")
        
        else:  # Facebook
            y = content_y
            for i, (name, value) in enumerate(spec_list[:5]):
                icon_name = ["screen", "camera", "memory", "storage", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                img.paste(icon, (content_cfg["x"], y), icon)
                draw.text((content_cfg["x"] + spec_cfg["icon_size"] + 20, y + 12),
                         value, fill=text_color, font=self.fonts["body"])
                y += spec_cfg["spacing"]
        
        # Price badge with better margins
        price_cfg = self.layout["price"]
        price_text = f"KES {format_price(price)}"
        
        # Calculate text width to adjust badge
        bbox = draw.textbbox((0, 0), price_text, font=self.fonts["price"])
        text_width = bbox[2] - bbox[0]
        
        # Adjust badge width to have good margins
        badge_width = max(price_cfg["w"], text_width + 80)  # 40px margin on each side
        
        # Center badge if needed
        if badge_width > price_cfg["w"]:
            badge_x = (self.width - badge_width) // 2
        else:
            badge_x = price_cfg["x"]
        
        # Use mint color for price badge
        price_bg = mint_color if self.platform != "whatsapp" else tuple(int(CONFIG['brand']['maroon'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        price_text_color = tuple(int(CONFIG['brand']['maroon'][i:i+2], 16) for i in (1, 3, 5)) + (255,) if self.platform != "whatsapp" else accent_color
        
        draw.rounded_rectangle(
            [badge_x, price_cfg["y"], badge_x + badge_width, price_cfg["y"] + price_cfg["h"]],
            radius=18, fill=price_bg
        )
        
        # Center text in badge
        draw.text((badge_x + (badge_width - text_width) // 2, price_cfg["y"] + 20),
                 price_text, fill=price_text_color, font=self.fonts["price"])
        
        # Footer with WhatsApp icon
        footer_y = self.layout["footer"]["y"]
        footer_color = accent_color if self.platform != "whatsapp" else tuple(int(CONFIG['brand']['maroon'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        
        # Add WhatsApp icon
        whatsapp_icon = get_whatsapp_icon(24)
        icon_x = self.width // 2 - 120
        img.paste(whatsapp_icon, (icon_x, footer_y - 12), whatsapp_icon)
        
        # Draw text with icon
        draw.text((icon_x + 30, footer_y),
                 f" {CONFIG['contact']['phone']} | {CONFIG['contact']['url']}",
                 fill=footer_color, font=self.fonts["small"], anchor="lm")
        
        return img

# ==========================================
# VIDEO GENERATOR (Real GIF)
# ==========================================

@st.cache_data(ttl=300, max_entries=3)
def create_video_frames(base_img: Image.Image, num_frames: int = 20) -> List[Image.Image]:
    """Create video frames with animations - cached"""
    frames = []
    
    for i in range(num_frames):
        frame = base_img.copy()
        
        # Simple zoom effect
        if i < num_frames // 2:
            scale = 1.0 + (i / num_frames) * 0.03
            new_size = (int(frame.width * scale), int(frame.height * scale))
            resized = frame.resize(new_size, Image.Resampling.LANCZOS)
            
            # Crop to center
            left = (resized.width - frame.width) // 2
            top = (resized.height - frame.height) // 2
            frame = resized.crop((left, top, left + frame.width, top + frame.height))
        
        frames.append(frame)
    
    return frames

@st.cache_data(ttl=300, max_entries=3)
def save_video_gif(_frames: List[Image.Image]) -> bytes:
    """Save as animated GIF - cached"""
    buf = BytesIO()
    _frames[0].save(
        buf,
        format='GIF',
        save_all=True,
        append_images=_frames[1:],
        duration=300,  # 300ms per frame = 6 seconds for 20 frames
        loop=0,
        optimize=True
    )
    return buf.getvalue()

# ==========================================
# MAIN APP
# ==========================================

def main():
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'phone' not in st.session_state:
        st.session_state.phone = None
    if 'ad' not in st.session_state:
        st.session_state.ad = None
    if 'video' not in st.session_state:
        st.session_state.video = None
    
    st.title("📱 Professional Phone Ad Generator")
    
    # Config Panel
    with st.expander("⚙️ Configuration", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Brand Colors:**")
            st.color_picker("Maroon", CONFIG['brand']['maroon'], key="cfg_maroon", disabled=True)
            st.color_picker("Gold", CONFIG['brand']['gold'], key="cfg_gold", disabled=True)
            st.color_picker("Mint", CONFIG['brand']['mint'], key="cfg_mint", disabled=True)
        with col2:
            st.markdown("**Contact:**")
            st.text_input("Phone", CONFIG['contact']['phone'], key="cfg_phone", disabled=True)
            st.text_input("Website", CONFIG['contact']['url'], key="cfg_url", disabled=True)
        
        st.info(f"🎨 Using Poppins font | 🖼️ Background removal: {'Simple method'}")
    
    st.markdown("---")
    
    # Main Interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1️⃣ Search Phone")
        query = st.text_input("Phone name", placeholder="e.g., Poco X3 Pro", key="search_query")
        
        if st.button("🔍 Search", use_container_width=True, key="search_btn"):
            if query:
                with st.spinner("Searching..."):
                    results = search_phone(query)
                    if results:
                        st.session_state.results = results
                        st.success(f"✅ {len(results)} phones found")
                    else:
                        st.error("❌ No results")
        
        if st.session_state.results:
            st.markdown("**Select a phone:**")
            for idx, phone in enumerate(st.session_state.results[:5]):
                if st.button(f"📱 {phone.get('name', 'Unknown')}", 
                           key=f"select_{idx}", 
                           use_container_width=True):
                    with st.spinner("Loading details..."):
                        details = get_phone_details(phone.get("id", ""))
                        if details:
                            st.session_state.phone = {
                                "name": phone.get('name', 'Unknown Phone'),
                                "specs": extract_specs(details),
                                "image": get_phone_image(phone.get("id", "")) or phone.get("image", "")
                            }
                            st.rerun()
    
    with col2:
        st.subheader("2️⃣ Generate Ad")
        
        if st.session_state.phone:
            phone = st.session_state.phone
            st.success(f"**{phone['name']}**")
            
            # Platform & Price
            platform = st.selectbox("Platform", ["facebook", "whatsapp", "instagram"], key="platform_select")
            price = st.text_input("Price (KES)", "45999", key="price_input")
            
            if st.button("✨ Generate Ad", type="primary", use_container_width=True, key="generate_btn"):
                with st.spinner("Creating ad..."):
                    try:
                        gen = AdGenerator(platform)
                        ad = gen.generate(phone['name'], phone['specs'], price, phone['image'])
                        st.session_state.ad = ad
                        st.session_state.platform = platform
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("👈 Select a phone first")
    
    # Display Ad
    if st.session_state.ad:
        st.markdown("---")
        st.subheader("✅ Your Ad")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.image(st.session_state.ad, use_container_width=True)
        
        with col2:
            # Download PNG
            buf_png = BytesIO()
            st.session_state.ad.save(buf_png, format='PNG')
            st.download_button(
                label="📥 PNG", 
                data=buf_png.getvalue(), 
                file_name="ad.png", 
                mime="image/png", 
                use_container_width=True,
                key="dl_png"
            )
            
            # Download JPEG
            buf_jpg = BytesIO()
            st.session_state.ad.convert('RGB').save(buf_jpg, format='JPEG', quality=95)
            st.download_button(
                label="📥 JPEG", 
                data=buf_jpg.getvalue(), 
                file_name="ad.jpg", 
                mime="image/jpeg", 
                use_container_width=True,
                key="dl_jpg"
            )
            
            # Generate Video
            if st.button("🎥 6s Video", use_container_width=True, key="video_btn"):
                with st.spinner("Creating video..."):
                    frames = create_video_frames(st.session_state.ad, 20)
                    video_data = save_video_gif(frames)
                    st.session_state.video = video_data
                    st.success("✅ Video ready!")
            
            # Download Video
            if st.session_state.video:
                st.download_button(
                    label="📥 GIF Video", 
                    data=st.session_state.video, 
                    file_name="ad_video.gif", 
                    mime="image/gif", 
                    use_container_width=True,
                    key="dl_video"
                )

if __name__ == "__main__":
    main()