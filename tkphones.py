import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import numpy as np
from moviepy import VideoClip
import re
import random

# ==========================================
# 1. GLOBAL CONFIGURATION
# ==========================================
CONFIG = {
    "colors": {
        "bg_top": "#0F0A0A", 
        "bg_bottom": "#1A1A2E",
        "mint": "#3EB489", 
        "white": "#FFFFFF", 
        "gold": "#C5A059"
    },
    "fonts": {"title": 55, "specs": 26, "price": 40, "footer": 20},
    "sizes": {
        "logo": (250, 80),
        "phone_img": (400, 600),
        "spec_icon": (40, 40),
        "footer_icon_whatsapp": (35, 35),
        "footer_icon_location": (30, 30),
        "footer_icon_web": (30, 30),
        "badge_radius": 15
    },
    "icons": {
        "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png",
        "processor": "https://ik.imagekit.io/ericmwangi/processor.png",
        "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
        "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
        "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
        "battery": "https://ik.imagekit.io/ericmwangi/battery.png",
        "whatsapp": "https://ik.imagekit.io/ericmwangi/whatsapp.png",
        "location": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
        "web": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png"
    },
    "layouts": {
        "whatsapp": {
            "canvas": (1080, 1080), "phone_box": [60, 220, 620, 850], 
            "spec_start": (680, 250), "title_pos": (540, 150),
            "footer_y": 950, "footer_x": [40, 380, 720]
        },
        "tiktok": {
            "canvas": (1080, 1920), "phone_box": [140, 450, 940, 1250], 
            "spec_start": (200, 1350), "title_pos": (540, 320),
            "footer_y": 1800, "footer_x": [80, 400, 720]
        }
    },
    "particles": {"count": 40, "speed": 1.5},
    "contact": {
        "whatsapp": "+254 700 123 456", 
        "location": "CBD, Nairobi", 
        "web": "www.tripplek.co.ke"
    },
    "placeholder_phone": "https://ik.imagekit.io/ericmwangi/phone_placeholder.png"
}

