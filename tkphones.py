"""
Professional Phone Ad Generator - Streamlined Version
With Config Panel, rembg, Poppins Font, RGBA, Layout Dictionary, Real Video
"""

import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageSequence
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
        "white": "#FFFFFF",
        "black": "#333333",
    },
    "contact": {
        "phone": "+254700123456",
        "url": "https://www.tripplek.co.ke",
        "location": "CBD Opposite MKU Towers"
    },
    "assets": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107",
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

# Layout Dictionary - Just change coordinates for different platforms
LAYOUTS = {
    "facebook": {
        "size": (1200, 630),
        "logo": {"x": 40, "y": 35, "w": 200, "h": 70},
        "phone": {"x": 80, "y": 80, "w": 550, "h": 550},
        "content": {"x": 680, "y": 100},
        "specs": {"start_y": 180, "spacing": 70, "icon_size": 52},
        "price": {"x": 680, "y": 470, "w": 400, "h": 85},
        "footer": {"y": 580},
        "bg_colors": ("#8B0000", "#4a0000")
    },
    "whatsapp": {
        "size": (1080, 1080),
        "logo": {"x": 50, "y": 50, "w": 200, "h": 70},
        "phone": {"x": 240, "y": 190, "w": 600, "h": 600},
        "content": {"x": 540, "y": 830},
        "specs": {"col1_x": 270, "col2_x": 810, "start_y": 830, "spacing": 65, "icon_size": 48},
        "price": {"x": 315, "y": 980, "w": 450, "h": 95},
        "footer": {"y": 1020},
        "bg_colors": ("#FFFFFF", "#FFFFFF"),
        "header_gradient": True
    },
    "instagram": {
        "size": (1080, 1350),
        "logo": {"x": 440, "y": 35, "w": 200, "h": 70},
        "phone": {"x": 190, "y": 130, "w": 700, "h": 700},
        "content": {"x": 540, "y": 870},
        "specs": {"start_x": 140, "y": 900, "spacing": 220, "icon_size": 65},
        "price": {"x": 290, "y": 1050, "w": 500, "h": 95},
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
    """Remove background using rembg or fallback"""
    if not REMBG_AVAILABLE:
        # Simple fallback
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        data = img.getdata()
        new_data = []
        for item in data:
            r, g, b = item[:3]
            a = item[3] if len(item) == 4 else 255
            if r > 240 and g > 240 and b > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        return img
    
    # Use rembg
    try:
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        output = rembg_remove(buf.read())
        result = Image.open(BytesIO(output))
        return result.convert('RGBA')
    except:
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
        
        # Load Poppins font
        try:
            self.fonts = {
                "title": ImageFont.truetype("poppins.ttf", CONFIG['fonts']['title']),
                "subtitle": ImageFont.truetype("poppins.ttf", CONFIG['fonts']['subtitle']),
                "body": ImageFont.truetype("poppins.ttf", CONFIG['fonts']['body']),
                "price": ImageFont.truetype("poppins.ttf", CONFIG['fonts']['price']),
                "small": ImageFont.truetype("poppins.ttf", CONFIG['fonts']['small'])
            }
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
        
        # Logo
        logo = download_image(CONFIG['assets']['logo'])
        if logo:
            logo_cfg = self.layout["logo"]
            logo.thumbnail((logo_cfg["w"], logo_cfg["h"]), Image.Resampling.LANCZOS)
            img.paste(logo, (logo_cfg["x"], logo_cfg["y"]), logo)
        
        # Phone image
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                phone_img = remove_background(phone_img)
                phone_cfg = self.layout["phone"]
                phone_img.thumbnail((phone_cfg["w"], phone_cfg["h"]), Image.Resampling.LANCZOS)
                
                x = phone_cfg["x"] + (phone_cfg["w"] - phone_img.width) // 2
                y = phone_cfg["y"] + (phone_cfg["h"] - phone_img.height) // 2
                
                # Shadow
                shadow = Image.new('RGBA', (phone_img.width + 30, phone_img.height + 30), (0, 0, 0, 100))
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
                img.paste(shadow, (x - 15, y + 15), shadow)
                img.paste(phone_img, (x, y), phone_img)
        
        # Content
        text_color = (255, 255, 255, 255) if self.platform != "whatsapp" else (51, 51, 51, 255)
        accent_color = tuple(int(CONFIG['brand']['gold'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        
        content_cfg = self.layout["content"]
        
        # Phone name
        draw.text((content_cfg["x"], content_cfg["y"]), phone_name[:30], 
                 fill=text_color, font=self.fonts["title"])
        
        # Specs
        spec_cfg = self.layout["specs"]
        spec_list = [(k, v) for k, v in specs.items() if v != "N/A"]
        
        if self.platform == "whatsapp":
            # Two columns
            for i, (name, value) in enumerate(spec_list[:5]):
                col_x = spec_cfg["col1_x"] if i < 3 else spec_cfg["col2_x"]
                y = spec_cfg["start_y"] + (i if i < 3 else i - 3) * spec_cfg["spacing"]
                
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
                img.paste(icon, (x, spec_cfg["y"]), icon)
                draw.text((x + spec_cfg["icon_size"] // 2, spec_cfg["y"] + spec_cfg["icon_size"] + 15),
                         value, fill=text_color, font=self.fonts["small"], anchor="mm")
        
        else:  # Facebook
            y = spec_cfg["start_y"]
            for i, (name, value) in enumerate(spec_list[:5]):
                icon_name = ["screen", "camera", "memory", "storage", "battery"][i]
                icon = get_icon(icon_name, spec_cfg["icon_size"])
                img.paste(icon, (content_cfg["x"], y), icon)
                draw.text((content_cfg["x"] + spec_cfg["icon_size"] + 20, y + 12),
                         value, fill=text_color, font=self.fonts["body"])
                y += spec_cfg["spacing"]
        
        # Price
        price_cfg = self.layout["price"]
        price_text = f"KES {format_price(price)}"
        
        price_bg = accent_color if self.platform != "whatsapp" else tuple(int(CONFIG['brand']['maroon'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        price_text_color = tuple(int(CONFIG['brand']['maroon'][i:i+2], 16) for i in (1, 3, 5)) + (255,) if self.platform != "whatsapp" else accent_color
        
        draw.rounded_rectangle(
            [price_cfg["x"], price_cfg["y"], price_cfg["x"] + price_cfg["w"], price_cfg["y"] + price_cfg["h"]],
            radius=18, fill=price_bg
        )
        
        bbox = draw.textbbox((0, 0), price_text, font=self.fonts["price"])
        text_w = bbox[2] - bbox[0]
        draw.text((price_cfg["x"] + (price_cfg["w"] - text_w) // 2, price_cfg["y"] + 22),
                 price_text, fill=price_text_color, font=self.fonts["price"])
        
        # Footer
        footer_y = self.layout["footer"]["y"]
        footer_color = accent_color if self.platform != "whatsapp" else tuple(int(CONFIG['brand']['maroon'][i:i+2], 16) for i in (1, 3, 5)) + (255,)
        draw.text((self.width // 2, footer_y),
                 f"📞 {CONFIG['contact']['phone']} | 🌐 {CONFIG['contact']['url']}",
                 fill=footer_color, font=self.fonts["small"], anchor="mm")
        
        return img

# ==========================================
# VIDEO GENERATOR (Real MP4/GIF)
# ==========================================

def create_video_frames(base_img: Image.Image, num_frames: int = 30) -> List[Image.Image]:
    """Create video frames with animations"""
    frames = []
    
    for i in range(num_frames):
        frame = base_img.copy()
        
        # Apply effects based on frame number
        progress = i / num_frames
        
        # Zoom effect (first half)
        if i < num_frames // 2:
            scale = 1.0 + (progress * 0.05)
            new_size = (int(frame.width * scale), int(frame.height * scale))
            frame = frame.resize(new_size, Image.Resampling.LANCZOS)
            # Crop to original
            left = (frame.width - base_img.width) // 2
            top = (frame.height - base_img.height) // 2
            frame = frame.crop((left, top, left + base_img.width, top + base_img.height))
        
        # Brightness pulse
        enhancer = ImageEnhance.Brightness(frame)
        brightness = 1.0 + 0.1 * abs(progress - 0.5)
        frame = enhancer.enhance(brightness)
        
        frames.append(frame)
    
    return frames

def save_video_gif(frames: List[Image.Image]) -> BytesIO:
    """Save as animated GIF"""
    buf = BytesIO()
    frames[0].save(
        buf,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=200,  # 200ms per frame = 6 seconds total for 30 frames
        loop=0
    )
    buf.seek(0)
    return buf

# ==========================================
# MAIN APP
# ==========================================

def main():
    st.title("📱 Professional Phone Ad Generator")
    
    # Config Panel (Collapsible)
    with st.expander("⚙️ Configuration", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Brand Colors:**")
            st.color_picker("Primary", CONFIG['brand']['maroon'], key="cfg_primary", disabled=True)
            st.color_picker("Accent", CONFIG['brand']['gold'], key="cfg_accent", disabled=True)
        with col2:
            st.markdown("**Contact:**")
            st.text_input("Phone", CONFIG['contact']['phone'], key="cfg_phone", disabled=True)
            st.text_input("Website", CONFIG['contact']['url'], key="cfg_url", disabled=True)
        
        st.info(f"🎨 Using Poppins font | 🖼️ rembg: {'✅ Active' if REMBG_AVAILABLE else '❌ Fallback'}")
    
    st.markdown("---")
    
    # Main Interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1️⃣ Search Phone")
        query = st.text_input("Phone name", placeholder="e.g., Poco X3 Pro")
        
        if st.button("🔍 Search", use_container_width=True):
            if query:
                with st.spinner("Searching..."):
                    results = search_phone(query)
                    if results:
                        st.session_state.results = results
                        st.success(f"✅ {len(results)} phones found")
                    else:
                        st.error("❌ No results")
        
        if 'results' in st.session_state:
            for idx, phone in enumerate(st.session_state.results[:5]):
                if st.button(f"📱 {phone.get('name')}", key=f"p_{idx}", use_container_width=True):
                    with st.spinner("Loading..."):
                        details = get_phone_details(phone.get("id", ""))
                        if details:
                            st.session_state.phone = {
                                "name": phone.get("name"),
                                "specs": extract_specs(details),
                                "image": get_phone_image(phone.get("id", "")) or phone.get("image", "")
                            }
                            st.rerun()
    
    with col2:
        st.subheader("2️⃣ Generate Ad")
        
        if 'phone' in st.session_state:
            phone = st.session_state.phone
            st.success(f"**{phone['name']}**")
            
            # Platform & Price
            platform = st.selectbox("Platform", ["facebook", "whatsapp", "instagram"])
            price = st.text_input("Price (KES)", "45999")
            
            if st.button("✨ Generate", type="primary", use_container_width=True):
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
    if 'ad' in st.session_state:
        st.markdown("---")
        st.subheader("✅ Your Ad")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.image(st.session_state.ad)
        
        with col2:
            # Download PNG
            buf_png = BytesIO()
            st.session_state.ad.save(buf_png, format='PNG')
            st.download_button("📥 PNG", buf_png.getvalue(), "ad.png", "image/png", use_container_width=True)
            
            # Download JPEG
            buf_jpg = BytesIO()
            st.session_state.ad.convert('RGB').save(buf_jpg, format='JPEG', quality=95)
            st.download_button("📥 JPEG", buf_jpg.getvalue(), "ad.jpg", "image/jpeg", use_container_width=True)
            
            # Generate Video
            if st.button("🎥 6s Video", use_container_width=True):
                with st.spinner("Creating video..."):
                    frames = create_video_frames(st.session_state.ad, 30)
                    video_gif = save_video_gif(frames)
                    st.session_state.video = video_gif.getvalue()
                    st.success("✅ Video ready!")
            
            # Download Video
            if 'video' in st.session_state:
                st.download_button("📥 GIF Video", st.session_state.video, "ad_video.gif", "image/gif", use_container_width=True)

if __name__ == "__main__":
    main()