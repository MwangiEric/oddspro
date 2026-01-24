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
# SMART COLOR & IMAGE UTILS
# ============================================================================
def get_adaptive_color(pil_img):
    """Extracts dominant color and ensures it is dark enough for white text."""
    img = pil_img.copy().convert("RGBA")
    img.thumbnail((100, 100))
    pixels = [p[:3] for p in img.getdata() if p[3] > 128]
    if not pixels: return (0, 0, 0)
    
    dom_color = max(set(pixels), key=pixels.count)
    # Calculate Luminance (standard formula)
    lum = (0.299 * dom_color[0] + 0.587 * dom_color[1] + 0.114 * dom_color[2])
    
    # Darken if too light, Lighten if too dark
    if lum > 200: return (int(dom_color[0]*0.6), int(dom_color[1]*0.6), int(dom_color[2]*0.6))
    if lum < 30: return (80, 80, 80)
    return dom_color

def check_image_content(pil_img):
    """Detects if the image is mostly empty/transparent in the center."""
    img = pil_img.convert("RGBA")
    w, h = img.size
    center = img.crop((w//4, h//4, 3*w//4, 3*h//4))
    alpha = center.getchannel('A')
    non_empty = sum(1 for p in alpha.getdata() if p > 15)
    return (non_empty / (alpha.size[0] * alpha.size[1])) * 100

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
        # Apply Comma Rule: Split and take the first phrase
        df['Clean_Name'] = df['Full_Name'].str.split(',').str[0].str.strip()
        df['Price_Int'] = df['Price_Raw'].replace(r'[^\d]', '', regex=True).fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return pd.DataFrame()

# ============================================================================
# ADAPTIVE DESIGN ENGINE
# ============================================================================
def generate_poster(name, price, img_obj):
    theme_color = get_adaptive_color(img_obj)
    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # 1. Subtle Gradient Background
    for i in range(800):
        alpha = int(20 * (1 - i/800))
        draw.line([(0, i), (1080, i)], fill=theme_color + (alpha,))

    try:
        f_brand = ImageFont.truetype(FALLBACK_FONT, 115) 
        f_model = ImageFont.truetype(FALLBACK_FONT, 75)  
        f_price = ImageFont.truetype(FALLBACK_FONT, 90)
        f_contact = ImageFont.truetype(FALLBACK_FONT, 46)
    except:
        f_brand = f_model = f_price = f_contact = ImageFont.load_default()

    # 2. Text Splitting (First word as Brand)
    parts = name.split(' ', 1)
    brand_t = parts[0].upper()
    model_t = parts[1].upper() if len(parts) > 1 else ""
    
    draw.text((540, 240), brand_t, font=f_brand, fill=theme_color, anchor="mm")
    draw.text((540, 350), model_t, font=f_model, fill=(60, 60, 60), anchor="mm")

    # 3. Product Placement
    img_obj.thumbnail((920, 920), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 500), img_obj)

    # 4. Adaptive Price Badge
    p_text = f"KSH {price:,}"
    bbox = draw.textbbox((0,0), p_text, font=f_price)
    pad = 40
    bw, bh = (bbox[2]-bbox[0]) + pad*2, (bbox[3]-bbox[1]) + pad*2
    # Shadow + Badge
    draw.rounded_rectangle([1080-bw-55, 1425, 1025, 1425+bh], radius=25, fill=(0,0,0,30))
    draw.rounded_rectangle([1080-bw-60, 1420, 1020, 1420+bh], radius=25, fill=theme_color)
    draw.text((1080-60-(bw/2), 1420+(bh/2)), p_text, font=f_price, fill=(255,255,255), anchor="mm")

    # 5. WhatsApp Footer
    draw.text((540, 1780), "WhatsApp / Call +254 733 565861 to order", 
              font=f_contact, fill=(30, 30, 30), anchor="mm")
    
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Poster Gen", layout="wide")

if 'final_poster' not in st.session_state: st.session_state.final_poster = None

st.title("📱 Social Media Poster Studio")

df = get_live_data(URL)

if not df.empty:
    st.write("### 1. Select Product")
    search_q = st.text_input("🔍 Search model name (e.g., JBL, Anker)...")
    filtered = df[df['Clean_Name'].str.contains(search_q, case=False)]
    
    choice = st.selectbox("Pick product:", ["-- Select --"] + filtered['Clean_Name'].tolist())

    if choice != "-- Select --":
        selected_row = filtered[filtered['Clean_Name'] == choice].iloc[0]
        
        st.divider()
        st.write(f"### 2. Select Image for **{choice}**")
        
        # Build Search
        q = f'"{choice}" product transparent png'
        search_res = requests.get(SEARCH_API, params={"q": q, "format": "json"}).json()
        valid_list = [i for i in search_res.get('results', []) if is_high_quality(i.get('resolution', ''))][:9]
        
        if valid_list:
            cols = st.columns(3)
            for idx, img_data in enumerate(valid_list):
                with cols[idx % 3]:
                    st.image(img_data['img_src'], use_container_width=True)
                    if st.button("Use This", key=f"btn_{idx}"):
                        try:
                            r_bytes = requests.get(img_data['img_src'], timeout=10).content
                            p_img = Image.open(io.BytesIO(r_bytes)).convert("RGBA")
                            
                            # Content Check
                            score = check_image_content(p_img)
                            if score < 5:
                                st.warning(f"Image looks poor/empty ({score:.1f}%). Try another.")
                            else:
                                st.session_state.final_poster = generate_poster(
                                    selected_row['Clean_Name'], 
                                    selected_row['Price_Int'], 
                                    p_img
                                )
                                st.success(f"Poster Generated! Color Syncing Done.")
                        except:
                            st.error("Could not load this image file. Try another.")
        else:
            st.warning("No high-quality transparent images found.")

if st.session_state.final_poster:
    st.divider()
    st.image(st.session_state.final_poster)
    buf = io.BytesIO()
    st.session_state.final_poster.save(buf, format="PNG")
    st.download_button("Download Story Poster", buf.getvalue(), "poster.png", "image/png")
