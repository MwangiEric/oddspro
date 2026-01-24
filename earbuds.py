import streamlit as st
import requests
import json
import re
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "search": {
        "api_url": "https://far-paule-emw-a67bd497.koyeb.app/search",
        "timeout": 45,
    },
    "images": {
        "min_width": 900,  # Enforced 900x900
        "min_height": 900,
    },
    "fonts": {
        "primary": "arial.ttf", # PIL default system access
        "sizes": {
            "title": 80,
            "price_badge": 52,
            "features": 34,
            "footer": 24
        }
    },
    "poster": {
        "size": (1200, 1600),
        "margins": 80,
        "product_max_size": 750,
    }
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_font(size):
    """Load standard arial.ttf from system via PIL"""
    try:
        return ImageFont.truetype(CONFIG["fonts"]["primary"], size)
    except OSError:
        # Fallback to default if arial.ttf is inaccessible
        return ImageFont.load_default()

def download_image(url):
    try:
        response = requests.get(url, timeout=20)
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        return None

def extract_official_product_name(search_results):
    name_patterns = [r"(Oraimo\s+[\w\s\-]+\d+\w*)", r"(FreePods\s+\d+\w*)"]
    for result in search_results:
        content = f"{result.get('title', '')} {result.get('content', '')}"
        for pattern in name_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match: return match.group(1).strip()
    return "Oraimo Product"

# ============================================================================
# SEARCH & FILTERING
# ============================================================================

class OraimoSearchEngine:
    def __init__(self):
        self.session = requests.Session()

    def search_products(self, query):
        params = {"q": f"{query} Oraimo Kenya", "categories": "general", "format": "json"}
        try:
            resp = self.session.get(CONFIG["search"]["api_url"], params=params, timeout=30)
            results = resp.json().get("results", [])
            return self.process_results(results)
        except: return []

    def process_results(self, results):
        products = {}
        for r in results:
            name = extract_official_product_name([r])
            if name not in products:
                products[name] = {
                    "name": name,
                    "highest_price": 5500, # Placeholder or extracted logic
                    "features": ["True Wireless", "Heavy Bass", "Long Battery"],
                    "description": r.get('title', '')
                }
        return list(products.values())

    def search_images(self, product_name):
        # Specific query for high-res transparent PNGs
        query = f'"{product_name}" product transparent png high resolution'
        params = {"q": query, "categories": "images", "format": "json"}
        try:
            resp = self.session.get(CONFIG["search"]["api_url"], params=params, timeout=30)
            raw_imgs = resp.json().get("results", [])
            
            # STRICT 900x900 FILTER
            valid_imgs = []
            for img in raw_imgs:
                res = img.get('resolution', '0x0')
                match = re.search(r'(\d+)\s*x\s*(\d+)', res)
                if match:
                    w, h = int(match.group(1)), int(match.group(2))
                    if w >= 900 and h >= 900:
                        valid_imgs.append(img)
            return valid_imgs
        except: return []

# ============================================================================
# POSTER GENERATOR
# ============================================================================

class OraimoPosterGenerator:
    def generate_poster(self, product, product_image):
        # 1. Background
        poster = Image.new('RGBA', CONFIG["poster"]["size"], (250, 250, 250, 255))
        draw = ImageDraw.Draw(poster)
        
        # Simple Gradient Overlay
        for i in range(1600):
            draw.line([(0, i), (1200, i)], fill=(0, 150, 0, int(30 * (i/1600))))

        # 2. Product Image Scaling
        max_dim = CONFIG["poster"]["product_max_size"]
        product_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
        img_x = (1200 - product_image.width) // 2
        poster.paste(product_image, (img_x, 200), product_image)

        # 3. Text Elements (Arial)
        title_font = get_font(CONFIG["fonts"]["sizes"]["title"])
        draw.text((600, 1050), product['name'].upper(), font=title_font, fill=(30, 30, 30), anchor="mm")
        
        # 4. Price Badge
        badge_font = get_font(CONFIG["fonts"]["sizes"]["price_badge"])
        draw.ellipse([850, 50, 1100, 300], fill=(0, 200, 0, 230))
        draw.text((975, 175), f"Ksh\n{product['highest_price']:,}", font=badge_font, fill=(255, 255, 255), anchor="mm", align="center")

        return poster

# ============================================================================
# APP UI
# ============================================================================

st.set_page_config(page_title="Oraimo Poster Pro", layout="wide")

if 'products' not in st.session_state: st.session_state.products = []
if 'selected_product' not in st.session_state: st.session_state.selected_product = None
if 'img_results' not in st.session_state: st.session_state.img_results = []
if 'final_poster' not in st.session_state: st.session_state.final_poster = None

tab1, tab2, tab3 = st.tabs(["Find Product", "Pick High-Res Image", "Download"])

with tab1:
    q = st.text_input("Product Name", "Oraimo FreePods 4")
    if st.button("Search Products"):
        st.session_state.products = OraimoSearchEngine().search_products(q)
    
    for p in st.session_state.products:
        col1, col2 = st.columns([4,1])
        col1.write(f"**{p['name']}**")
        if col2.button("Select", key=p['name']):
            st.session_state.selected_product = p
            st.session_state.img_results = OraimoSearchEngine().search_images(p['name'])
            st.rerun()

with tab2:
    if st.session_state.selected_product:
        st.write(f"### Select high-res image for {st.session_state.selected_product['name']}")
        if not st.session_state.img_results:
            st.warning("No images found with 900x900+ resolution.")
        else:
            # GRID UI (3 Columns)
            cols = st.columns(3)
            for idx, img in enumerate(st.session_state.img_results[:9]): # Limit to top 9
                with cols[idx % 3]:
                    st.image(img['img_src'], use_container_width=True)
                    st.caption(f"Resolution: {img['resolution']}")
                    if st.button(f"Pick Image {idx+1}", key=f"sel_{idx}"):
                        loaded_img = download_image(img['img_src'])
                        if loaded_img:
                            st.session_state.final_poster = OraimoPosterGenerator().generate_poster(st.session_state.selected_product, loaded_img)
                            st.success("Poster Generated!")
                        else:
                            st.error("Failed to download image.")
    else:
        st.info("Pick a product in Tab 1 first.")

with tab3:
    if st.session_state.final_poster:
        st.image(st.session_state.final_poster)
        buf = io.BytesIO()
        st.session_state.final_poster.save(buf, format="PNG")
        st.download_button("Download PNG", buf.getvalue(), "oraimo_poster.png", "image/png")
