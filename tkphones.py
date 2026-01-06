import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import numpy as np
from moviepy.editor import VideoClip
import os

# ==========================================
# 1. GLOBAL CONFIGURATION
# ==========================================
CONFIG = {
    "brand_name": "TRIPPLE K AGENCY",
    "colors": {
        "bg": "#0F0A0A",
        "mint": "#3EB489",
        "white": "#FFFFFF",
        "gold": "#C5A059",
        "blue": "#1DA1F2" 
    },
    "icons": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107",
        "processor": "https://ik.imagekit.io/ericmwangi/processor.png",
        "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
        "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
        "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
        "battery": "https://ik.imagekit.io/ericmwangi/battery.png",
        "whatsapp": "https://ik.imagekit.io/ericmwangi/whatsapp.png",
        "location": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
        "web": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png"
    },
    "contact_info": {
        "whatsapp": "+254 700 123 456",
        "location": "CBD, Opposite MKU Towers",
        "web": "www.tripplek.co.ke"
    },
    "layouts": {
        "whatsapp": {
            "canvas": (1080, 1080),
            "logo_pos": (50, 50),
            "logo_size": (200, 70),
            "title_pos": (280, 65),
            "phone_box": [60, 200, 620, 950],
            "spec_start": (680, 250),
            "spec_gap": 100,
            "price_box": [680, 800, 1000, 880],
            "footer_y": 1020
        },
        "tiktok": {
            "canvas": (1080, 1920),
            "logo_pos": (390, 80),
            "logo_size": (300, 110),
            "title_pos": (540, 220),
            "phone_box": [140, 350, 940, 1250],
            "spec_start": (200, 1300),
            "spec_gap": 80,
            "price_box": [200, 1720, 880, 1810],
            "footer_y": 1850
        }
    }
}

# ==========================================
# 2. DATA FETCHING (GSMARENA API)
# ==========================================
def fetch_data(q):
    try:
        # Step 1: Search for the device
        s_res = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={q}", timeout=10).json()
        if not s_res: return None
        device_id = s_res[0]['id']
        
        # Step 2: Fetch detailed info and images
        info = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{device_id}", timeout=10).json()
        imgs = requests.get(f"https://tkphsp2.vercel.app/gsm/images/{device_id}", timeout=10).json()
        
        # Parse Chipset
        chip = info.get("platform", {}).get("chipset", "High Performance").split('(')[0].strip()
        
        # Parse Battery (e.g., "5000 mAh")
        raw_batt = info.get("battery", {}).get("battType", "5000")
        batt_clean = raw_batt.split('mAh')[0].strip().split(' ')[-1] + " mAh"
        
        # Parse Memory (e.g., "128GB 8GB RAM")
        mem_raw = info.get("memory", {}).get("internal", "Standard").split(',')[0].strip()
        
        # Image Selection
        img_url = imgs.get('images', [])[1] if len(imgs.get('images', [])) > 1 else s_res[0]['image']
        
        return {
            "name": s_res[0]['name'], 
            "image_url": img_url, 
            "specs": [
                ("processor", chip),
                ("screen", info.get("display", {}).get("size", "6.7\"").split(' ')[0] + " Display"),
                ("camera", info.get("mainCamera", {}).get("mainModules", "50MP").split(',')[0]),
                ("memory", mem_raw),
                ("battery", batt_clean)
            ]
        }
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

