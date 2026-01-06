import streamlit as st
from PIL import Image, ImageDraw
import requests
from io import BytesIO
import numpy as np
from moviepy.editor import VideoClip
import re

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
    },
    "contact": {
        "whatsapp": "+254 700 123 456",
        "location": "CBD, Nairobi",
        "web": "www.tripplek.co.ke"
    }
}

# ==========================================
# 2. DATA HANDLING FUNCTIONS
# ==========================================
def clean_specs(info):
    """Parses raw API data into clean marketing strings."""
    # Processor
    chip = info.get("platform", {}).get("chipset", "Flagship Processor").split('(')[0].strip()
    # Battery
    batt_raw = info.get("battery", {}).get("battType", "5000")
    batt_match = re.search(r'(\d+)\s*mAh', batt_raw)
    battery = f"{batt_match.group(1)} mAh" if batt_match else "5000 mAh"
    # Memory & Display
    memory = info.get("memory", {}).get("internal", "High Speed").split(',')[0].strip()
    screen = info.get("display", {}).get("size", "6.7\"").split(' ')[0] + " Display"
    camera = info.get("mainCamera", {}).get("mainModules", "50MP").split(',')[0].strip()

    return [
        ("processor", chip), ("screen", screen), 
        ("camera", camera), ("memory", memory), ("battery", battery)
    ]

def fetch_device_data(query):
    """Fetches data with a built-in fallback for rate limits."""
    def get_fallback():
        return {
            "name": query.upper(),
            "img_url": CONFIG["icons"]["logo"],
            "specs": [
                ("processor", "Premium Chipset"), ("screen", "Ultra Vision Display"),
                ("camera", "Pro-Grade Camera"), ("memory", "Expanded Storage"),
                ("battery", "All-Day Battery Life")
            ],
            "is_fallback": True
        }

    base_url = "https://tkphsp2.vercel.app/gsm"
    try:
        search_res = requests.get(f"{base_url}/search?q={query}", timeout=5)
        
        # Handle Rate Limit or API Down
        if search_res.status_code != 200:
            return get_fallback()

        search_data = search_res.json()
        if not search_data: return None
        
        dev_id = search_data[0]['id']
        info = requests.get(f"{base_url}/info/{dev_id}", timeout=5).json()
        imgs = requests.get(f"{base_url}/images/{dev_id}", timeout=5).json()
        
        img_list = imgs.get('images', [])
        return {
            "name": search_data[0]['name'],
            "img_url": img_list[1] if len(img_list) > 1 else search_data[0]['image'],
            "specs": clean_specs(info),
            "is_fallback": False
        }
    except:
        return get_fallback()

# ==========================================
# 3. GRAPHICS & DRAWING FUNCTIONS
# ==========================================
@st.cache_data
def load_asset(url, color=None, size=None):
    try:
        res = requests.get(url, timeout=10)
        img = Image.open(BytesIO(res.content)).convert("RGBA")
        if color:
            r, g, b, a = img.split()
            target = Image.new("RGB", img.size, color)
            img = Image.merge("RGBA", (*target.split(), a))
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        return img
    except:
        return Image.new("RGBA", (100, 100), (0,0,0,0))

def draw_ad_frame(mode, data, price, t=None):
    cfg = CONFIG["layouts"][mode]
    canvas = Image.new("RGB", cfg["canvas"], CONFIG["colors"]["bg"])
    draw = ImageDraw.Draw(canvas)
    
    # 1. Phone Container
    draw.rounded_rectangle(cfg["phone_box"], radius=30, fill="white", outline=CONFIG["colors"]["gold"], width=6)
    
    # 2. Phone Image
    phone = load_asset(data["img_url"])
    phone.thumbnail((450, 800), Image.Resampling.LANCZOS)
    canvas.paste(phone, (cfg["phone_box"][0]+40, cfg["phone_box"][1]+60), phone)

    # 3. Animated Title (Typewriter)
    title = data["name"].upper()
    if t is not None:
        title = title[:int(len(title) * min(t/1.5, 1.0))]
    
    anchor = "mm" if mode == "tiktok" else "la"
    draw.text(cfg["title_pos"], title, fill="white", font_size=55, anchor=anchor)

    # 4. Staggered Specs
    sx, sy = cfg["spec_start"]
    for i, (icon_name, val) in enumerate(data["specs"]):
        if t is not None and t < (1.5 + i * 0.2): continue
        y_pos = sy + (i * 95)
        icon = load_asset(CONFIG["icons"][icon_name], CONFIG["colors"]["white"], (45, 45))
        canvas.paste(icon, (sx, y_pos), icon)
        draw.text((sx + 65, y_pos + 5), val, fill="white", font_size=28)

    # 5. Price (Appear at 3.5s)
    if t is None or t > 3.5:
        draw.text((sx, sy + 550), f"KES {price}", fill=CONFIG["colors"]["mint"], font_size=65)

    return canvas

# ==========================================
# 4. VIDEO & MAIN UI
# ==========================================
def generate_video(mode, data, price):
    def make_frame(t):
        frame = draw_ad_frame(mode, data, price, t)
        w, h = frame.size
        zoom = 1 + (0.05 * (t / 5))
        frame = frame.resize((int(w*zoom), int(h*zoom)), Image.Resampling.LANCZOS)
        return np.array(frame.crop(((frame.width-w)//2, (frame.height-h)//2, (frame.width+w)//2, (frame.height+h)//2)))

    clip = VideoClip(make_frame, duration=5)
    clip.write_videofile("ad_final.mp4", fps=24, codec="libx264", audio=False, logger=None)
    return "ad_final.mp4"

def main():
    st.set_page_config(page_title="Triple K Pro", layout="centered")
    st.title("🎬 Triple K Agency: Ad Master")

    # Input Row
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Search Device", "iPhone 15 Pro")
    price = c2.text_input("Price (KES)", "145,000")
    mode = c3.selectbox("Format", ["whatsapp", "tiktok"])

    if st.button("Generate", use_container_width=True):
        data = fetch_device_data(query)
        
        if data:
            if data.get("is_fallback"):
                st.warning("⚠️ API Rate Limit active. Using generic professional specs.")
            
            # Static Flyer
            st.subheader("1. Static Flyer")
            img = draw_ad_frame(mode, data, price)
            st.image(img)
            
            # Download Image
            buf = BytesIO()
            img.save(buf, format="PNG")
            st.download_button("📥 Download Flyer", buf.getvalue(), f"{query}.png", "image/png")
            
            st.divider()

            # Video
            st.subheader("2. Animated Video Ad")
            with st.spinner("Generating Zoom Animation..."):
                v_path = generate_video(mode, data, price)
                st.video(v_path)
                with open(v_path, "rb") as f:
                    st.download_button("📥 Download Video", f.read(), f"{query}.mp4")
        else:
            st.error("Could not find that device.")

if __name__ == "__main__":
    main()
