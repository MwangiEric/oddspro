import streamlit as st
import pandas as pd
import requests
import io
import re
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# CONFIGURATION
# ============================================================================
URL = "https://www.priceinkenya.com/price-list/bluetooth-speakers"
SEARCH_API = "https://far-paule-emw-a67bd497.koyeb.app/search"
FALLBACK_FONT = "poppins.ttf" 

# ============================================================================
# UTILS
# ============================================================================
def is_high_quality(res_string, threshold=800):
    if not res_string: return False
    dims = [int(s) for s in re.findall(r'\d+', res_string)]
    return max(dims) >= threshold if dims else False

@st.cache_data(ttl=3600)
def get_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        # Using io.StringIO to satisfy Pandas 2.0+ requirements
        dfs = pd.read_html(io.StringIO(resp.text))
        df = dfs[0]
        df.columns = ['Full_Name', 'Price_Raw', 'Date']
        # The "Before Comma" Rule
        df['Clean_Name'] = df['Full_Name'].str.split(',').str[0].str.strip()
        # Price Cleaning
        df['Price_Int'] = df['Price_Raw'].replace(r'[^\d]', '', regex=True).fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return pd.DataFrame()

# ============================================================================
# DESIGN ENGINE
# ============================================================================
def generate_poster(name, price, img_obj):
    # Create 1080x1920 Story Canvas
    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    try:
        # Using Poppins per your instruction
        f_title = ImageFont.truetype(FALLBACK_FONT, 90)
        f_price = ImageFont.truetype(FALLBACK_FONT, 85)
        f_cta = ImageFont.truetype(FALLBACK_FONT, 55)
    except:
        f_title = f_price = f_cta = ImageFont.load_default()

    # Product Scaling (Fit into center)
    img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 450), img_obj)

    # Typography
    draw.text((540, 250), name.upper(), font=f_title, fill=(0,0,0), anchor="mm")
    draw.text((540, 380), f"Ksh {price:,}", font=f_price, fill=(0, 180, 0), anchor="mm")

    # Call to Action Button
    draw.rectangle([150, 1720, 930, 1860], fill=(0, 0, 0))
    draw.text((540, 1790), "ORDER NOW @ ORAIMO", font=f_cta, fill=(255, 255, 255), anchor="mm")
    
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Poster Gen", layout="wide")

# Initialize Session State
if 'selected_item' not in st.session_state: st.session_state.selected_item = None
if 'poster_img' not in st.session_state: st.session_state.poster_img = None

st.title("📱 Social Media Poster Generator")

df = get_data(URL)

if not df.empty:
    st.write("### 1. Select Product")
    search_q = st.text_input("🔍 Search model name...", "")
    
    # Filtered View
    filtered = df[df['Clean_Name'].str.contains(search_q, case=False)].copy()
    
    # Selection Widget (Stable for Cloud)
    options = ["-- Select Product --"] + filtered['Clean_Name'].tolist()
    choice = st.selectbox("Choose a product to design:", options)

    if choice != "-- Select Product --":
        # Save choice to session state
        st.session_state.selected_item = filtered[filtered['Clean_Name'] == choice].iloc[0]
        
        st.divider()
        st.write(f"### 2. Choose Image for **{choice}**")
        
        # Search API
        q = f'"{choice}" product transparent png'
        search_results = requests.get(SEARCH_API, params={"q": q, "categories": "images", "format": "json"}).json()
        
        # Smart Filtering (>= 800px)
        valid_imgs = [i for i in search_results.get('results', []) 
                      if is_high_quality(i.get('resolution', ''))][:9]
        
        if valid_imgs:
            cols = st.columns(3)
            for idx, img_data in enumerate(valid_imgs):
                with cols[idx % 3]:
                    st.image(img_data['img_src'], use_container_width=True)
                    if st.button("Use Image", key=f"btn_{idx}"):
                        # Fetch and Generate
                        raw = requests.get(img_data['img_src']).content
                        prod_img = Image.open(io.BytesIO(raw)).convert("RGBA")
                        
                        st.session_state.poster_img = generate_poster(
                            st.session_state.selected_item['Clean_Name'], 
                            st.session_state.selected_item['Price_Int'], 
                            prod_img
                        )
                        st.success("Poster Created! Scroll down.")
        else:
            st.warning("No high-quality images found. Try a different search term.")

# 3. EXPORT AREA
if st.session_state.poster_img:
    st.divider()
    st.write("### 3. Final Preview & Download")
    st.image(st.session_state.poster_img)
    
    # Buffer for download
    buf = io.BytesIO()
    st.session_state.poster_img.save(buf, format="PNG")
    st.download_button("Download for WhatsApp/Instagram", buf.getvalue(), "oraimo_poster.png", "image/png")