# ==========================================
# 3. ENGINE & VIDEO GENERATION
# ==========================================
@st.cache_data
def load_and_tint(url, color=None):
    try:
        res = requests.get(url, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGBA")
        if color:
            r, g, b, a = img.split()
            target = Image.new("RGB", img.size, color)
            tr, tg, tb = target.split()
            img = Image.merge("RGBA", (tr, tg, tb, a))
        return img
    except: return Image.new("RGBA", (100, 100), (0,0,0,0))

class AdEngine:
    def build_ad(self, mode, data, price, t=None):
        cfg = CONFIG["layouts"][mode]
        canvas = Image.new("RGB", cfg["canvas"], CONFIG["colors"]["bg"])
        draw = ImageDraw.Draw(canvas)

        # 1. Phone Card Shadow & Box
        box = cfg["phone_box"]
        draw.rounded_rectangle(box, radius=25, fill="white", outline=CONFIG["colors"]["gold"], width=5)

        # 2. Paste Phone Image
        phone = load_and_tint(data["image_url"])
        phone.thumbnail((box[2]-box[0]-80, box[3]-box[1]-80), Image.Resampling.LANCZOS)
        px = box[0] + (box[2]-box[0]-phone.width)//2
        py = box[1] + (box[3]-box[1]-phone.height)//2
        canvas.paste(phone, (px, py), phone)

        # 3. Logo & Animated Title
        logo = load_and_tint(CONFIG["icons"]["logo"]).resize(cfg["logo_size"], Image.Resampling.LANCZOS)
        canvas.paste(logo, cfg["logo_pos"], logo)
        
        full_title = data["name"].upper()
        if t is not None:
            chars = int(len(full_title) * min(t/1.5, 1.0)) # Type out in 1.5s
            display_title = full_title[:chars]
        else: display_title = full_title
            
        anchor = "mm" if mode == "tiktok" else "la"
        draw.text(cfg["title_pos"], display_title, fill="white", font_size=55, anchor=anchor)

        # 4. Specs (Staggered Entry)
        sx, sy = cfg["spec_start"]
        for i, (icon_k, val) in enumerate(data["specs"]):
            if t is not None and t < (1.5 + i * 0.3): continue # Sequence Specs
            y = sy + (i * cfg["spec_gap"])
            icon = load_and_tint(CONFIG["icons"].get(icon_k), CONFIG["colors"]["white"]).resize((45, 45), Image.Resampling.LANCZOS)
            canvas.paste(icon, (sx, y), icon)
            draw.text((sx + 65, y + 5), val, fill="white", font_size=28)

        # 5. Price Badge (Pop-in at 3.5s)
        if t is None or t > 3.5:
            draw.rounded_rectangle(cfg["price_box"], radius=15, fill=CONFIG["colors"]["mint"])
            px_c = (cfg["price_box"][0] + cfg["price_box"][2]) // 2
            py_c = (cfg["price_box"][1] + cfg["price_box"][3]) // 2
            draw.text((px_c, py_c), f"KES {price}", fill="white", font_size=42, anchor="mm")

        # 6. Footer
        self.draw_footer(canvas, cfg["footer_y"])
        return canvas

    def draw_footer(self, canvas, y):
        draw = ImageDraw.Draw(canvas)
        items = [
            ("whatsapp", CONFIG["contact_info"]["whatsapp"], None),
            ("location", CONFIG["contact_info"]["location"], None),
            ("web", CONFIG["contact_info"]["web"], CONFIG["colors"]["blue"])
        ]
        w = canvas.width // 3
        for i, (icon_k, txt, col) in enumerate(items):
            ix = (i * w) + 35
            icon = load_and_tint(CONFIG["icons"][icon_k], col).resize((35, 35), Image.Resampling.LANCZOS)
            canvas.paste(icon, (ix, y), icon)
            draw.text((ix + 45, y + 5), txt, fill="white", font_size=18)

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
st.set_page_config(page_title="Triple K Generator", layout="centered")
st.title("📱 Triple K: Ad Master")

# Input Section
colA, colB = st.columns(2)
with colA:
    query = st.text_input("Device Name", "iPhone 15 Pro Max")
    price_val = st.text_input("Price (KES)", "175,000")
with colB:
    format_mode = st.selectbox("Social Format", ["whatsapp", "tiktok"])

if st.button("Generate", use_container_width=True):
    device_data = fetch_data(query)
    
    if device_data:
        engine = AdEngine()
        
        # Image Display
        st.subheader("1. Static Flyer")
        final_img = engine.build_ad(format_mode, device_data, price_val)
        st.image(final_img)
        
        # Download Image
        img_io = BytesIO()
        final_img.save(img_io, 'PNG')
        st.download_button("📥 Download Flyer", img_io.getvalue(), f"{query}.png", "image/png")
        
        st.divider()

        # Video Rendering
        st.subheader("2. Animated Video Ad")
        with st.spinner("Processing High-Quality Video..."):
            def make_frame(t):
                # Build frame with time-based animations
                frame_img = engine.build_ad(format_mode, device_data, price_val, t)
                # Apply Zoom
                w, h = frame_img.size
                zoom = 1 + (0.05 * (t / 5))
                frame_img = frame_img.resize((int(w*zoom), int(h*zoom)), Image.Resampling.LANCZOS)
                # Center Crop
                return np.array(frame_img.crop(((frame_img.width-w)//2, (frame_img.height-h)//2, (frame_img.width+w)//2, (frame_img.height+h)//2)))

            clip = VideoClip(make_frame, duration=5)
            clip.write_videofile("output.mp4", fps=24, codec="libx264", audio=False, logger=None)
            st.video("output.mp4")
            
            with open("output.mp4", "rb") as f:
                st.download_button("📥 Download Video", f.read(), f"{query}.mp4", "video/mp4")
    else:
        st.error("No data found for this model. Please check the spelling.")
