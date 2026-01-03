import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import numpy as np
import re
import os

# Try to import moviepy
try:
    from moviepy.editor import ImageClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# Try to import rembg
try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# ==========================================
# CONFIG & ASSETS
# ==========================================
CONFIG = {
    "brand": {"maroon": "#8B0000", "gold": "#FFD700", "mint": "#3EB489", "white": "#FFFFFF"},
    "contact": {"phone": "+254 700 123 456", "url": "www.tripplek.co.ke"},
    "api_base": "https://tkphsp2.vercel.app",
    "assets": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107",
        "whatsapp": "https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg",
        "icons": {
            "screen": "https://img.icons8.com/ios-filled/100/ffffff/touchscreen.png",
            "camera": "https://img.icons8.com/ios-filled/100/ffffff/camera.png",
            "battery": "https://img.icons8.com/ios-filled/100/ffffff/battery--v1.png",
            "memory": "https://img.icons8.com/ios-filled/100/ffffff/memory-slot.png"
        }
    }
}

LAYOUTS = {
    "instagram": {"size": (1080, 1350), "logo_w": 450, "phone_w": 650, "y_start": 60},
    "facebook": {"size": (1200, 630), "logo_w": 380, "phone_w": 450, "y_start": 30}
}

# ==========================================
# UTILS & API
# ==========================================
def get_img(url):
    try:
        resp = requests.get(url, timeout=10)
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    except: return None

def api_call(path):
    try:
        r = requests.get(f"{CONFIG['api_base']}{path}", timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def clean_img(img):
    if REMBG_AVAILABLE: return rembg_remove(img)
    return img

# ==========================================
# GENERATOR ENGINE
# ==========================================
class ProAdEngine:
    def __init__(self, platform):
        self.L = LAYOUTS[platform]
        self.w, self.h = self.L["size"]
        try:
            self.f_t = ImageFont.truetype("Poppins-Bold.ttf", 60)
            self.f_p = ImageFont.truetype("Poppins-Bold.ttf", 55)
            self.f_s = ImageFont.truetype("Poppins-Medium.ttf", 32)
        except:
            self.f_t = ImageFont.load_default()
            self.f_p = ImageFont.load_default()
            self.f_s = ImageFont.load_default()

    def render(self, data, price):
        # 1. Base
        img = Image.new("RGBA", (self.w, self.h), CONFIG["brand"]["maroon"])
        draw = ImageDraw.Draw(img)
        
        # 2. Logo
        logo = get_img(CONFIG["assets"]["logo"])
        if logo:
            logo.thumbnail((self.L["logo_w"], 150), Image.LANCZOS)
            img.paste(logo, ((self.w - logo.width)//2, self.L["y_start"]), logo)
            y = self.L["y_start"] + logo.height + 40
        
        # 3. Centered Title
        draw.text((self.w//2, y), data['name'].upper(), font=self.f_t, fill="white", anchor="mm")
        y += 60

        # 4. Phone Asset
        p_img = get_img(data['image'])
        if p_img:
            p_img = clean_img(p_img)
            p_img.thumbnail((self.L["phone_w"], self.L["phone_w"]), Image.LANCZOS)
            img.paste(p_img, ((self.w - p_img.width)//2, y), p_img)
            y += p_img.height + 40

        # 5. Specs Icons
        spec_x = self.w // 2 - 180
        for icon_name, val in data['specs'].items():
            icon = get_img(CONFIG["assets"]["icons"].get(icon_name))
            if icon and val != "N/A":
                icon.thumbnail((45, 45), Image.LANCZOS)
                img.paste(icon, (spec_x, y), icon)
                draw.text((spec_x + 65, y + 5), val, font=self.f_s, fill=CONFIG["brand"]["gold"])
                y += 55

        # 6. Mint Badge
        y += 20
        p_txt = f"KES {price}"
        tw = draw.textlength(p_txt, font=self.f_p)
        bw, bh = tw + 100, 100
        bx = (self.w - bw)//2
        draw.rounded_rectangle([bx, y, bx+bw, y+bh], radius=25, fill=CONFIG["brand"]["mint"])
        draw.text((self.w//2, y + 50), p_txt, font=self.f_p, fill=CONFIG["brand"]["maroon"], anchor="mm")

        # 7. WhatsApp Footer
        wa = get_img(CONFIG["assets"]["whatsapp"])
        wa.thumbnail((35, 35), Image.LANCZOS)
        f_txt = f"  {CONFIG['contact']['phone']}   |   {CONFIG['contact']['url']}"
        fw = draw.textlength(f_txt, font=self.f_s) + 40
        fx = (self.w - fw)//2
        img.paste(wa, (int(fx), self.h - 85), wa)
        draw.text((fx + 45, self.h - 80), f_txt, font=self.f_s, fill="white")
        
        return img

# ==========================================
# STREAMLIT INTERFACE
# ==========================================
st.set_page_config(page_title="Tripple K Pro", layout="wide")
st.title("📱 Tripple K Ad & Video Suite")

if 'phone_data' not in st.session_state: st.session_state.phone_data = None

# Sidebar Search (Restoring Original Feature)
with st.sidebar:
    st.header("1. Search Device")
    query = st.text_input("Model Name", placeholder="e.g. S24 Ultra")
    if st.button("Search GSM Database"):
        results = api_call(f"/gsm/search?q={query}")
        if results:
            choice = st.selectbox("Select Model", results, format_func=lambda x: x['name'])
            details = api_call(f"/gsm/info/{choice['id']}")
            # Basic parsing from original logic
            st.session_state.phone_data = {
                "name": choice['name'],
                "image": choice['image'],
                "specs": {
                    "screen": details.get('display', {}).get('size', 'N/A'),
                    "camera": "Main Camera" if details.get('mainCamera') else "N/A",
                    "battery": details.get('battery', {}).get('battType', 'N/A')
                }
            }
            st.success("Loaded Specs!")

# Main Column
if st.session_state.phone_data:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("2. Final Adjustments")
        platform = st.selectbox("Platform", ["instagram", "facebook"])
        price = st.text_input("Price (KES)", "85,000")
        
        if st.button("🚀 Generate Marketing Kit", type="primary"):
            engine = ProAdEngine(platform)
            final_ad = engine.render(st.session_state.phone_data, price)
            st.session_state.current_ad = final_ad

    if 'current_ad' in st.session_state:
        with col2:
            st.image(st.session_state.current_ad)
            
            # Downloads
            buf = BytesIO()
            st.session_state.current_ad.save(buf, format="PNG")
            st.download_button("📥 Download PNG", buf.getvalue(), "ad.png")
            
            if MOVIEPY_AVAILABLE:
                if st.button("🎥 Create Cinematic MP4"):
                    with st.spinner("Rendering 24fps Video..."):
                        frame = np.array(st.session_state.current_ad.convert("RGB"))
                        clip = ImageClip(frame).set_duration(5)
                        clip = clip.resize(lambda t: 1 + 0.05 * t)
                        clip.write_videofile("promo.mp4", fps=24, codec="libx264", logger=None)
                        with open("promo.mp4", "rb") as f:
                            st.download_button("📥 Download Video", f.read(), "promo.mp4")
