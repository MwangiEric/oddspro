import streamlit as st
import requests
import numpy as np
import re
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime

# ============================================================================
# CONFIG & FONT ENGINE (HD ARIAL & VERDANA FALLBACK)
# ============================================================================
CONFIG = {
    "fonts": {"primary": "arial.ttf", "fallback": "Verdana.ttf"},
    "platforms": {
        "POSTER": {"size": (1200, 1600), "type": "TALL"},
        "STORY": {"size": (1080, 1920), "type": "TALL"},
        "WIDE": {"size": (1200, 628), "type": "WIDE"}
    }
}

def get_hd_font(size, bold=False):
    """Ensures sharp vector text rendering"""
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(font_name, size)
    except:
        try: return ImageFont.truetype("Verdana.ttf", size) # Your preferred fallback
        except: return ImageFont.load_default()

# ============================================================================
# FEATURE 1 & 2: MARKET INTELLIGENCE & SPECS EXTRACTION
# ============================================================================
def extract_marketing_insights(results):
    """Extracts prices for comparison and units for spec sheets"""
    prices = []
    specs = []
    
    unit_patterns = [r"\d+\s?mAh", r"\d+\s?GB", r"\d+\.?\d*\s?inches", r"BT\s?\d\.\d"]
    
    for r in results:
        text = f"{r.get('title', '')} {r.get('content', '')}"
        # Extract Prices
        found_prices = re.findall(r"(?:Ksh|KES)\s?([\d,]{3,})", text, re.I)
        prices.extend([int(p.replace(',', '')) for p in found_prices])
        # Extract Specs
        for pat in unit_patterns:
            match = re.search(pat, text, re.I)
            if match: specs.append(match.group())
            
    return {
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "quick_specs": list(set(specs))[:4]
    }

# ============================================================================
# NUMPY COLOR DETECTION & GENERATOR
# ============================================================================
class MarketingGenerator:
    def __init__(self, hd_image):
        self.hd_image = hd_image.convert("RGBA")
        self.theme_color = self.detect_color()

    def detect_color(self):
        img = self.hd_image.copy()
        img.thumbnail((100, 100))
        data = np.array(img)
        r, g, b, a = data.T
        mask = (a > 100) & ~((r > 240) & (g > 240) & (b > 240)) # Ignore transparency/white
        pixels = data[mask.T]
        return tuple(np.mean(pixels[:, :3], axis=0).astype(int)) if len(pixels) > 0 else (70, 130, 180)

    def generate(self, name, price, insights, platform_key):
        cfg = CONFIG["platforms"][platform_key]
        w, h = cfg["size"]
        
        # Create High-Res Canvas
        canvas = Image.new('RGBA', (w, h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Soft Gradient Background
        for i in range(h):
            alpha = int(35 * (i / h))
            draw.line([(0, i), (w, i)], fill=(*self.theme_color, alpha))

        # Layout Logic
        if cfg["type"] == "WIDE":
            # Image on left, Info on right
            prod = self.hd_image.copy()
            prod.thumbnail((w//2, h-100), Image.Resampling.LANCZOS)
            canvas.paste(prod, (50, (h-prod.size[1])//2), prod)
            
            draw.text((w//2 + 20, 150), name.upper(), font=get_hd_font(50, True), fill=(40,40,40))
            draw.text((w//2 + 20, 240), f"Ksh {price:,}", font=get_hd_font(70, True), fill=self.theme_color)
        else:
            # Vertical Stack
            prod = self.hd_image.copy()
            prod.thumbnail((w-200, h//2), Image.Resampling.LANCZOS)
            canvas.paste(prod, ((w-prod.size[0])//2, 250), prod)
            
            draw.text((w//2, h-450), name.upper(), font=get_hd_font(80, True), fill=(40,40,40), anchor="mm")
            draw.text((w//2, h-320), f"Ksh {price:,}", font=get_hd_font(90, True), fill=self.theme_color, anchor="mm")
            
            # Add Spec Badges
            for i, spec in enumerate(insights['quick_specs']):
                draw.text((w//2, h-220 + (i*40)), f"• {spec}", font=get_hd_font(30), fill=(100,100,100), anchor="mm")

        return canvas

# ============================================================================
# STREAMLIT UI: PREVIEW GALLERY
# ============================================================================
st.set_page_config(layout="wide")
st.title("🎨 Universal Marketing Suite")

# Step 1: Search (Mock logic for brevity)
query = st.text_input("Product Name", "Sony WH-1000XM5")
if st.button("🔍 Analyze & Search"):
    # Imagine this fetches from your API
    st.session_state.results = [{"content": "Sony XM5 Ksh 45,000, BT 5.2, 30h battery", "url": "...", "thumbnail_src": "..."}]
    st.session_state.hd_url = "https://example.com/hd_sony.png" # Selected from thumbnails

# Step 2: Multi-Platform Preview
if 'hd_url' in st.session_state:
    insights = extract_marketing_insights(st.session_state.results)
    
    # HD Download & Process
    raw_img = Image.open(requests.get(st.session_state.hd_url, stream=True).raw)
    engine = MarketingGenerator(raw_img)
    
    st.subheader("🖼️ Live Multi-Platform Preview")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.caption("Professional Poster")
        st.image(engine.generate(query, 45000, insights, "POSTER"))
        
    with c2:
        st.caption("Instagram Story")
        st.image(engine.generate(query, 45000, insights, "STORY"))
        
    with c3:
        st.caption("E-commerce Wide")
        st.image(engine.generate(query, 45000, insights, "WIDE"))

    # Feature 1: Market Intelligence Display
    st.info(f"📊 **Market Analysis:** Found prices ranging from Ksh {insights['min_price']:,} to Ksh {insights['max_price']:,}")
