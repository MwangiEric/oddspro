import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import numpy as np
import os

# Performance/MoviePy Setup
try:
    from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip
    from rembg import remove as rembg_remove
    MOVIEPY_AVAILABLE = True
    REMBG_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    REMBG_AVAILABLE = False

# ==========================================
# 1. PREMIUM CONFIGURATION
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

# ==========================================
# 2. ADVANCED MOTION ENGINE
# ==========================================
class AgencyMotion:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.num_particles = 45
        self.px = np.random.rand(self.num_particles) * width
        self.py = np.random.rand(self.num_particles) * height
        self.speed = np.random.rand(self.num_particles) * 15 + 5

    def get_bg_frame(self, t):
        # Shifting Maroon Gradient
        frame = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        c1 = np.array([139, 0, 0]) # Maroon
        c2 = np.array([60, 0, 0])  # Deep Dark Maroon
        shift = np.sin(t * 1.2) * 0.5 + 0.5
        curr_c = (c1 * (1 - shift) + c2 * shift).astype(np.uint8)
        
        for y in range(self.h):
            row_c = (curr_c * (1 - (y/self.h) * 0.4)).astype(np.uint8)
            frame[y, :] = row_c

        # Update and Draw Gold Particles
        for i in range(self.num_particles):
            self.py[i] = (self.py[i] - self.speed[i] * 0.1) % self.h
            self.px[i] = (self.px[i] + np.sin(t + i) * 0.5) % self.w
            ix, iy = int(self.px[i]), int(self.py[i])
            if 0 <= ix < self.w - 2 and 0 <= iy < self.h - 2:
                frame[iy:iy+2, ix:ix+2] = [255, 215, 0] # Gold Dust
        return frame

