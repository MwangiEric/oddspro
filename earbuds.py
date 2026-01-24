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
FALLBACK_FONT = "poppins.ttf" 

# ============================================================================
# SMART RESOLUTION CHECKER
# ============================================================================
def is_high_quality(res_string, threshold=800):
    """
    Extracts digits from '799 x 1185' and checks if the largest 
    side meets the threshold.
    """
    if not res_string: return False
    # Find all numbers in the string
    dims = [int(s) for s in re.findall(r'\d+', res_string)]
    if not dims: return False
    # If the widest or tallest side is >= threshold, it's good
    return max(dims) >= threshold

# ============================================================================
# DATA ENGINE
# ============================================================================
@st.cache_data(ttl=3600)
def get_inventory_df(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=15)
        dfs = pd.read_html(io.StringIO(resp.text))
        df = dfs[0]
        df.columns = ['Full_Name', 'Price_Raw', 'Date']
        
        # Split logic: Take name before first comma
        df['Clean_Name'] = df['Full_Name'].str.split(',').str[0].str.strip()
        df['Price_Int'] = df['Price_Raw'].replace(r'[^\d]', '', regex=True).astype(int)
        return df
    except Exception as e:
        st.error(f"Scraper error: {e}")
        return pd.DataFrame()

# ============================================================================
# DESIGN ENGINE
# ============================================================================
def generate_poster(name, price, img_obj):
    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    try:
        f_title = ImageFont.truetype(FALLBACK_FONT, 90)
        f_price = ImageFont.truetype(FALLBACK_FONT, 80)
        f_cta = ImageFont.truetype(FALLBACK_FONT, 50)
    except:
        f_title = f_price = f_cta = ImageFont.load_default()

    # Product Visual (Scaling to fit 900x900)
    img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 450), img_obj)

    # Content
    draw.text((540, 250), name.upper(), font=f_title, fill=(0,0,0), anchor="mm")
    draw.text((540, 370), f"Ksh {price:,}", font=f_price, fill=(0, 160, 0), anchor="mm")

    # CTA
    draw.rectangle([150, 1720, 930, 1850], fill=(0, 0, 0))
    draw.text((540, 1785), "ORDER NOW @ ORAIMO", font=f_cta, fill=(255, 255, 255), anchor="mm")
    
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Studio", layout="wide")
st.title("🛒 Product Poster Studio")

df = get_inventory_df(URL)

if not df.empty:
    st.write("### 1. Find Product")
    search_q = st.text_input("🔍 Search brand or model...", placeholder="e.g. Redmi Buds")
    
    filtered_df = df[df['Clean_Name'].str.contains(search_q, case=False)]
    
    # Modern Selection Table
    event = st.dataframe(
        filtered_df[['Clean_Name', 'Price_Raw']],
        on_select="rerun",
        selection_mode="single_row",
        hide_index=True,
        use_container_width=True
    )

    if len(event.selection.rows) > 0:
        row_idx = event.selection.rows[0]
        item = filtered_df.iloc[row_idx]
        
        st.divider()
        st.write(f"### 2. Choose Image for **{item['Clean_Name']}**")
        
        # Search for PNGs
        q = f'"{item["Clean_Name"]}" product transparent background png'
        search_results = requests.get(SEARCH_API, params={"q": q, "categories": "images", "format": "json"}).json()
        
        # Apply the SMART Resolution Checker (Threshold: 800px)
        valid_images = [img for img in search_results.get('results', []) 
                        if is_high_quality(img.get('resolution', ''))][:9]
        
        if valid_images:
            cols = st.columns(3)
            for idx, img_data in enumerate(valid_images):
                with cols[idx % 3]:
                    st.image(img_data['img_src'], use_container_width=True)
                    if st.button("Select This", key=f"img_{idx}"):
                        raw = requests.get(img_data['img_src']).content
                        pil_img = Image.open(io.BytesIO(raw)).convert("RGBA")
                        st.session_state.poster = generate_poster(item['Clean_Name'], item['Price_Int'], pil_img)
                        st.success("Poster ready!")
        else:
            st.warning("No high-quality images found for this specific search.")

# 3. EXPORT
if 'poster' in st.session_state:
    st.divider()
    st.write("### 3. Final Preview")
    st.image(st.session_state.poster)
    
    buf = io.BytesIO()
    st.session_state.poster.save(buf, format="PNG")
    st.download_button("Download Story Image", buf.getvalue(), "oraimo_poster.png", "image/png")
