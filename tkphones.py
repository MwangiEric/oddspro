import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
import numpy as np
from moviepy import VideoClip
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
# 2. UTILS & ANIMATED VIDEO ENGINE
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

def make_video(engine, mode, data, price, name="temp_ad_video.mp4"):
    duration = 5
    
    def get_frame(t):
        # We build a unique frame for every timestamp 't' to allow for text animations
        img = engine.build_ad(mode, data, price, time_offset=t)
        img_rgb = img.convert("RGB")
        w, h = img_rgb.size
        
        # Consistent 5% zoom
        zoom = 1 + (0.05 * (t/duration))
        nw, nh = int(w*zoom), int(h*zoom)
        frame = img_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
        left, top = (nw - w) // 2, (nh - h) // 2
        return np.array(frame.crop((left, top, left + w, top + h)))

    clip = VideoClip(get_frame, duration=duration)
    clip.write_videofile(name, fps=24, codec="libx264", audio=False, logger=None)
    return name

# ==========================================
# 3. MASTER AD ENGINE
# ==========================================
class AdEngine:
    def build_ad(self, mode, data, price, time_offset=None):
        cfg = CONFIG["layouts"][mode]
        canvas = Image.new("RGB", cfg["canvas"], CONFIG["colors"]["bg"])
        draw = ImageDraw.Draw(canvas)

        # 1. Shadow & White Card for Phone
        box = cfg["phone_box"]
        for i in range(12): 
            draw.rounded_rectangle([box[0]+i, box[1]+i, box[2]+i, box[3]+i], radius=25, fill=(0,0,0,25))
        draw.rounded_rectangle(box, radius=25, fill="white", outline=CONFIG["colors"]["gold"], width=5)

        # 2. Phone Image
        phone = load_and_tint(data["image_url"])
        phone.thumbnail((box[2]-box[0]-80, box[3]-box[1]-80), Image.Resampling.LANCZOS)
        px = box[0] + (box[2]-box[0]-phone.width)//2
        py = box[1] + (box[3]-box[1]-phone.height)//2
        canvas.paste(phone, (px, py), phone)

        # 3. Logo & Title (Animation: Typewriter Effect)
        logo = load_and_tint(CONFIG["icons"]["logo"]).resize(cfg["logo_size"], Image.Resampling.LANCZOS)
        canvas.paste(logo, cfg["logo_pos"], logo)
        
        anchor = "mm" if mode == "tiktok" else "la"
        full_title = data["name"].upper()
        if time_offset is not None:
            # Title finishes typing in 1.5 seconds
            chars = int(len(full_title) * min(time_offset / 1.5, 1.0))
            display_title = full_title[:chars]
        else:
            display_title = full_title
            
        draw.text(cfg["title_pos"], display_title, fill="white", font_size=55, anchor=anchor)

        # 4. Specs (Animation: Progressive Staggered Entry)
        sx, sy = cfg["spec_start"]
        for i, (icon_k, val) in enumerate(data["specs"]):
            # Delay each spec by 0.3 seconds
            if time_offset is not None and time_offset < (1.5 + i * 0.3):
                continue
                
            y = sy + (i * cfg["spec_gap"])
            icon = load_and_tint(CONFIG["icons"].get(icon_k), CONFIG["colors"]["white"]).resize((45, 45), Image.Resampling.LANCZOS)
            canvas.paste(icon, (sx, y), icon)
            draw.text((sx + 65, y + 5), val, fill="white", font_size=28)

        # 5. Price Badge (Animation: Pop in at 3.5s)
        if time_offset is None or time_offset > 3.5:
            draw.rounded_rectangle(cfg["price_box"], radius=15, fill=CONFIG["colors"]["mint"])
            px = (cfg["price_box"][0] + cfg["price_box"][2]) // 2
            py = (cfg["price_box"][1] + cfg["price_box"][3]) // 2
            draw.text((px, py), f"KES {price}", fill="white", font_size=40, anchor="mm")

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
# 4. DATA FETCH & EXECUTION
# ==========================================
def fetch_data(q):
    try:
        s = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={q}").json()
        if not s: return None
        i = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{s[0]['id']}").json()
        m = requests.get(f"https://tkphsp2.vercel.app/gsm/images/{s[0]['id']}").json()
        
        # Cleaned Hardware Data
        chip = i.get("platform", {}).get("chipset", "Powerful Chip").split('(')[0].strip()
        
        # Fixed Battery extraction
        raw_batt = i.get("battery", {}).get("battType", "5000 mAh")
        batt_val = raw_batt.split('mAh')[0].strip().split(' ')[-1] + " mAh"
        
        # Fixed RAM/Storage extraction
        mem_info = i.get("memory", {}).get("internal", "High Performance")
        mem_val = mem_info.split(',')[0].strip()
        
        img = m.get('images', [])[1] if len(m.get('images', [])) > 1 else s[0]['image']
        
        return {"name": s[0]['name'], "image_url": img, "specs": [
            ("processor", chip), 
            ("screen", i.get("display", {}).get("size", "6.7\"")),
            ("camera", i.get("mainCamera", {}).get("mainModules", "48MP").split(',')[0]),
            ("memory", mem_val), 
            ("battery", batt_val)
        ]}
    except: return None

# MAIN UI (No sidebar)
st.set_page_config(page_title="Triple K Ad Gen", layout="centered")
st.title("Triple K: Master Ad Generator")

c1, c2 = st.columns(2)
with c1:
    q = st.text_input("Model", "iPhone 15 Pro")
    p = st.text_input("Price (KES)", "145,000")
with c2:
    m = st.selectbox("Format", ["whatsapp", "tiktok"])

if st.button("Generate", use_container_width=True):
    data = fetch_data(q)
    if data:
        engine = AdEngine()
        
        # 1. Image Flyer
        st.subheader("Static Flyer")
        final_img = engine.build_ad(m, data, p)
        st.image(final_img)
        
        # Image Download
        buf = BytesIO()
        final_img.save(buf, format="PNG")
        st.download_button("📥 Download Static Flyer", buf.getvalue(), f"flyer_{q}.png", "image/png")
        
        st.divider()
        
        # 2. Video Ad
        st.subheader("Animated Video Ad")
        with st.spinner("Rendering Video with Text Animations..."):
            vid_path = make_video(engine, m, data, p)
            st.video(vid_path)
            
            with open(vid_path, "rb") as f:
                st.download_button("📥 Download MP4 Video", f.read(), f"video_{q}.mp4", "video/mp4")
    else:
        st.error("Could not find data for that model.")
