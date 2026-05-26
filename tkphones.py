import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import numpy as np
from moviepy import VideoClip
import re
import random
import html
import textwrap

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
    "placeholder_phone": "https://ik.imagekit.io/ericmwangi/iphone.png"
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
    except: 
        return Image.new("RGBA", (1,1), (0,0,0,0))

def parse_specs_from_short_desc(short_desc):
    """Extract key specs from WooCommerce short_description HTML/text"""
    specs = []
    text = html.unescape(short_desc)

    proc_match = re.search(r'Processor:\s*([^\n]+)', text, re.IGNORECASE)
    if proc_match:
        proc = proc_match.group(1).strip()
        proc = re.sub(r'\s*\([^)]*\)\s*–.*$', '', proc)
        specs.append(("processor", proc))
    else:
        specs.append(("processor", "High Performance"))

    disp_match = re.search(r'Display:\s*([^\n]+)', text, re.IGNORECASE)
    if disp_match:
        disp = disp_match.group(1).strip()
        size_match = re.search(r'([\d\.]+[″"]?\s*[\-\w\s]+?(?:AMOLED|OLED|LCD|IPS))', disp, re.IGNORECASE)
        screen = size_match.group(1).strip() if size_match else disp.split(',')[0].strip()
        specs.append(("screen", screen))
    else:
        specs.append(("screen", "OLED Display"))

    mem_match = re.search(r'(?:Memory|RAM)[:\s]+([^\n]+)', text, re.IGNORECASE)
    if mem_match:
        mem = mem_match.group(1).strip()
        mem_clean = mem.split(',')[0].strip()
        mem_clean = re.sub(r'\s+RAM\s*/\s*', ' / ', mem_clean, flags=re.IGNORECASE)
        mem_clean = re.sub(r'\s+ROM$', '', mem_clean, flags=re.IGNORECASE)
        specs.append(("memory", mem_clean))
    else:
        specs.append(("memory", "High Speed"))

    batt_match = re.search(r'Battery:\s*([^\n]+)', text, re.IGNORECASE)
    if batt_match:
        batt = batt_match.group(1).strip()
        mah_match = re.search(r'(\d{3,4})\s*mAh', batt, re.IGNORECASE)
        battery = f"{mah_match.group(1)} mAh" if mah_match else batt.split(',')[0].strip()
        specs.append(("battery", battery))
    else:
        specs.append(("battery", "Long Life"))

    return specs

def fetch_woocommerce_data(query):
    """Primary source: Fetch from Tripple K WooCommerce store"""
    try:
        url = f"https://myrhubpy.vercel.app/woocommerce/search/tripplek.co.ke.json?q={requests.utils.quote(query)}"
        res = requests.get(url, timeout=15).json()

        if res.get("error") or not res.get("items"):
            return None

        items = res["items"]
        if not items:
            return None

        product = items[0]
        extra = product.get("extra", {})

        price_raw = extra.get("sale_price") or extra.get("price", "0")
        price_num = re.sub(r'[^\d]', '', str(price_raw))

        # Use wsrv.nl processed image (image1) - this is the optimized URL
        img_url = extra.get("image1") or extra.get("image1_original") or CONFIG["placeholder_phone"]

        short_desc = extra.get("short_description", "")
        specs = parse_specs_from_short_desc(short_desc)

        return {
            "source": "woocommerce",
            "name": extra.get("product_name") or product.get("title", query),
            "img_url": img_url,
            "price": price_num,
            "specs": specs,
            "raw_data": product
        }

    except Exception as e:
        st.warning(f"WooCommerce fetch failed: {e}")
        return None

