import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import io
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION
# ============================================================================
CONFIG = {
    "url": "https://www.priceinkenya.com/price-list/bluetooth-speakers",
    "search_api": "https://far-paule-emw-a67bd497.koyeb.app/search",
    "font_file": "poppins.ttf", # Your secondary fallback font
    "poster_size": (1080, 1920)
}

# ============================================================================
# SURGICAL HTML SCRAPER
# ============================================================================
def get_live_inventory():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(CONFIG["url"], headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Target the specific table body from your HTML
        table_body = soup.find('tbody', class_='bg-white divide-y divide-gray-100')
        rows = table_body.find_all('tr') if table_body else []
        
        products = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                # 1. Name: Extract text and split at the first comma
                full_name = cells[0].get_text(strip=True)
                clean_name = full_name.split(',')[0].strip()
                
                # 2. Price: Extract numeric digits only
                price_text = cells[1].get_text(strip=True)
                price_clean = re.sub(r'[^\d]', '', price_text)
                
                if clean_name and price_clean:
                    products.append({
                        "name": clean_name,
                        "price": f"Ksh {int(price_clean):,}",
                        "search_term": clean_name
                    })
        return products
    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return []

# ============================================================================
# POSTER DESIGNER (1080x1920)
# ============================================================================
class OraimoDesigner:
    def create(self, product, img_obj):
        # Create Canvas
        canvas = Image.new('RGBA', CONFIG["poster_size"], (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Load Fonts
        try:
            f_title = ImageFont.truetype(CONFIG["font_file"], 95)
            f_price = ImageFont.truetype(CONFIG["font_file"], 85)
            f_cta = ImageFont.truetype(CONFIG["font_file"], 55)
        except:
            f_title = f_price = f_cta = ImageFont.load_default()

        # Scale & Paste Image (Targeting 900x900 area)
        img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
        canvas.paste(img_obj, ((1080 - img_obj.width)//2, 450), img_obj)

        # Draw Text
        draw.text((540, 250), product['name'].upper(), font=f_title, fill=(0,0,0), anchor="mm")
        draw.text((540, 380), product['price'], font=f_price, fill=(0, 180, 0), anchor="mm")

        # CTA Button
        draw.rectangle([180, 1700, 900, 1850], fill=(0, 0, 0))
        draw.text((540, 1775), "ORDER NOW @ ORAIMO", font=f_cta, fill=(255, 255, 255), anchor="mm")

        return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Poster Lab", layout="wide")

if 'items' not in st.session_state: st.session_state.items = []
if 'img_results' not in st.session_state: st.session_state.img_results = []
if 'final_poster' not in st.session_state: st.session_state.final_poster = None

st.title("📱 Social Media Poster Generator")

t1, t2, t3 = st.tabs(["1. Market List", "2. Select Visual", "3. Export"])

with t1:
    if st.button("Sync with Live Site"):
        st.session_state.items = get_live_inventory()
    
    # Filter for brand
    brand_filter = st.text_input("Filter results (e.g., JBL, Anker)", "")
    
    display_list = [i for i in st.session_state.items if brand_filter.lower() in i['name'].lower()]
    
    for idx, item in enumerate(display_list):
        c1, c2 = st.columns([5, 1])
        c1.info(f"**{item['name']}** — {item['price']}")
        if c2.button("Select", key=f"sel_{idx}"):
            st.session_state.active_prod = item
            # Use SearXNG to find high-res PNG
            q = f'"{item["name"]}" product transparent background png'
            resp = requests.get(CONFIG["search_api"], params={"q": q, "categories": "images", "format": "json"})
            # Check for 900 in resolution for crispness
            st.session_state.img_results = [r for r in resp.json().get("results", []) if "900" in r.get('resolution', '0')]
            st.rerun()

with t2:
    if 'active_prod' in st.session_state:
        st.write(f"### Visuals for {st.session_state.active_prod['name']}")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.img_results[:9]):
            with cols[i % 3]:
                st.image(img['img_src'], use_container_width=True)
                if st.button("Generate Poster", key=f"img_btn_{i}"):
                    raw = requests.get(img['img_src']).content
                    pil_img = Image.open(io.BytesIO(raw)).convert("RGBA")
                    st.session_state.final_poster = OraimoDesigner().create(st.session_state.active_prod, pil_img)
                    st.success("Design Created!")
    else: st.info("Go to Tab 1 and sync/select an item.")

with t3:
    if st.session_state.final_poster:
        st.image(st.session_state.final_poster)
        buf = io.BytesIO()
        st.session_state.final_poster.save(buf, format="PNG")
        st.download_button("Download for Instagram/WhatsApp", buf.getvalue(), "oraimo_poster.png")
