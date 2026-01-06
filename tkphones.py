import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import numpy as np
from moviepy import VideoClip
import os

# ==========================================
# 1. GLOBAL CONFIGURATION
# ==========================================
CONFIG = {
    "colors": {
        "bg": "#0F0A0A", 
        "mint": "#3EB489", 
        "white": "#FFFFFF", 
        "gold": "#C5A059", 
        "blue": "#1DA1F2"
    },
    "icons": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png",
        "processor": "https://ik.imagekit.io/ericmwangi/processor.png",
        "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
        "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
        "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
        "battery": "https://ik.imagekit.io/ericmwangi/battery.png"
    },
    "layouts": {
        "whatsapp": {
            "canvas": (1080, 1080), 
            "phone_box": [60, 200, 620, 950], 
            "spec_start": (680, 250),
            "title_pos": (280, 100)
        },
        "tiktok": {
            "canvas": (1080, 1920), 
            "phone_box": [140, 350, 940, 1250], 
            "spec_start": (200, 1350),
            "title_pos": (540, 250)
        }
    }
}

# ==========================================
# 2. DATA & CLEANING FUNCTIONS
# ==========================================
def clean_specs(info):
    """Refined function to polish raw hardware data for marketing."""
    # Chipset cleaning
    chip = info.get("platform", {}).get("chipset", "High Performance").split('(')[0].strip()
    
    # Battery cleaning
    batt_raw = info.get("battery", {}).get("battType", "5000")
    batt_num = batt_raw.split('mAh')[0].strip().split(' ')[-1]
    battery = f"{batt_num} mAh"
    
    # Memory and Display
    memory = info.get("memory", {}).get("internal", "Standard").split(',')[0].strip()
    screen = info.get("display", {}).get("size", "6.7\"").split(' ')[0] + " Display"
    camera = info.get("mainCamera", {}).get("mainModules", "50MP").split(',')[0].strip()

    return [
        ("processor", chip), ("screen", screen), 
        ("camera", camera), ("memory", memory), ("battery", battery)
    ]

def fetch_device_data(query):
    """Handles API calls and returns a structured data object."""
    try:
        # Step 1: Search
        search = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={query}", timeout=10).json()
        if not search: return None
        
        # Step 2: Details & Images
        dev_id = search[0]['id']
        info = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{dev_id}").json()
        imgs = requests.get(f"https://tkphsp2.vercel.app/gsm/images/{dev_id}").json()
        
        return {
            "name": search[0]['name'],
            "img_url": imgs.get('images', [])[1] if len(imgs.get('images', [])) > 1 else search[0]['image'],
            "specs": clean_specs(info)
        }
    except:
        return None

# ==========================================
# 3. DRAWING & ASSET FUNCTIONS
# ==========================================
@st.cache_data
def load_asset(url, color=None, size=None):
    try:
        res = requests.get(url, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGBA")
        if color:
            r, g, b, a = img.split()
            target = Image.new("RGB", img.size, color)
            tr, tg, tb = target.split()
            img = Image.merge("RGBA", (tr, tg, tb, a))
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except:
        return Image.new("RGBA", (1, 1), (0,0,0,0))

def draw_ad_frame(mode, data, price, t=None):
    cfg = CONFIG["layouts"][mode]
    canvas = Image.new("RGB", cfg["canvas"], CONFIG["colors"]["bg"])
    draw = ImageDraw.Draw(canvas)
    
    # Draw Container
    draw.rounded_rectangle(cfg["phone_box"], radius=30, fill="white", outline=CONFIG["colors"]["gold"], width=6)
    
    # Phone Image
    phone = load_asset(data["img_url"])
    phone.thumbnail((450, 800), Image.Resampling.LANCZOS)
    canvas.paste(phone, (cfg["phone_box"][0]+40, cfg["phone_box"][1]+60), phone)

    # Animated Title
    title = data["name"].upper()
    if t is not None:
        title = title[:int(len(title) * min(t/1.5, 1.0))]
    
    anchor = "mm" if mode == "tiktok" else "la"
    draw.text(cfg["title_pos"], title, fill="white", font_size=55, anchor=anchor)

    # Staggered Specs
    sx, sy = cfg["spec_start"]
    for i, (icon_name, val) in enumerate(data["specs"]):
        if t is not None and t < (1.5 + i * 0.2): continue
        y_pos = sy + (i * 95)
        icon = load_asset(CONFIG["icons"][icon_name], CONFIG["colors"]["white"], (45, 45))
        canvas.paste(icon, (sx, y_pos), icon)
        draw.text((sx + 65, y_pos + 5), val, fill="white", font_size=28)

    # Price Badge (Appear at end)
    if t is None or t > 3.0:
        draw.text((sx, sy + 550), f"KES {price}", fill=CONFIG["colors"]["mint"], font_size=65)

    return canvas

# ==========================================
# 4. VIDEO ENGINE & MAIN UI
# ==========================================
def generate_video(mode, data, price):
    def make_frame(t):
        frame = draw_ad_frame(mode, data, price, t)
        w, h = frame.size
        zoom = 1 + (0.05 * (t / 5))
        frame = frame.resize((int(w*zoom), int(h*zoom)), Image.Resampling.LANCZOS)
        return np.array(frame.crop(((frame.width-w)//2, (frame.height-h)//2, (frame.width+w)//2, (frame.height+h)//2)))

    clip = VideoClip(make_frame, duration=5)
    clip.write_videofile("ad_output.mp4", fps=24, codec="libx264", audio=False, logger=None)
    return "ad_output.mp4"

def main():
    st.set_page_config(page_title="Triple K Pro", layout="centered")
    st.title("🚀 Triple K: Master Ad Generator")

    # Sidebar-free Input Row
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Device", "iPhone 15 Pro")
    price = c2.text_input("Price", "145,000")
    mode = c3.selectbox("Format", ["whatsapp", "tiktok"])

    if st.button("Generate", use_container_width=True):
        with st.spinner("Processing High-Quality Assets..."):
            data = fetch_device_data(query)
            if data:
                # Static Flyer
                st.subheader("Flyer Preview")
                img = draw_ad_frame(mode, data, price)
                st.image(img)
                
                # Video Ad
                st.subheader("Animated Video")
                video_path = generate_video(mode, data, price)
                st.video(video_path)
                
                # Downloads
                with open(video_path, "rb") as f:
                    st.download_button("📥 Download MP4 Video", f.read(), f"{query}.mp4")
            else:
                st.error("Could not find that device. Please check the spelling.")

if __name__ == "__main__":
    main()