def fetch_gsmarena_data(query):
    """Fallback source: Fetch from GSM Arena API"""
    dummy = {
        "name": query.upper(), 
        "img_url": CONFIG["placeholder_phone"], 
        "specs": [("processor", "Flagship Chip"), ("screen", "OLED Display"), ("memory", "High Speed"), ("battery", "Long Life")]
    }

    try:
        search_res = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={query}", timeout=10).json()
        if not search_res: 
            return {**dummy, "price": "0", "source": "gsm_fallback"}

        base_id = search_res[0]['id']
        official_name = search_res[0]['name']

        if "-" in base_id:
            parts = base_id.rsplit('-', 1)
            clean_part_0 = parts[0].replace(".php", "")
            image_id = f"{clean_part_0}-pictures-{parts[1]}"
        else:
            image_id = base_id

        info = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{base_id}", timeout=10).json()
        imgs_data = requests.get(f"https://tkphsp2.vercel.app/gsm/images/{image_id}", timeout=10).json()

        img_list = imgs_data.get('images', [])
        if len(img_list) > 1:
            api_img = img_list[1]
        elif len(img_list) == 1:
            api_img = img_list[0]
        else:
            api_img = search_res[0].get('image', CONFIG["placeholder_phone"])

        chip = info.get("platform", {}).get("chipset", "High Performance").split('(')[0].strip()
        display_raw = info.get("display", {}).get("size", "6.7 inches")
        screen = display_raw.split(',')[0].strip()

        mem_data = info.get("memory", {})
        if isinstance(mem_data, list) and len(mem_data) > 0:
            mem_raw = mem_data[0].get("internal", "128GB 8GB RAM")
        elif isinstance(mem_data, dict):
            mem_raw = mem_data.get("internal", "128GB 8GB RAM")
        else:
            mem_raw = "128GB 8GB RAM"
        memory = mem_raw.split(',')[0].strip()

        batt_raw = info.get("battery", {}).get("battType", "5000 mAh")
        batt_match = re.search(r'(\d+)\s*mAh', str(batt_raw))
        battery = f"{batt_match.group(1)} mAh" if batt_match else "5000 mAh"

        return {
            "source": "gsmarena",
            "name": official_name, 
            "img_url": api_img,
            "price": "0",
            "specs": [
                ("processor", chip), 
                ("screen", screen), 
                ("memory", memory), 
                ("battery", battery)
            ]
        }

    except Exception as e:
        return {**dummy, "price": "0", "source": "gsm_fallback"}

def fetch_device_data(query):
    """Unified fetch: WooCommerce first, GSM Arena fallback"""
    wc_data = fetch_woocommerce_data(query)
    if wc_data:
        return wc_data

    st.info("Not found in store inventory. Falling back to GSM Arena...")
    return fetch_gsmarena_data(query)

# ==========================================
# 3. TEXT WRAPPING UTILITIES
# ==========================================
def get_text_width(text, font_size):
    """Estimate text width based on font size (rough approximation)"""
    # Average character width is roughly 0.6 * font_size for typical fonts
    return len(text) * int(font_size * 0.6)

def wrap_text_to_width(text, font_size, max_width):
    """Wrap text to fit within max_width pixels"""
    if not text:
        return [""]

    # Calculate max characters per line
    avg_char_width = font_size * 0.55  # Slightly conservative estimate
    max_chars = max(1, int(max_width / avg_char_width))

    # Use textwrap with the calculated width
    wrapped = textwrap.wrap(text, width=max_chars, break_long_words=True, replace_whitespace=False)

    if not wrapped:
        return [text]

    return wrapped

def draw_wrapped_text(draw, text, position, font_size, fill, anchor=None, max_width=None, line_spacing=1.2):
    """Draw text with automatic wrapping. Returns total height used."""
    if max_width is None:
        # Default: canvas width minus some padding
        max_width = 1000

    x, y = position
    lines = wrap_text_to_width(text, font_size, max_width)

    line_height = int(font_size * line_spacing)

    for i, line in enumerate(lines):
        line_y = y + (i * line_height)
        if anchor and "m" in str(anchor):
            # For centered text, we need to handle each line
            draw.text((x, line_y), line, fill=fill, font_size=font_size, anchor="lm")
        else:
            draw.text((x, line_y), line, fill=fill, font_size=font_size)

    return len(lines) * line_height

