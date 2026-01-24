import streamlit as st
import requests
import re
import io
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# DATA CATEGORIES & PATTERNS
# ============================================================================

CATEGORIES = {
    "Bluetooth Speakers": {
        "sites": ["fgee.co.ke", "smartphoneskenya.co.ke"],
        "patterns": {
            "Price": r"(?:KShs?|Ksh)\s*([\d,]+)",
            "Power": r"(\d+W\s*(?:RMS|Power)?)",
            "Playtime": r"(\d+\s*(?:hrs?|hours?)\s*play(?:time)?)",
            "BT Version": r"(?:Bluetooth|BT)\s*(?:Version)?\s*(\d+\.\d+)",
            "Waterproof": r"(IPX[0-7]|Waterproof|Splashproof)"
        }
    },
    "Earpods/Earbuds": {
        "sites": ["smartphoneskenya.co.ke", "fgee.co.ke"],
        "patterns": {
            "Price": r"(?:KShs?|Ksh)\s*([\d,]+)",
            "Total Playtime": r"(\d+\s*(?:hours?|hrs?)\s*(?:total|with\s*case))",
            "Charging": r"(Type-C|Wireless Charging|Lightning)",
            "Features": r"(ANC|Active Noise Cancelling|ENC|Transparency Mode)",
            "BT Version": r"(?:Bluetooth|BT)\s*(\d+\.\d+)"
        }
    }
}

# ============================================================================
# SEARCH ENGINE (Surgical Extraction)
# ============================================================================

class OraimoEngine:
    def __init__(self):
        self.session = requests.Session()
        self.api_url = "https://far-paule-emw-a67bd497.koyeb.app/search"

    def surgical_search(self, model_query, category_name):
        config = CATEGORIES[category_name]
        all_products = []
        
        # Search across specified high-quality sites
        for site in config["sites"]:
            full_query = f"site:{site} Oraimo {model_query}"
            params = {"q": full_query, "categories": "general", "format": "json"}
            
            try:
                resp = self.session.get(self.api_url, params=params, timeout=20)
                results = resp.json().get("results", [])
                
                for r in results:
                    snippet = r.get('content', '')
                    title = r.get('title', '')
                    
                    # 1. Extract Name
                    official_name = title.split('|')[0].split('-')[0].strip()
                    
                    # 2. Extract Data using Category Regex
                    extracted_specs = []
                    price = "Ksh 0"
                    
                    for key, pattern in config["patterns"].items():
                        match = re.search(pattern, snippet, re.IGNORECASE)
                        if match:
                            val = match.group(0 if key != "Price" else 1)
                            if key == "Price":
                                price = f"Ksh {int(val.replace(',', '')):,}"
                            else:
                                extracted_specs.append(val.strip().upper())
                    
                    # Only add if we found at least a price or some specs
                    if len(extracted_specs) > 0 or price != "Ksh 0":
                        all_products.append({
                            "name": official_name,
                            "price": price,
                            "features": extracted_specs[:4], # Top 4 specs for poster
                            "site": site
                        })
            except Exception as e:
                continue
                
        return all_products

# ============================================================================
# POSTER DESIGNER (Story Format 1080x1920)
# ============================================================================

class PosterDesigner:
    def create(self, product, img_obj):
        # Canvas & Background
        canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Fonts
        try:
            f_title = ImageFont.truetype("poppins.ttf", 85)
            f_price = ImageFont.truetype("poppins.ttf", 70)
            f_feat = ImageFont.truetype("poppins.ttf", 40)
            f_cta = ImageFont.truetype("poppins.ttf", 45)
        except:
            f_title = f_price = f_feat = f_cta = ImageFont.load_default()

        # Product Image (Resized to 900x900 area)
        img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
        canvas.paste(img_obj, ((1080 - img_obj.width)//2, 380), img_obj)

        # Content
        draw.text((540, 200), product['name'].upper(), font=f_title, fill=(0,0,0), anchor="mm")
        draw.text((540, 320), product['price'], font=f_price, fill=(0, 180, 0), anchor="mm")

        # Vertical Features
        y = 1350
        for feat in product['features']:
            draw.text((540, y), f"✓ {feat}", font=f_feat, fill=(50, 50, 50), anchor="mm")
            y += 75

        # Footer CTA
        draw.rectangle([200, 1700, 880, 1830], fill=(0, 0, 0))
        draw.text((540, 1765), "ORDER NOW @ ORAIMO", font=f_cta, fill=(255, 255, 255), anchor="mm")

        return canvas

# ============================================================================
# UI LOGIC
# ============================================================================

st.set_page_config(page_title="Oraimo Designer", layout="wide")

# Sidebar for Category selection
with st.sidebar:
    st.header("Settings")
    cat_choice = st.selectbox("Select Category", list(CATEGORIES.keys()))

# Tab Logic
t1, t2, t3 = st.tabs(["Search", "Select Image", "Download"])

with t1:
    model = st.text_input(f"Model Name (in {cat_choice})", "FreePods 4")
    if st.button("Search Targeted Sites"):
        engine = OraimoEngine()
        st.session_state.prods = engine.surgical_search(model, cat_choice)

    if 'prods' in st.session_state:
        for idx, p in enumerate(st.session_state.prods):
            c1, c2 = st.columns([4, 1])
            c1.info(f"**{p['name']}** from {p['site']} | {p['price']}")
            if c2.button("Use Info", key=f"sel_{idx}"):
                st.session_state.sel = p
                # Image search using the official name
                params = {"q": f'"{p["name"]}" product transparent png 900x900', "categories": "images", "format": "json"}
                resp = requests.get("https://far-paule-emw-a67bd497.koyeb.app/search", params=params)
                st.session_state.imgs = [i for i in resp.json().get("results", []) if "900" in i.get('resolution', '')]
                st.rerun()

# 

with t2:
    if 'sel' in st.session_state:
        st.write(f"### High-Res Images for {st.session_state.sel['name']}")
        cols = st.columns(3)
        for idx, im in enumerate(st.session_state.imgs[:9]):
            with cols[idx % 3]:
                st.image(im['img_src'], use_container_width=True)
                if st.button("Generate Poster", key=f"gen_{idx}"):
                    raw = Image.open(io.BytesIO(requests.get(im['img_src']).content)).convert("RGBA")
                    st.session_state.final = PosterDesigner().create(st.session_state.sel, raw)
                    st.success("Poster Created!")

with t3:
    if 'final' in st.session_state:
        st.image(st.session_state.final)
        b = io.BytesIO()
        st.session_state.final.save(b, format="PNG")
        st.download_button("Download Story", b.getvalue(), "poster.png")
