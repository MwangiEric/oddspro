import streamlit as st
import requests
import re
import io
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "search": {
        "api_url": "https://far-paule-emw-a67bd497.koyeb.app/search",
        "timeout": 45,
    },
    "images": {
        "min_width": 900,
        "min_height": 900,
    },
    "fonts": {
        "primary": "poppins.ttf", # Exact lowercase filename
        "sizes": {
            "title": 85,
            "features": 36,
            "price": 60,
            "cta": 45,
            "footer": 22
        }
    },
    "poster": {
        "size": (1080, 1920),
        "product_area_size": 950,
    }
}

# ============================================================================
# EXTRACTION & SEARCH LOGIC
# ============================================================================

def get_font(size):
    """Load poppins.ttf with error handling"""
    try:
        return ImageFont.truetype(CONFIG["fonts"]["primary"], size)
    except OSError:
        return ImageFont.load_default()

def extract_official_name(title):
    """Cleans search titles to get the specific model name"""
    # Remove common e-commerce suffixes
    name = title.split('|')[0].split('-')[0].split('(')[0]
    return name.strip()

def extract_price(content):
    match = re.search(r"(?:Ksh|KSH|Kes)\s*([\d,]+)", content, re.IGNORECASE)
    if match:
        return f"Ksh {int(match.group(1).replace(',', '')):,}"
    return "Check Price"

def extract_features(content):
    keywords = ["battery", "waterproof", "bass", "noise", "bluetooth", "charging", "enc", "anc", "fast"]
    found = [word.upper() for word in keywords if word in content.lower()]
    return found[:5] if found else ["PREMIUM AUDIO", "SMART TOUCH", "LONG PLAYTIME"]

class OraimoEngine:
    def __init__(self):
        self.session = requests.Session()

    def find_products(self, query):
        params = {"q": f"{query} Oraimo official", "categories": "general", "format": "json"}
        try:
            resp = self.session.get(CONFIG["search"]["api_url"], params=params, timeout=30)
            results = resp.json().get("results", [])
            data = []
            for r in results:
                official_name = extract_official_name(r.get('title', ''))
                data.append({
                    "name": official_name,
                    "price": extract_price(r.get('content', '')),
                    "features": extract_features(r.get('content', '')),
                    "source": r.get('url', '')
                })
            return data
        except: return []

    def find_images(self, official_name):
        # Using the cleaned official name for specific image search
        query = f'"{official_name}" product transparent background png'
        params = {"q": query, "categories": "images", "format": "json"}
        try:
            resp = self.session.get(CONFIG["search"]["api_url"], params=params, timeout=30)
            imgs = resp.json().get("results", [])
            valid = []
            for img in imgs:
                res = img.get('resolution', '0x0')
                match = re.search(r'(\d+)\s*x\s*(\d+)', res)
                if match and int(match.group(1)) >= 900 and int(match.group(2)) >= 900:
                    valid.append(img)
            return valid
        except: return []

# ============================================================================
# POSTER DESIGNER
# ============================================================================

class PosterDesigner:
    def create(self, product, img_obj):
        # 1. Canvas
        canvas = Image.new('RGBA', CONFIG["poster"]["size"], (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # 2. Layout Elements
        img_obj.thumbnail((950, 950), Image.Resampling.LANCZOS)
        canvas.paste(img_obj, ((1080 - img_obj.width)//2, 350), img_obj)

        # 3. Text Styling (poppins.ttf)
        font_title = get_font(CONFIG["fonts"]["sizes"]["title"])
        font_feat = get_font(CONFIG["fonts"]["sizes"]["features"])
        font_price = get_font(CONFIG["fonts"]["sizes"]["price"])
        font_cta = get_font(CONFIG["fonts"]["sizes"]["cta"])

        # Name & Price
        draw.text((540, 200), product['name'].upper(), font=font_title, fill=(0, 0, 0), anchor="mm")
        draw.text((540, 310), product['price'], font=font_price, fill=(0, 180, 0), anchor="mm")

        # Features (Centered List)
        y_feat = 1350
        for f in product['features']:
            draw.text((540, y_feat), f"⚡ {f}", font=font_feat, fill=(60, 60, 60), anchor="mm")
            y_feat += 70

        # 4. CTA Section (Bottom)
        draw.rectangle([240, 1720, 840, 1840], fill=(0, 0, 0)) # Black Button
        draw.text((540, 1780), "SHOP NOW @ ORAIMO", font=font_cta, fill=(255, 255, 255), anchor="mm")

        return canvas

# ============================================================================
# STREAMLIT APP
# ============================================================================

st.set_page_config(page_title="Oraimo Poster Gen", layout="wide")

if 'prods' not in st.session_state: st.session_state.prods = []
if 'sel' not in st.session_state: st.session_state.sel = None
if 'imgs' not in st.session_state: st.session_state.imgs = []
if 'final' not in st.session_state: st.session_state.final = None

t1, t2, t3 = st.tabs(["Search", "Pick Image", "Export"])

with t1:
    user_query = st.text_input("Product Model", "Oraimo Watch 4 Plus")
    if st.button("Search Products"):
        st.session_state.prods = OraimoEngine().find_products(user_query)
    
    for p in st.session_state.prods:
        c1, c2 = st.columns([4, 1])
        c1.info(f"**{p['name']}** | {p['price']}")
        if c2.button("Select Model", key=p['name']):
            st.session_state.sel = p
            # Search images using the extracted official name
            st.session_state.imgs = OraimoEngine().find_images(p['name'])
            st.rerun()

with t2:
    if st.session_state.sel:
        st.write(f"### Images for: {st.session_state.sel['name']}")
        cols = st.columns(3)
        for i, im in enumerate(st.session_state.imgs[:9]):
            with cols[i % 3]:
                st.image(im['img_src'], use_container_width=True)
                st.caption(im['resolution'])
                if st.button("Design Poster", key=f"gen_{i}"):
                    resp = requests.get(im['img_src'])
                    raw_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                    st.session_state.final = PosterDesigner().create(st.session_state.sel, raw_img)
                    st.success("Poster Generated!")
    else: st.info("Select a product first.")

with t3:
    if st.session_state.final:
        st.image(st.session_state.final)
        b = io.BytesIO()
        st.session_state.final.save(b, format="PNG")
        st.download_button("Download Story Poster", b.getvalue(), "oraimo_poster.png")
