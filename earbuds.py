import streamlit as st
import pandas as pd
import requests
import io
import re
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION & RELEVANT URLS
# ============================================================================
URL_MAP = {
    "Phones": "https://www.priceinkenya.com/price-list/phones",
    "Laptops": "https://www.priceinkenya.com/price-list/laptops",
    "TVs": "https://www.priceinkenya.com/price-list/tvs",
    "Smartwatches": "https://www.priceinkenya.com/price-list/smartwatches",
    "Soundbars": "https://www.priceinkenya.com/price-list/soundbars",
    "Video Game Consoles": "https://www.priceinkenya.com/price-list/video-game-consoles",
    "Bluetooth Speakers": "https://www.priceinkenya.com/price-list/bluetooth-speakers",
    "Hi-Fi Systems": "https://www.priceinkenya.com/price-list/hi-fi-systems",
    "Headphones": "https://www.priceinkenya.com/price-list/headphones"
}
SEARCH_API = "https://far-paule-emw-a67bd497.koyeb.app/search"
FALLBACK_FONT = "poppins.ttf" 

# ============================================================================
# COLOR & RESOLUTION UTILS
# ============================================================================
def get_adaptive_color(pil_img):
    """Detects dominant color and adjusts luminance for readability."""
    img = pil_img.copy().convert("RGBA")
    img.thumbnail((100, 100))
    # Extract colors from non-transparent pixels
    pixels = [p[:3] for p in img.getdata() if p[3] > 128]
    if not pixels: return (0, 0, 0)
    
    dom_color = max(set(pixels), key=pixels.count)
    # Luminance check to ensure text contrast
    lum = (0.299 * dom_color[0] + 0.587 * dom_color[1] + 0.114 * dom_color[2])
    
    if lum > 200: # Too light? Darken.
        return (int(dom_color[0]*0.6), int(dom_color[1]*0.6), int(dom_color[2]*0.6))
    if lum < 30: # Too dark? Lighten.
        return (80, 80, 80)
    return dom_color

def is_high_quality(res_string, threshold=800):
    if not res_string: return False
    dims = [int(s) for s in re.findall(r'\d+', res_string)]
    return max(dims) >= threshold if dims else False

# ============================================================================
# DATA ENGINE
# ============================================================================
@st.cache_data(ttl=3600)
def get_live_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        df = pd.read_html(io.StringIO(resp.text))[0]
        df.columns = ['Full_Name', 'Price_Raw', 'Date']
        
        # LOGIC: First comma for name - if no comma, take full cell
        def clean_name(val):
            val_str = str(val)
            return val_str.split(',')[0].strip() if ',' in val_str else val_str.strip()
            
        df['Clean_Name'] = df['Full_Name'].apply(clean_name)
        df['Price_Int'] = df['Price_Raw'].replace(r'[^\d]', '', regex=True).fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return pd.DataFrame()

# ============================================================================
# DESIGN ENGINE
# ============================================================================
def generate_poster(name, price, img_obj):
    theme_color = get_adaptive_color(img_obj)
    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Top Gradient
    for i in range(800):
        alpha = int(22 * (1 - i/800))
        draw.line([(0, i), (1080, i)], fill=theme_color + (alpha,))

    try:
        f_brand = ImageFont.truetype(FALLBACK_FONT, 115) 
        f_model = ImageFont.truetype(FALLBACK_FONT, 75)  
        f_price = ImageFont.truetype(FALLBACK_FONT, 95)
        f_contact = ImageFont.truetype(FALLBACK_FONT, 46)
    except:
        f_brand = f_model = f_price = f_contact = ImageFont.load_default()

    # Split: First word (Brand) vs Rest
    parts = name.split(' ', 1)
    brand_t = parts[0].upper()
    model_t = parts[1].upper() if len(parts) > 1 else ""
    
    draw.text((540, 240), brand_t, font=f_brand, fill=theme_color, anchor="mm")
    draw.text((540, 360), model_t, font=f_model, fill=(60, 60, 60), anchor="mm")

    # Product Visual
    img_obj.thumbnail((920, 920), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 520), img_obj)

    # Price Badge on Right
    p_text = f"KSH {price:,}"
    bbox = draw.textbbox((0,0), p_text, font=f_price)
    pad = 40
    bw, bh = (bbox[2]-bbox[0]) + pad*2, (bbox[3]-bbox[1]) + pad*2
    draw.rounded_rectangle([1080-bw-60, 1420, 1020, 1420+bh], radius=25, fill=theme_color)
    draw.text((1080-60-(bw/2), 1420+(bh/2)), p_text, font=f_price, fill=(255,255,255), anchor="mm")

    # Footer Contact Info
    draw.text((540, 1780), "WhatsApp / Call +254 733 565861 to order", 
              font=f_contact, fill=(30, 30, 30), anchor="mm")
    
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Poster Gen", layout="wide")
st.title("🛒 Multi-Category Poster Studio")

# 1. CATEGORY SELECTION
cat_choice = st.sidebar.selectbox("Select Category", list(URL_MAP.keys()))
df = get_live_data(URL_MAP[cat_choice])

if not df.empty:
    search_q = st.text_input(f"🔍 Search in {cat_choice}...")
    filtered = df[df['Clean_Name'].str.contains(search_q, case=False)]
    
    choice = st.selectbox("Pick product:", ["-- Select --"] + filtered['Clean_Name'].tolist())

    if choice != "-- Select --":
        selected_row = filtered[filtered['Clean_Name'] == choice].iloc[0]
        
        st.divider()
        st.write(f"### 2. Choose Image for {choice}")
        
        # Search API
        q = f'"{choice}" {cat_choice} transparent png'
        res = requests.get(SEARCH_API, params={"q": q, "format": "json"}).json()
        valid_list = [i for i in res.get('results', []) if is_high_quality(i.get('resolution', ''))][:9]
        
        if valid_list:
            cols = st.columns(3)
            for idx, img_data in enumerate(valid_list):
                with cols[idx % 3]:
                    st.image(img_data['img_src'], use_container_width=True)
                    if st.button("Use Image", key=f"btn_{idx}"):
                        try:
                            # Try to download and open the image
                            r_bytes = requests.get(img_data['img_src'], timeout=10).content
                            p_img = Image.open(io.BytesIO(r_bytes)).convert("RGBA")
                            
                            st.session_state.final_poster = generate_poster(
                                selected_row['Clean_Name'], 
                                selected_row['Price_Int'], 
                                p_img
                            )
                            st.success("Poster Created! Scroll down for preview.")
                        except:
                            st.error("Invalid image format or broken link. Try another.")
        else:
            st.warning("No high-quality images found for this model.")

if 'final_poster' in st.session_state:
    st.divider()
    st.image(st.session_state.final_poster)
    buf = io.BytesIO()
    st.session_state.final_poster.save(buf, format="PNG")
    st.download_button("Download Story Poster", buf.getvalue(), "poster.png", "image/png")