# ==========================================
# 2. UTILS & DATA SCOUTING
# ==========================================
@st.cache_data
def load_asset(url, size=None):
    try:
        res = requests.get(url, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGBA")
        if size: img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except: return Image.new("RGBA", (1,1), (0,0,0,0))

def fetch_device_data(query):
    # Professional fallback data
    dummy = {
        "name": query.upper(), 
        "img_url": CONFIG["placeholder_phone"], 
        "specs": [("processor", "Flagship Chip"), ("screen", "OLED Display"), ("memory", "High Speed"), ("battery", "Long Life")]
    }
    try:
        # 1. SEARCH: Get the base_id and official name
        search_res = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={query}", timeout=10).json()
        
        base_id = search_res[0]['id'] # e.g., "xiaomi_poco_x3_pro-10802.php"
        official_name = search_res[0]['name']

        # 2. IMAGE ID TRANSFORMATION
        # The API requires "-pictures-" inserted before the numeric ID
        if "-" in base_id:
            parts = base_id.rsplit('-', 1)
            image_id = f"{parts[0]}-pictures-{parts[1]}"
        else:
            image_id = base_id
        
        # 3. FETCH INFO & IMAGES
        info = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{base_id}", timeout=10).json()
        imgs_data = requests.get(f"https://tkphsp2.vercel.app/gsm/images/{base_id}", timeout=10).json()
        
        # 4. IMAGE LOGIC: Priority to Lifestyle Shot (index 1)
        img_list = imgs_data.get('images', [])
        api_img = img_list[1]

        # 5. CLEAN SPECS (Mapped to your specific JSON structure)
        # Chipset is inside 'platform'
        chip = info.get("platform", {}).get("chipset", "High Performance").split('(')[0].strip()
        
        # Screen is inside 'display' -> 'size'
        display_raw = info.get("display", {}).get("size", "6.7 inches")
        screen = display_raw.split(',')[0].strip() # Clean "6.67 inches, 107 cm2..." to "6.67 inches"
        
        # Memory is inside 'memory' -> 'internal'
        mem_raw = info.get("memory", {}).get("internal", "128GB 8GB RAM")
        memory = mem_raw.split(',')[0].strip() # Takes the primary storage/RAM combo

        # Battery is inside 'battery' -> 'battType'
        batt_raw = info.get("battery", {}).get("battType", "5000 mAh")
        batt_match = re.search(r'(\d+)\s*mAh', batt_raw)
        battery = f"{batt_match.group(1)} mAh" if batt_match else "5000 mAh"

        return {
            "name": official_name, 
            "img_url": api_img,
            "specs": [
                ("processor", chip), 
                ("screen", screen), 
                ("memory", memory), 
                ("battery", battery)
            ]
        }
    except Exception as e:
        # If any step fails, return the clean dummy data
        return {
            "name": official_name, 
            "img_url": api_img,
            "specs": [
                ("processor", chip), 
                ("screen", screen), 
                ("memory", memory), 
                ("battery", battery)
            ]

# ==========================================
# 3. MOTION GRAPHICS ENGINE
# ==========================================
def hex_to_rgb(hex_str):
    return tuple(int(hex_str.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def create_gradient_bg(width, height):
    base = Image.new('RGB', (width, height))
    top_color = hex_to_rgb(CONFIG["colors"]["bg_top"])
    bottom_color = hex_to_rgb(CONFIG["colors"]["bg_bottom"])
    draw = ImageDraw.Draw(base)
    for y in range(height):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (y / height))
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (y / height))
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base

def draw_particles(canvas, t):
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    random.seed(42)
    for _ in range(CONFIG["particles"]["count"]):
        x = random.randint(0, w)
        y_start = random.randint(0, h)
        y = (y_start + int(t * 100 * CONFIG["particles"]["speed"])) % h
        size = random.randint(1, 3)
        draw.ellipse([x, y, x+size, y+size], fill=(255, 255, 255, 100))
    return canvas

def create_base_layer(mode, data):
    cfg = CONFIG["layouts"][mode]
    base = Image.new("RGBA", cfg["canvas"], (0,0,0,0))
    draw = ImageDraw.Draw(base)
    
    # Logo
    logo = load_asset(CONFIG["icons"]["logo"], size=CONFIG["sizes"]["logo"])
    base.paste(logo, (cfg["canvas"][0]//2 - CONFIG["sizes"]["logo"][0]//2, 40), logo)

    # Phone Card
    draw.rounded_rectangle(cfg["phone_box"], radius=30, fill="white", outline=CONFIG["colors"]["gold"], width=6)
    phone = load_asset(data["img_url"])
    phone.thumbnail(CONFIG["sizes"]["phone_img"], Image.Resampling.LANCZOS)
    px = cfg["phone_box"][0] + (cfg["phone_box"][2]-cfg["phone_box"][0]-phone.width)//2
    py = cfg["phone_box"][1] + (cfg["phone_box"][3]-cfg["phone_box"][1]-phone.height)//2
    base.paste(phone, (px, py), phone)

    # Footer
    items = [("whatsapp", CONFIG["contact"]["whatsapp"], "footer_icon_whatsapp"), 
             ("location", CONFIG["contact"]["location"], "footer_icon_location"), 
             ("web", CONFIG["contact"]["web"], "footer_icon_web")]
    for i, (k, txt, sz_key) in enumerate(items):
        icon = load_asset(CONFIG["icons"][k], size=CONFIG["sizes"][sz_key])
        x = cfg["footer_x"][i]
        base.paste(icon, (x, cfg["footer_y"]), icon)
        draw.text((x + 45, cfg["footer_y"] + 5), txt, fill="white", font_size=CONFIG["fonts"]["footer"])
    return base

def add_animation_overlay(canvas, mode, data, price, t=None):
    overlay = canvas.copy()
    draw = ImageDraw.Draw(overlay)
    cfg = CONFIG["layouts"][mode]
    
    # Typing Title
    name = data["name"].upper()
    if t is not None: name = name[:int(len(name) * min(t/1.5, 1.0))]
    draw.text(cfg["title_pos"], name, fill="white", font_size=CONFIG["fonts"]["title"], anchor="mm")

    # Staggered Specs
    sx, sy = cfg["spec_start"]
    for i, (icon_name, val) in enumerate(data["specs"]):
        if t is not None and t < (1.5 + i * 0.2): continue
        y = sy + (i * 95)
        icon = load_asset(CONFIG["icons"][icon_name], size=CONFIG["sizes"]["spec_icon"])
        overlay.paste(icon, (sx, y), icon)
        draw.text((sx + 60, y + 5), val, fill="white", font_size=CONFIG["fonts"]["specs"])

    # Price Badge
    if t is None or t > 3.5:
        badge_box = [sx, sy + 480, sx + 320, sy + 560]
        draw.rounded_rectangle(badge_box, radius=CONFIG["sizes"]["badge_radius"], fill=CONFIG["colors"]["mint"])
        draw.text((sx + 160, sy + 520), f"KES {price}", fill="white", font_size=CONFIG["fonts"]["price"], anchor="mm")
    return overlay

# ==========================================
# 4. FINAL ASSEMBLY
# ==========================================
def generate_video(mode, data, price):
    cfg = CONFIG["layouts"][mode]
    base_layer = create_base_layer(mode, data)
    gradient_bg = create_gradient_bg(cfg["canvas"][0], cfg["canvas"][1])

    def make_frame(t):
        frame = draw_particles(gradient_bg.copy(), t)
        frame.paste(base_layer, (0,0), base_layer)
        final = add_animation_overlay(frame, mode, data, price, t)
        return np.array(final)

    clip = VideoClip(make_frame, duration=5)
    clip.write_videofile("ad.mp4", fps=24, codec="libx264", audio=False, logger=None)
    return "ad.mp4"

def main():
    st.set_page_config(page_title="Triple K Pro", layout="centered")
    st.title("🎬 Triple K: Ad Engine")
    
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Device Name", "iPhone 15 Pro")
    price = c2.text_input("Price", "145,000")
    mode = c3.selectbox("Format", ["whatsapp", "tiktok"])
    
    if st.button("Generate Assets", use_container_width=True):
        data = fetch_device_data(query)
        # Display static preview
        cfg = CONFIG["layouts"][mode]
        bg = create_gradient_bg(cfg["canvas"][0], cfg["canvas"][1])
        base = create_base_layer(mode, data)
        bg.paste(base, (0,0), base)
        st.image(add_animation_overlay(bg, mode, data, price))
        
        with st.spinner("Rendering Animation..."):
            st.video(generate_video(mode, data, price))

if __name__ == "__main__": main()
