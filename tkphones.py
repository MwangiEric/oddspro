"""
Professional Phone Ad Generator - Streamlined Version
Fixed: No overlap, better phone images, real MP4 video
"""

import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import Optional, Dict, List
import re
import os
import tempfile
import base64

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG = {
    "brand": {
        "maroon": "#8B0000",
        "gold": "#FFD700",
        "accent": "#FF6B35",
        "mint": "#3EB489",
        "white": "#FFFFFF",
        "black": "#333333",
        "shadow": "#2C2C2C",
    },
    "contact": {
        "phone": "+254700123456",
        "url": "www.tripplek.co.ke",
        "location": "CBD Opposite MKU Towers"
    },
    "assets": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107",
        "whatsapp_icon": "https://cdn-icons-png.flaticon.com/512/124/124034.png",
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
        "title": 48,
        "subtitle": 36,
        "body": 30,
        "price": 44,
        "small": 24
    }
}

# Improved Layout Dictionary with spacing
LAYOUTS = {
    "facebook": {
        "size": (1200, 630),
        "logo": {"x": 40, "y": 30, "w": 250, "h": 90},
        "phone": {"x": 60, "y": 180, "w": 500, "h": 400},
        "content": {"x": 650, "y": 140},
        "specs": {"start_y": 220, "spacing": 65, "icon_size": 48},
        "price": {"x": 650, "y": 470, "w": 380, "h": 75},
        "footer": {"y": 590},
        "bg_colors": ("#8B0000", "#4a0000")
    },
    "whatsapp": {
        "size": (1080, 1080),
        "logo": {"x": 50, "y": 40, "w": 250, "h": 90},
        "phone": {"x": 240, "y": 220, "w": 600, "h": 450},
        "content": {"x": 540, "y": 700},
        "specs": {"col1_x": 270, "col2_x": 810, "start_y": 720, "spacing": 60, "icon_size": 44},
        "price": {"x": 315, "y": 920, "w": 400, "h": 75},
        "footer": {"y": 1010},
        "bg_colors": ("#FFFFFF", "#FFFFFF"),
        "header_gradient": True
    },
    "instagram": {
        "size": (1080, 1350),
        "logo": {"x": 415, "y": 30, "w": 250, "h": 90},
        "phone": {"x": 140, "y": 180, "w": 800, "h": 500},
        "content": {"x": 540, "y": 720},
        "specs": {"start_x": 140, "y": 750, "spacing": 200, "icon_size": 60},
        "price": {"x": 290, "y": 950, "w": 450, "h": 80},
        "footer": {"y": 1280},
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

def enhance_phone_image(img: Image.Image) -> Image.Image:
    """Enhance phone image with shadow border (NO background removal)"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Resize to optimal size
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    
    # Add subtle glow effect
    glow = img.copy()
    glow = glow.filter(ImageFilter.GaussianBlur(radius=5))
    
    # Create new image with glow
    result = Image.new('RGBA', (img.width + 40, img.height + 40), (0, 0, 0, 0))
    result.paste(glow, (20, 20), glow)
    result.paste(img, (20, 20), img)
    
    return result

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
        font = ImageFont.truetype("arialbd.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    draw.text((size//2, size//2), name[0].upper(), fill="white", font=font, anchor="mm")
    return img

def get_whatsapp_icon(size: int = 28) -> Image.Image:
    """Get WhatsApp icon"""
    icon = download_image(CONFIG['assets']['whatsapp_icon'])
    if icon:
        icon = icon.resize((size, size), Image.Resampling.LANCZOS)
        return icon
    
    # Fallback
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill="#25D366")
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
        specs["Screen"] = f"{match.group(1)}″" if match else "N/A"
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
                specs["RAM"] = f"{ram_match.group(1)}GB"
            
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
# AD GENERATOR - NO OVERLAP
# ==========================================

class AdGenerator:
    """Generate ads with proper spacing"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.layout = LAYOUTS[platform]
        self.width, self.height = self.layout["size"]
        
        # Load fonts
        self.fonts = {}
        try:
            self.fonts["title"] = ImageFont.truetype("arialbd.ttf", CONFIG['fonts']['title'])
            self.fonts["subtitle"] = ImageFont.truetype("arialbd.ttf", CONFIG['fonts']['subtitle'])
            self.fonts["body"] = ImageFont.truetype("arial.ttf", CONFIG['fonts']['body'])
            self.fonts["price"] = ImageFont.truetype("arialbd.ttf", CONFIG['fonts']['price'])
            self.fonts["small"] = ImageFont.truetype("arial.ttf", CONFIG['fonts']['small'])
        except:
            default = ImageFont.load_default()
            self.fonts = {k: default for k in ["title", "subtitle", "body", "price", "small"]}
    
    def create_gradient(self, color1: str, color2: str) -> Image.Image:
        """Create gradient background"""
        img = Image.new('RGB', (self.width, self.height), color1)
        draw = ImageDraw.Draw(img)
        
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        
        for y in range(self.height):
            factor = y / self.height
            r = int(r1 * (1 - factor) + r2 * factor)
            g = int(g1 * (1 - factor) + g2 * factor)
            b = int(b1 * (1 - factor) + b2 * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def generate(self, phone_name: str, specs: Dict, price: str, phone_img_url: str) -> Image.Image:
        """Generate ad with proper spacing"""
        
        # Create background
        if self.platform == "whatsapp":
            img = Image.new('RGB', (self.width, self.height), "white")
            draw = ImageDraw.Draw(img)
            
            # Header gradient for WhatsApp
            if self.layout.get("header_gradient"):
                for y in range(160):
                    factor = y / 160
                    r = int(139 * (1 - factor) + 255 * factor)
                    draw.line([(0, y), (self.width, y)], fill=(r, 0, 0))
        else:
            img = self.create_gradient(*self.layout["bg_colors"])
            draw = ImageDraw.Draw(img)
        
        # Logo
        logo = download_image(CONFIG['assets']['logo'])
        if logo:
            logo_cfg = self.layout["logo"]
            logo.thumbnail((logo_cfg["w"], logo_cfg["h"]), Image.Resampling.LANCZOS)
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            img.paste(logo, (logo_cfg["x"], logo_cfg["y"]), logo)
        
        # Phone name centered below logo
        logo_cfg = self.layout["logo"]
        name_y = logo_cfg["y"] + logo_cfg["h"] + 15
        
        # Truncate phone name if too long
        display_name = phone_name[:30] + "..." if len(phone_name) > 30 else phone_name
        
        # Get text width
        bbox = draw.textbbox((0, 0), display_name, font=self.fonts["title"])
        text_width = bbox[2] - bbox[0]
        
        # Center the text
        x = (self.width - text_width) // 2
        
        # Choose text color based on platform
        text_color = "white" if self.platform != "whatsapp" else CONFIG['brand']['maroon']
        draw.text((x, name_y), display_name, fill=text_color, font=self.fonts["title"])
        
        # Phone image with creative shadow border
        phone_cfg = self.layout["phone"]
        phone_y = name_y + 80  # Space after name
        
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                # Enhance image (no background removal)
                phone_img = enhance_phone_image(phone_img)
                
                # Fit within layout bounds
                phone_img.thumbnail((phone_cfg["w"], phone_cfg["h"]), Image.Resampling.LANCZOS)
                
                # Center the phone
                x = phone_cfg["x"] + (phone_cfg["w"] - phone_img.width) // 2
                y = phone_y
                
                # Creative shadow border
                border_size = 30
                border_img = Image.new('RGBA', 
                    (phone_img.width + border_size, phone_img.height + border_size), 
                    (0, 0, 0, 0))
                
                # Draw gradient border
                border_draw = ImageDraw.Draw(border_img)
                for i in range(border_size):
                    alpha = int(100 * (1 - i/border_size))
                    border_draw.rectangle(
                        [i, i, phone_img.width + border_size - i, phone_img.height + border_size - i],
                        outline=(139, 0, 0, alpha),
                        width=1
                    )
                
                # Paste phone on border
                border_img.paste(phone_img, (border_size//2, border_size//2), phone_img)
                
                # Apply blur for shadow effect
                shadow = border_img.filter(ImageFilter.GaussianBlur(radius=3))
                
                # Paste shadow then phone
                img.paste(shadow, (x - border_size//2, y + 5), shadow)
                img.paste(border_img, (x - border_size//2, y), border_img)
                
                # Update specs position
                specs_y = y + phone_img.height + 60
            else:
                specs_y = phone_y + 100
        else:
            specs_y = phone_y + 100
        
        # Content colors
        text_color = "white" if self.platform != "whatsapp" else "#333333"
        price_bg_color = CONFIG['brand']['mint'] if self.platform != "whatsapp" else CONFIG['brand']['maroon']
        price_text_color = "white" if self.platform != "whatsapp" else CONFIG['brand']['gold']
        
        # Specs
        spec_list = [(k, v) for k, v in specs.items() if v != "N/A"]
        spec_cfg = self.layout["specs"]
        
        if self.platform == "whatsapp":
            # Two columns
            for i, (name, value) in enumerate(spec_list[:5]):
                col_x = spec_cfg["col1_x"] if i < 3 else spec_cfg["col2_x"]
                y = specs_y + (i if i < 3 else i - 3) * spec_cfg["spacing"]
                
                icon_name = ["screen", "camera", "memory", "storage", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                if icon.mode != 'RGBA':
                    icon = icon.convert('RGBA')
                img.paste(icon, (col_x - 50, y), icon)
                draw.text((col_x, y + 8), value, fill=text_color, font=self.fonts["body"], anchor="lm")
        
        elif self.platform == "instagram":
            # Horizontal specs
            for i, (name, value) in enumerate(spec_list[:4]):
                x = spec_cfg["start_x"] + i * spec_cfg["spacing"]
                icon_name = ["screen", "camera", "memory", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                if icon.mode != 'RGBA':
                    icon = icon.convert('RGBA')
                img.paste(icon, (x, specs_y), icon)
                
                # Center text below icon
                text_bbox = draw.textbbox((0, 0), value, font=self.fonts["small"])
                text_width = text_bbox[2] - text_bbox[0]
                draw.text((x + spec_cfg["icon_size"]//2, specs_y + spec_cfg["icon_size"] + 20),
                         value, fill=text_color, font=self.fonts["small"], anchor="mm")
        
        else:  # Facebook
            # Vertical specs
            y = specs_y
            for i, (name, value) in enumerate(spec_list[:5]):
                icon_name = ["screen", "camera", "memory", "storage", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                if icon.mode != 'RGBA':
                    icon = icon.convert('RGBA')
                img.paste(icon, (self.layout["content"]["x"], y), icon)
                draw.text((self.layout["content"]["x"] + spec_cfg["icon_size"] + 15, y + 10),
                         value, fill=text_color, font=self.fonts["body"])
                y += spec_cfg["spacing"]
        
        # Price badge with good margins
        price_cfg = self.layout["price"]
        price_text = f"KES {format_price(price)}"
        
        # Calculate text size for proper margins
        price_bbox = draw.textbbox((0, 0), price_text, font=self.fonts["price"])
        price_text_width = price_bbox[2] - price_bbox[0]
        
        # Add margins (40px on each side)
        badge_width = max(price_cfg["w"], price_text_width + 80)
        
        # Center badge if too wide
        if badge_width > price_cfg["w"]:
            badge_x = (self.width - badge_width) // 2
        else:
            badge_x = price_cfg["x"]
        
        # Draw badge
        draw.rounded_rectangle(
            [badge_x, price_cfg["y"], badge_x + badge_width, price_cfg["y"] + price_cfg["h"]],
            radius=15,
            fill=price_bg_color
        )
        
        # Center text in badge
        draw.text((badge_x + (badge_width - price_text_width) // 2, price_cfg["y"] + 18),
                 price_text, fill=price_text_color, font=self.fonts["price"])
        
        # Footer with WhatsApp icon
        footer_y = self.layout["footer"]["y"]
        footer_color = CONFIG['brand']['gold'] if self.platform != "whatsapp" else CONFIG['brand']['maroon']
        
        # WhatsApp icon
        whatsapp_icon = get_whatsapp_icon(26)
        if whatsapp_icon.mode != 'RGBA':
            whatsapp_icon = whatsapp_icon.convert('RGBA')
        
        # Center footer
        footer_text = f"{CONFIG['contact']['phone']} | {CONFIG['contact']['url']}"
        text_bbox = draw.textbbox((0, 0), footer_text, font=self.fonts["small"])
        text_width = text_bbox[2] - text_bbox[0]
        
        # Calculate total width with icon
        total_width = text_width + 35  # Icon width + spacing
        
        # Start position for centered content
        start_x = (self.width - total_width) // 2
        
        # Paste icon
        img.paste(whatsapp_icon, (start_x, footer_y - 13), whatsapp_icon)
        
        # Draw text
        draw.text((start_x + 30, footer_y), footer_text, 
                 fill=footer_color, font=self.fonts["small"], anchor="lm")
        
        return img.convert('RGB')

# ==========================================
# VIDEO GENERATOR (MP4 with moviepy)
# ==========================================

try:
    import numpy as np
    from moviepy.editor import ImageSequenceClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    st.warning("⚠️ moviepy not installed. Install with: pip install moviepy")

@st.cache_data(ttl=300, max_entries=3)
def create_mp4_video(ad_image: Image.Image, duration: int = 6) -> bytes:
    """Create MP4 video with zoom effect"""
    if not MOVIEPY_AVAILABLE:
        return None
    
    try:
        frames = []
        num_frames = 30  # For smooth 30fps
        
        for i in range(num_frames):
            frame = ad_image.copy()
            
            # Gentle zoom effect
            progress = i / num_frames
            if progress < 0.5:
                # Zoom in slightly
                scale = 1.0 + (progress * 0.04)
                new_width = int(frame.width * scale)
                new_height = int(frame.height * scale)
                
                # Resize
                resized = frame.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Crop back to original size
                left = (new_width - frame.width) // 2
                top = (new_height - frame.height) // 2
                frame = resized.crop((left, top, left + frame.width, top + frame.height))
            
            # Convert to numpy array for moviepy
            frame_np = np.array(frame)
            frames.append(frame_np)
        
        # Create video clip
        fps = num_frames / duration  # Calculate FPS for exact duration
        clip = ImageSequenceClip(frames, fps=fps)
        
        # Save to bytes
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        clip.write_videofile(temp_file.name, codec='libx264', audio=False, verbose=False, logger=None)
        
        # Read bytes
        with open(temp_file.name, 'rb') as f:
            video_bytes = f.read()
        
        # Clean up
        os.unlink(temp_file.name)
        
        return video_bytes
        
    except Exception as e:
        print(f"Video creation error: {e}")
        return None

@st.cache_data(ttl=300, max_entries=3)
def create_gif_video(ad_image: Image.Image) -> bytes:
    """Fallback GIF creation"""
    frames = []
    num_frames = 15
    
    for i in range(num_frames):
        frame = ad_image.copy()
        
        # Simple brightness pulse
        if i < num_frames // 2:
            brightness = 1.0 + (i / num_frames) * 0.1
        else:
            brightness = 1.1 - ((i - num_frames//2) / num_frames) * 0.1
        
        # Apply brightness (simple way)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(frame)
        frame = enhancer.enhance(brightness)
        
        frames.append(frame)
    
    # Save GIF
    buf = BytesIO()
    frames[0].save(
        buf,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=200,
        loop=0,
        optimize=True
    )
    return buf.getvalue()

# ==========================================
# MAIN APP
# ==========================================

def main():
    # Initialize session state
    for key in ['results', 'phone', 'ad', 'video', 'video_type']:
        if key not in st.session_state:
            st.session_state[key] = None
    
    st.title("📱 Professional Phone Ad Generator")
    
    # Config Panel
    with st.expander("⚙️ Configuration", expanded=False):
        st.info(f"🎨 Using mint color for price badges")
        if not MOVIEPY_AVAILABLE:
            st.warning("⚠️ Install moviepy for MP4 videos: `pip install moviepy`")
    
    st.markdown("---")
    
    # Main Interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1️⃣ Search Phone")
        query = st.text_input("Phone name", placeholder="e.g., Poco X3 Pro", key="search_query")
        
        if st.button("🔍 Search", use_container_width=True, key="search_btn"):
            if query and len(query.strip()) > 1:
                with st.spinner("Searching..."):
                    results = search_phone(query)
                    if results:
                        st.session_state.results = results
                        st.success(f"✅ Found {len(results)} phones")
                    else:
                        st.error("❌ No results found")
            else:
                st.warning("Enter at least 2 characters")
        
        if st.session_state.results:
            st.markdown("**Select a phone:**")
            for idx, phone in enumerate(st.session_state.results[:5]):
                phone_name = phone.get('name', 'Unknown Phone')
                if st.button(f"📱 {phone_name[:40]}", 
                           key=f"select_{idx}", 
                           use_container_width=True):
                    with st.spinner("Loading details..."):
                        details = get_phone_details(phone.get("id", ""))
                        if details:
                            st.session_state.phone = {
                                "name": phone_name,
                                "specs": extract_specs(details),
                                "image": get_phone_image(phone.get("id", "")) or phone.get("image", "")
                            }
                            st.rerun()
    
    with col2:
        st.subheader("2️⃣ Generate Ad")
        
        if st.session_state.phone:
            phone = st.session_state.phone
            st.success(f"**{phone['name']}**")
            
            # Display specs
            with st.expander("📊 Phone Specs", expanded=True):
                for key, value in phone['specs'].items():
                    if value != "N/A":
                        st.write(f"**{key}:** {value}")
            
            # Platform & Price
            col_a, col_b = st.columns(2)
            with col_a:
                platform = st.selectbox("Platform", ["facebook", "whatsapp", "instagram"])
            with col_b:
                price = st.text_input("Price (KES)", "45,999")
            
            if st.button("✨ Generate Ad", type="primary", use_container_width=True):
                with st.spinner("Creating ad..."):
                    try:
                        gen = AdGenerator(platform)
                        ad = gen.generate(phone['name'], phone['specs'], price, phone['image'])
                        st.session_state.ad = ad
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            st.info("👈 Search and select a phone first")
    
    # Display Ad
    if st.session_state.ad:
        st.markdown("---")
        st.subheader("✅ Your Ad")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.image(st.session_state.ad, use_container_width=True)
        
        with col2:
            # Download options
            buf_png = BytesIO()
            st.session_state.ad.save(buf_png, format='PNG')
            
            st.download_button(
                label="📥 Download PNG", 
                data=buf_png.getvalue(), 
                file_name="phone_ad.png", 
                mime="image/png", 
                use_container_width=True
            )
            
            # Video generation
            if MOVIEPY_AVAILABLE:
                if st.button("🎬 Create 6s MP4 Video", use_container_width=True):
                    with st.spinner("Rendering video..."):
                        video_data = create_mp4_video(st.session_state.ad, 6)
                        if video_data:
                            st.session_state.video = video_data
                            st.session_state.video_type = "mp4"
                            st.success("✅ MP4 video ready!")
                        else:
                            st.error("Failed to create video")
            else:
                if st.button("🎬 Create 6s GIF Video", use_container_width=True):
                    with st.spinner("Creating GIF..."):
                        video_data = create_gif_video(st.session_state.ad)
                        st.session_state.video = video_data
                        st.session_state.video_type = "gif"
                        st.success("✅ GIF video ready!")
            
            # Download video if available
            if st.session_state.video:
                if st.session_state.video_type == "mp4":
                    st.download_button(
                        label="📥 Download MP4", 
                        data=st.session_state.video, 
                        file_name="phone_ad.mp4", 
                        mime="video/mp4", 
                        use_container_width=True
                    )
                else:
                    st.download_button(
                        label="📥 Download GIF", 
                        data=st.session_state.video, 
                        file_name="phone_ad.gif", 
                        mime="image/gif", 
                        use_container_width=True
                    )
            
            # Clear button
            if st.button("🔄 Clear & Start Over", use_container_width=True):
                for key in ['ad', 'video', 'video_type']:
                    st.session_state[key] = None
                st.rerun()

if __name__ == "__main__":
    main()