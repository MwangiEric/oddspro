import streamlit as st
import pandas as pd
import requests
import io
import re
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION
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
# ADAPTIVE COLOR LOGIC
# ============================================================================
def get_adaptive_color(pil_img):
    img = pil_img.copy().convert("RGBA")
    img.thumbnail((100, 100))
    pixels = [p[:3] for p in img.getdata() if p[3] > 100] # Ignore transparency
    if not pixels: return (0, 0, 0)
    dom_color = max(set(pixels), key=pixels.count)
    lum = (0.299 * dom_color[0] + 0.587 * dom_color[1] + 0.114 * dom_color[2])
    if lum > 200: return (int(dom_color[0]*0.6), int(dom_color[1]*0.6), int(dom_color[2]*0.6))
    return dom_color

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
        def clean_name(val):
            val_str = str(val)
            return val_str.split(',')[0].strip() if ',' in val_str else val_str.strip()
        df['Clean_Name'] = df['Full_Name'].apply(clean_name)
        df['Price_Int'] = df['Price_Raw'].replace(r'[^\d]', '', regex=True).fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

# ============================================================================
# DESIGN ENGINE
# ============================================================================
def generate_poster(name, price, img_obj):
    theme_color = get_adaptive_color(img_obj)
    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    for i in range(700): # Light top gradient
        alpha = int(15 * (1 - i/700))
        draw.line([(0, i), (1080, i)], fill=theme_color + (alpha,))

    try:
        f_brand = ImageFont.truetype(FALLBACK_FONT, 115) 
        f_model = ImageFont.truetype(FALLBACK_FONT, 75)  
        f_price = ImageFont.truetype(FALLBACK_FONT, 95)
        f_contact = ImageFont.truetype(FALLBACK_FONT, 46)
    except:
        f_brand = f_model = f_price = f_contact = ImageFont.load_default()

    parts = name.split(' ', 1)
    brand_t, model_t = parts[0].upper(), (parts[1].upper() if len(parts)>1 else "")
    draw.text((540, 240), brand_t, font=f_brand, fill=theme_color, anchor="mm")
    draw.text((540, 360), model_t, font=f_model, fill=(60, 60, 60), anchor="mm")
    
    img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 520), img_obj)

    p_text = f"KSH {int(price):,}"
    bbox = draw.textbbox((0,0), p_text, font=f_price)
    pad = 40
    bw, bh = (bbox[2]-bbox[0]) + pad*2, (bbox[3]-bbox[1]) + pad*2
    draw.rounded_rectangle([1080-bw-60, 1420, 1020, 1420+bh], radius=25, fill=theme_color)
    draw.text((1080-60-(bw/2), 1420+(bh/2)), p_text, font=f_price, fill=(255,255,255), anchor="mm")
    draw.text((540, 1780), "WhatsApp / Call +254 733 565861 to order", font=f_contact, fill=(30, 30, 30), anchor="mm")
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Poster Studio", layout="wide")
st.title("📱 Multi-Source Poster Studio")

# 1. MODE SELECTION
mode = st.radio("Choose Mode:", ["Search List", "Manual Entry"], horizontal=True)

target_name = ""
target_price = 0

if mode == "Search List":
    cat_choice = st.selectbox("1. Filter by Category", list(URL_MAP.keys()))
    df = get_live_data(URL_MAP[cat_choice])
    
    if not df.empty:
        search_q = st.text_input(f"🔍 Search for product in {cat_choice}...")
        filtered = df[df['Clean_Name'].str.contains(search_q, case=False)]
        choice = st.selectbox("2. Pick Product", ["-- Select --"] + filtered['Clean_Name'].tolist())
        
        if choice != "-- Select --":
            row = filtered[filtered['Clean_Name'] == choice].iloc[0]
            target_name = row['Clean_Name']
            target_price = st.number_input("3. Edit Price (Optional)", value=int(row['Price_Int']))
else:
    col1, col2 = st.columns(2)
    with col1: target_name = st.text_input("Product Name", placeholder="e.g. Sony PS5 Slim")
    with col2: target_price = st.number_input("Product Price", value=0)

# 2. IMAGE SEARCH & POSTER GENERATION
if target_name:
    st.divider()
    st.write(f"### 🖼️ Select Image for **{target_name}**")
    
    # RELAXED SEARCH: Removed strict 'transparent png' to find more images
    q = f"{target_name} white background"
    res = requests.get(SEARCH_API, params={"q": q, "format": "json", "categories": "images"}).json()
    items = res.get('results', [])[:12] # Top 12 results
    
    if items:
        cols = st.columns(4)
        for idx, item in enumerate(items):
            with cols[idx % 4]:
                st.image(item['img_src'], use_container_width=True)
                if st.button("Use This", key=f"img_{idx}"):
                    try:
                        r = requests.get(item['img_src'], timeout=10).content
                        p_img = Image.open(io.BytesIO(r)).convert("RGBA")
                        st.session_state.poster = generate_poster(target_name, target_price, p_img)
                        st.success("Poster Created!")
                    except: st.error("Link broken.")
    else: st.warning("No images found. Try a different name.")

if 'poster' in st.session_state:
    st.divider()
    st.image(st.session_state.poster)
    buf = io.BytesIO()
    st.session_state.poster.save(buf, format="PNG")
    st.download_button("Download Image", buf.getvalue(), "poster.png", "image/png")
