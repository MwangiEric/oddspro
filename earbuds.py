import streamlit as st
import requests
import re
import io
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "scraper_url": "https://www.priceinkenya.com/price-list/bluetooth-speakers",
    "search_api": "https://far-paule-emw-a67bd497.koyeb.app/search",
    "poster_size": (1080, 1920),
    "font_file": "poppins.ttf" 
}

# ============================================================================
# REFINED SCRAPER
# ============================================================================

def get_live_price_list():
    """Parses the specific table structure from PriceInKenya"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(CONFIG["scraper_url"], headers=headers, timeout=15)
        
        # We look for the pattern: Name with comma -> Price -> Date
        # Based on your sample: "Anker Soundcore Pyro Mini, Bluetooth Speaker 4,000 August, 2024"
        raw_text = response.text
        
        # Regex to find: Name (before comma), Full Description, and Price
        # This targets the table rows specifically
        pattern = r"([^,\n]+),\s*([^0-9\n]+)\s+([\d,]+)"
        matches = re.findall(pattern, raw_text)
        
        products = []
        for match in matches:
            official_name = match[0].strip() # Text before comma
            description = match[1].strip()   # Text after comma
            price = match[2].strip()        # Numeric price
            
            products.append({
                "name": official_name,
                "full_desc": f"{official_name}, {description}",
                "price": f"Ksh {price}",
                "search_query": official_name 
            })
        return products
    except Exception as e:
        st.error(f"Scrape failed: {e}")
        return []

# ============================================================================
# POSTER DESIGNER (1080x1920)
# ============================================================================

class PosterDesigner:
    def create(self, product, img_obj):
        canvas = Image.new('RGBA', CONFIG["poster_size"], (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        try:
            f_name = ImageFont.truetype(CONFIG["font_file"], 95)
            f_price = ImageFont.truetype(CONFIG["font_file"], 80)
            f_cta = ImageFont.truetype(CONFIG["font_file"], 50)
        except:
            f_name = f_price = f_cta = ImageFont.load_default()

        # Image Scaling: Ensure it occupies the 900x900 center area
        img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
        canvas.paste(img_obj, ((1080 - img_obj.width)//2, 400), img_obj)

        # Text Elements
        draw.text((540, 200), product['name'].upper(), font=f_name, fill=(0,0,0), anchor="mm")
        draw.text((540, 320), product['price'], font=f_price, fill=(0, 180, 0), anchor="mm")

        # CTA Button
        draw.rectangle([200, 1720, 880, 1840], fill=(0, 0, 0))
        draw.text((540, 1770), "SHOP NOW @ ORAIMO", font=f_cta, fill=(255, 255, 255), anchor="mm")

        return canvas

# ============================================================================
# UI LOGIC
# ============================================================================

st.set_page_config(page_title="Oraimo Designer Pro", layout="wide")

if 'scraped_data' not in st.session_state: st.session_state.scraped_data = []
if 'selected_prod' not in st.session_state: st.session_state.selected_prod = None
if 'image_options' not in st.session_state: st.session_state.image_options = []
if 'final_poster' not in st.session_state: st.session_state.final_poster = None

st.title("📱 Social Media Poster Generator")

t1, t2, t3 = st.tabs(["1. Market Prices", "2. Pick Image", "3. Export"])

with t1:
    if st.button("Refresh Price List"):
        st.session_state.scraped_data = get_live_price_list()
    
    if st.session_state.scraped_data:
        # Display as a clean selection list
        for idx, item in enumerate(st.session_state.scraped_data):
            col1, col2 = st.columns([5, 1])
            col1.info(f"**{item['name']}** | {item['price']}")
            
            if col2.button("Select", key=f"prod_{idx}"):
                st.session_state.selected_prod = item
                # Surgical image search using the name before the comma
                query = f'"{item["name"]}" product transparent background png'
                resp = requests.get(CONFIG["search_api"], params={"q": query, "categories": "images", "format": "json"})
                
                # Filter for 900x900 resolution
                st.session_state.image_options = [
                    img for img in resp.json().get("results", []) 
                    if "900" in img.get('resolution', '0')
                ]
                st.rerun()

with t2:
    if st.session_state.selected_prod:
        st.write(f"### Select transparent image for {st.session_state.selected_prod['name']}")
        
        if not st.session_state.image_options:
            st.warning("No high-res transparent images found. Try selecting another product.")
        else:
            # Grid of images (3 columns)
            cols = st.columns(3)
            for i, img_data in enumerate(st.session_state.image_options[:9]):
                with cols[i % 3]:
                    st.image(img_data['img_src'], use_container_width=True)
                    st.caption(f"Res: {img_data['resolution']}")
                    if st.button("Use This Image", key=f"img_btn_{i}"):
                        img_bytes = requests.get(img_data['img_src']).content
                        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                        st.session_state.final_poster = PosterDesigner().create(st.session_state.selected_prod, pil_img)
                        st.success("Poster Designed!")
    else:
        st.info("Pick a product from the 'Market Prices' tab first.")

with t3:
    if st.session_state.final_poster:
        st.image(st.session_state.final_poster)
        buf = io.BytesIO()
        st.session_state.final_poster.save(buf, format="PNG")
        st.download_button("Download Story Poster", buf.getvalue(), "poster.png")