# ==========================================
# 4. MOTION GRAPHICS ENGINE
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
    canvas_w, canvas_h = cfg["canvas"]

    # Use price from data if available (WooCommerce), else use user input
    display_price = data.get("price", price)
    if display_price == "0" or not display_price:
        display_price = price

    # Format price with commas
    try:
        price_int = int(display_price)
        display_price = f"{price_int:,}"
    except:
        display_price = str(display_price)

    # === TITLE: Wrapped and centered ===
    name = data["name"].upper()
    if t is not None: 
        name = name[:int(len(name) * min(t/1.5, 1.0))]

    # Title max width: leave 80px padding on each side
    title_max_w = canvas_w - 160
    title_lines = wrap_text_to_width(name, CONFIG["fonts"]["title"], title_max_w)

    title_line_height = int(CONFIG["fonts"]["title"] * 1.1)
    title_total_h = len(title_lines) * title_line_height
    title_y = cfg["title_pos"][1] - (title_total_h // 2) + (title_line_height // 2)

    for i, line in enumerate(title_lines):
        line_y = title_y + (i * title_line_height)
        draw.text((cfg["title_pos"][0], line_y), line, fill="white", 
                  font_size=CONFIG["fonts"]["title"], anchor="mm")

    # === SPECS: Wrapped to fit in right column ===
    sx, sy = cfg["spec_start"]
    # Max width for specs: from spec_start to canvas edge minus padding
    spec_max_w = canvas_w - sx - 40  # 40px right padding

    for i, (icon_name, val) in enumerate(data["specs"]):
        if t is not None and t < (1.5 + i * 0.2): 
            continue

        y = sy + (i * 95)
        icon = load_asset(CONFIG["icons"][icon_name], size=CONFIG["sizes"]["spec_icon"])
        overlay.paste(icon, (sx, y), icon)

        # Wrap spec text
        spec_text_x = sx + 60
        spec_max_text_w = spec_max_w - 60  # Account for icon width + gap
        spec_lines = wrap_text_to_width(val, CONFIG["fonts"]["specs"], spec_max_text_w)

        spec_line_h = int(CONFIG["fonts"]["specs"] * 1.15)
        for j, line in enumerate(spec_lines):
            line_y = y + 5 + (j * spec_line_h)
            draw.text((spec_text_x, line_y), line, fill="white", 
                      font_size=CONFIG["fonts"]["specs"])

    # === PRICE BADGE ===
    if t is None or t > 3.5:
        badge_box = [sx, sy + 480, sx + 320, sy + 560]
        draw.rounded_rectangle(badge_box, radius=CONFIG["sizes"]["badge_radius"], 
                               fill=CONFIG["colors"]["mint"])
        draw.text((sx + 160, sy + 520), f"KES {display_price}", fill="white", 
                  font_size=CONFIG["fonts"]["price"], anchor="mm")

    return overlay

# ==========================================
# 5. FINAL ASSEMBLY
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

    st.caption("Primary: Tripple K Store API | Fallback: GSM Arena")

    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input("Device Name", "Samsung Galaxy S26")
    price = c2.text_input("Price (Override)", "145,000")
    mode = c3.selectbox("Format", ["whatsapp", "tiktok"])

    if st.button("Generate Assets", use_container_width=True):
        with st.spinner("Fetching product data..."):
            data = fetch_device_data(query)

        # Show which source was used
        source_badge = "🛒 Store" if data.get("source") == "woocommerce" else "📱 GSM Arena"
        st.success(f"Source: {source_badge}")

        # Debug: show the image URL being used
        with st.expander("Debug: Image URL"):
            st.code(data.get("img_url", "None"))

        # Display static preview
        cfg = CONFIG["layouts"][mode]
        bg = create_gradient_bg(cfg["canvas"][0], cfg["canvas"][1])
        base = create_base_layer(mode, data)
        bg.paste(base, (0,0), base)
        st.image(add_animation_overlay(bg, mode, data, price))

        with st.spinner("Rendering Animation..."):
            st.video(generate_video(mode, data, price))

if __name__ == "__main__": 
    main()
