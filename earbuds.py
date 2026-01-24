import streamlit as st
import pandas as pd
import requests
import io
import re
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# SETTINGS
# ============================================================================
URL = "https://www.priceinkenya.com/price-list/bluetooth-speakers"
SEARCH_API = "https://far-paule-emw-a67bd497.koyeb.app/search"
FALLBACK_FONT = "poppins.ttf" # Ensure this file is in your project folder

# ============================================================================
# DATA ENGINE (Pandas + Cleaning)
# ============================================================================
@st.cache_data(ttl=3600) # Caches the data for 1 hour to stay fast
def get_clean_inventory(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers)
    
    # Read the first table on the page directly into a DF
    dfs = pd.read_html(io.StringIO(resp.text))
    df = dfs[0]
    
    # Standardize columns based on your HTML structure
    df.columns = ['Full_Name', 'Price_Raw', 'Available_From']
    
    # 1. CLEANING: Take only the name before the comma
    df['Product_Name'] = df['Full_Name'].str.split(',').str[0].str.strip()
    
    # 2. CLEANING: Convert Price to numeric for math/sorting
    df['Price_Int'] = df['Price_Raw'].replace(r'[^\d]', '', regex=True).astype(int)
    
    return df

# ============================================================================
# DESIGN ENGINE
# ============================================================================
def create_story_poster(product_name, price, pil_img):
    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    try:
        f_title = ImageFont.truetype(FALLBACK_FONT, 90)
        f_price = ImageFont.truetype(FALLBACK_FONT, 80)
        f_cta = ImageFont.truetype(FALLBACK_FONT, 50)
    except:
        f_title = f_price = f_cta = ImageFont.load_default()

    # Center Image (900x900 scale)
    pil_img.thumbnail((900, 900), Image.Resampling.LANCZOS)
    canvas.paste(pil_img, ((1080 - pil_img.width)//2, 450), pil_img)

    # Text Elements
    draw.text((540, 250), product_name.upper(), font=f_title, fill=(0,0,0), anchor="mm")
    draw.text((540, 380), f"Ksh {price:,}", font=f_price, fill=(0, 160, 0), anchor="mm")
    
    # Bottom CTA
    draw.rectangle([150, 1720, 930, 1850], fill=(0,0,0))
    draw.text((540, 1785), "ORDER NOW @ ORAIMO", font=f_cta, fill=(255,255,255), anchor="mm")
    
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Poster Lab", layout="centered")

st.title("🛒 Product Poster Studio")
st.caption("Data synced live from PriceInKenya")

# 1. FETCH & SEARCH
inventory = get_clean_inventory(URL)

# Search Bar + Table View
search_q = st.text_input("🔍 Search products (e.g. JBL, Sony, Anker)...")
filtered_df = inventory[inventory['Product_Name'].str.contains(search_q, case=False)]

# Selection Table
st.write("### 1. Select a Product")
selected_row = st.dataframe(
    filtered_df[['Product_Name', 'Price_Raw']], 
    on_select="rerun", 
    selection_mode="single_row",
    hide_index=True,
    use_container_width=True
)

# 2. IMAGE PICKER
if len(selected_row.selection.rows) > 0:
    idx = selected_row.selection.rows[0]
    target = filtered_df.iloc[idx]
    
    st.divider()
    st.write(f"### 2. Pick a Photo for **{target['Product_Name']}**")
    
    # Fetch images
    q = f'"{target["Product_Name"]}" transparent png'
    r = requests.get(SEARCH_API, params={"q": q, "categories": "images", "format": "json"}).json()
    images = [img for img in r.get('results', []) if "900" in img.get('resolution', '')][:6]
    
    if not images:
        st.warning("No high-res images found. Try searching for a simpler name.")
    
    cols = st.columns(3)
    for i, img_meta in enumerate(images):
        with cols[i % 3]:
            st.image(img_meta['img_src'], use_container_width=True)
            if st.button("Use This", key=f"img_{i}"):
                # 3. GENERATE POSTER
                raw_bytes = requests.get(img_meta['img_src']).content
                prod_img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
                
                poster = create_story_poster(target['Product_Name'], target['Price_Int'], prod_img)
                st.session_state.final_poster = poster
                st.success("Poster generated in the Preview tab!")

# 4. EXPORT TAB
if 'final_poster' in st.session_state:
    with st.expander("✨ View Final Poster", expanded=True):
        st.image(st.session_state.final_poster)
        buf = io.BytesIO()
        st.session_state.final_poster.save(buf, format="PNG")
        st.download_button("Download PNG", buf.getvalue(), f"{target['Product_Name']}.png")