# ==========================================
# 3. CORE DESIGN ENGINE
# ==========================================
class ProAdEngine:
    def __init__(self, platform):
        self.plat = platform
        self.w, self.h = (1080, 1350) if platform == "instagram" else (1200, 630)
        try:
            self.f_t = ImageFont.truetype("Poppins-Bold.ttf", 65)
            self.f_p = ImageFont.truetype("Poppins-Bold.ttf", 55)
            self.f_s = ImageFont.truetype("Poppins-Medium.ttf", 34)
        except:
            self.f_t = ImageFont.load_default()
            self.f_p = ImageFont.load_default()
            self.f_s = ImageFont.load_default()

    def render(self, data, price):
        img = Image.new("RGBA", (self.w, self.h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # 1. Centered Logo (Increased size)
        logo = self.fetch_asset(CONFIG["assets"]["logo"])
        if logo:
            logo.thumbnail((450, 160), Image.LANCZOS)
            img.paste(logo, ((self.w - logo.width)//2, 60), logo)
            y = 240
        
        # 2. Wrapped Phone Name
        draw.text((self.w//2, y), data['name'].upper(), font=self.f_t, fill="white", anchor="mm")
        y += 80

        # 3. Phone Asset with Studio Shine
        p_img = self.fetch_asset(data['image'])
        if p_img:
            if REMBG_AVAILABLE: p_img = rembg_remove(p_img)
            p_img.thumbnail((700, 700), Image.LANCZOS)
            p_x, p_y = (self.w - p_img.width)//2, y
            img.paste(p_img, (p_x, p_y), p_img)
            
            # Studio Shine Overlay
            shine = Image.new("RGBA", p_img.size, (0,0,0,0))
            s_draw = ImageDraw.Draw(shine)
            s_draw.polygon([(0,0), (p_img.width//2, 0), (p_img.width//4, p_img.height), (0, p_img.height)], fill=(255,255,255,30))
            img.paste(shine, (p_x, p_y), shine)
            y += p_img.height + 50

        # 4. Specs Grid
        spec_x = self.w // 2 - 200
        for k, v in data['specs'].items():
            icon = self.fetch_asset(CONFIG["assets"]["icons"].get(k))
            if icon:
                icon.thumbnail((50, 50), Image.LANCZOS)
                img.paste(icon, (spec_x, y), icon)
                draw.text((spec_x + 75, y + 5), v, font=self.f_s, fill=CONFIG["brand"]["gold"])
                y += 65

        # 5. Dynamic Mint Price Badge
        y += 30
        p_txt = f"KES {price}"
        tw = draw.textlength(p_txt, font=self.f_p)
        bw, bx = tw + 120, (self.w - (tw + 120))//2
        draw.rounded_rectangle([bx, y, bx+bw, y+110], radius=30, fill=CONFIG["brand"]["mint"])
        draw.text((self.w//2, y + 55), p_txt, font=self.f_p, fill=CONFIG["brand"]["maroon"], anchor="mm")

        # 6. WhatsApp Footer
        wa = self.fetch_asset(CONFIG["assets"]["whatsapp"])
        wa.thumbnail((45, 45), Image.LANCZOS)
        f_txt = f"  {CONFIG['contact']['phone']}   |   {CONFIG['contact']['url']}"
        fx = (self.w - (draw.textlength(f_txt, font=self.f_s)+50))//2
        img.paste(wa, (int(fx), self.h - 90), wa)
        draw.text((fx + 55, self.h - 85), f_txt, font=self.f_s, fill="white")
        
        return img

    def fetch_asset(self, url):
        try:
            r = requests.get(url, timeout=10)
            return Image.open(BytesIO(r.content)).convert("RGBA")
        except: return None

# ==========================================
# 4. APP INTERFACE
# ==========================================
st.set_page_config(page_title="Tripple K Agency", layout="wide")
st.markdown("<style>.stButton>button{width:100%; background:#8B0000; color:white;}</style>", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = None

with st.sidebar:
    st.title("Step 1: Database")
    q = st.text_input("Search Phone")
    if st.button("Query GSM Database"):
        res = requests.get(f"{CONFIG['api_base']}/gsm/search?q={q}").json()
        if res:
            choice = st.selectbox("Select Model", res, format_func=lambda x: x['name'])
            det = requests.get(f"{CONFIG['api_base']}/gsm/info/{choice['id']}").json()
            st.session_state.data = {
                "name": choice['name'], "image": choice['image'],
                "specs": {"screen": det.get('display',{}).get('size','6.7"'), 
                          "camera": "Pro Camera System", "battery": "Fast Charge Battery"}
            }

if st.session_state.data:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Step 2: Ad Customization")
        price = st.text_input("Offer Price", "95,000")
        plat = st.selectbox("Format", ["instagram", "facebook"])
        if st.button("Generate Agency Kit"):
            engine = ProAdEngine(plat)
            st.session_state.img = engine.render(st.session_state.data, price)

    if 'img' in st.session_state:
        with c2:
            st.image(st.session_state.img)
            buf = BytesIO(); st.session_state.img.save(buf, format="PNG")
            st.download_button("📥 Save High-Res PNG", buf.getvalue(), "ad.png")
            
            if MOVIEPY_AVAILABLE:
                if st.button("🎥 Render Cinematic MP4"):
                    with st.spinner("Executing Physics & Motion..."):
                        motion = AgencyMotion(st.session_state.img.width, st.session_state.img.height)
                        bg_clip = VideoClip(lambda t: motion.get_bg_frame(t), duration=5)
                        fg_array = np.array(st.session_state.img)
                        fg_clip = ImageClip(fg_array).set_duration(5).set_position('center')
                        fg_clip = fg_clip.resize(lambda t: 1 + 0.01*(t**1.5)).crossfadein(0.8)
                        
                        final = CompositeVideoClip([bg_clip, fg_clip], size=st.session_state.img.size)
                        final.write_videofile("out.mp4", fps=24, codec="libx264", logger=None)
                        st.download_button("🎥 Download Agency Video", open("out.mp4","rb"), "promo.mp4")
