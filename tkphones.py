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
# 2. UTILS & VIDEO ENGINE
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

def make_video(image, name="temp_ad_video.mp4"):
    # Video must be RGB (discard alpha)
    img_rgb = image.convert("RGB")
    w, h = img_rgb.size
    
    def get_frame(t):
        # 5% Zoom over 5 seconds
        zoom = 1 + (0.05 * (t/5))
        nw, nh = int(w*zoom), int(h*zoom)
        # Resize with high quality to keep text/icons clear
        frame = img_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
        # Crop to original center
        left, top = (nw - w) // 2, (nh - h) // 2
        return np.array(frame.crop((left, top, left + w, top + h)))

    clip = VideoClip(get_frame, duration=5)
    clip.write_videofile(name, fps=24, codec="libx264", audio=False, logger=None)
    return name

# ==========================================
# 3. MASTER AD ENGINE
# ==========================================
class AdEngine:
    def build_ad(self, mode, data, price):
        cfg = CONFIG["layouts"][mode]
        canvas = Image.new("RGB", cfg["canvas"], CONFIG["colors"]["bg"])
        draw = ImageDraw.Draw(canvas)

        # 1. Shadow & White Card for Phone
        box = cfg["phone_box"]
        for i in range(12): # Soft Shadow
            draw.rounded_rectangle([box[0]+i, box[1]+i, box[2]+i, box[3]+i], radius=25, fill=(0,0,0,25))
        draw.rounded_rectangle(box, radius=25, fill="white", outline=CONFIG["colors"]["gold"], width=5)

        # 2. Phone Image (Centered in Box)
        phone = load_and_tint(data["image_url"])
        phone.thumbnail((box[2]-box[0]-80, box[3]-box[1]-80), Image.Resampling.LANCZOS)
        px = box[0] + (box[2]-box[0]-phone.width)//2
        py = box[1] + (box[3]-box[1]-phone.height)//2
        canvas.paste(phone, (px, py), phone)

        # 3. Logo & Title
        logo = load_and_tint(CONFIG["icons"]["logo"]).resize(cfg["logo_size"], Image.Resampling.LANCZOS)
        canvas.paste(logo, cfg["logo_pos"], logo)
        anchor = "mm" if mode == "tiktok" else "la"
        draw.text(cfg["title_pos"], data["name"].upper(), fill="white", font_size=55, anchor=anchor)

        # 4. Specs (Tinted White)
        sx, sy = cfg["spec_start"]
        for i, (icon_k, val) in enumerate(data["specs"]):
            y = sy + (i * cfg["spec_gap"])
            icon = load_and_tint(CONFIG["icons"].get(icon_k), CONFIG["colors"]["white"]).resize((45, 45), Image.Resampling.LANCZOS)
            canvas.paste(icon, (sx, y), icon)
            draw.text((sx + 65, y + 5), val, fill="white", font_size=28)

        # 5. Price Badge
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
        chip = i.get("platform", {}).get("chipset", "Powerful Chip").split('(')[0].strip()
        img = m.get('images', [])[1] if len(m.get('images', [])) > 1 else s[0]['image']
        return {"name": s[0]['name'], "image_url": img, "specs": [
            ("processor", chip), ("screen", i.get("display", {}).get("size", "6.7\"")),
            ("camera", i.get("mainCamera", {}).get("mainModules", "48MP").split(',')[0]),
            ("memory", "High RAM"), ("battery", i.get("battery", {}).get("battType", "5000mAh").split(' ')[0])
        ]}
    except: return None

st.title("Triple K: Master Ad Generator")
q = st.sidebar.text_input("Model", "iPhone 15 Pro")
p = st.sidebar.text_input("Price", "145,000")
m = st.sidebar.radio("Format", ["whatsapp", "tiktok"])

if st.sidebar.button("Generate Ad Assets"):
    data = fetch_data(q)
    if data:
        # 1. Build Image
        engine = AdEngine()
        final_img = engine.build_ad(m, data, p)
        st.image(final_img, caption="Static Preview")
        
        # 2. Render Video
        with st.spinner("Generating High-Quality Zoom Video..."):
            vid_path = make_video(final_img)
            st.video(vid_path)
            
            with open(vid_path, "rb") as f:
                st.download_button("📥 Download MP4 Video", f.read(), f"tripple_k_{q}.mp4")
