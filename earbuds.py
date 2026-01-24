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
# SURGICAL PARSING
# ============================================================================
def clean_spec(text):
    if not text: return ""
    return " ".join(text.replace('/', ' ').replace(',', ' ').strip().split())

def parse_cell(full_cell):
    parts = [p.strip() for p in full_cell.split(',')]
    name = parts[0] if len(parts) > 0 else "Product"
    # Collect all non-empty specs into a list
    specs = [clean_spec(p) for p in parts[1:4] if clean_spec(p)]
    return name, specs

# ============================================================================
# DESIGN ENGINE (Horizontal Badges Below Image)
# ============================================================================
def generate_poster(name, specs, price, img_obj):
    # Color Analysis
    img_sample = img_obj.copy().convert("RGBA")
    img_sample.thumbnail((100, 100))
    pixels = [p[:3] for p in img_sample.getdata() if p[3] > 100]
    theme_color = max(set(pixels), key=pixels.count) if pixels else (0,0,0)
    
    # Contrast Adjustment
    lum = (0.299 * theme_color[0] + 0.587 * theme_color[1] + 0.114 * theme_color[2])
    if lum > 210: theme_color = (int(theme_color[0]*0.7), int(theme_color[1]*0.7), int(theme_color[2]*0.7))

    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    try:
        f_brand = ImageFont.truetype(FALLBACK_FONT, 115) 
        f_model = ImageFont.truetype(FALLBACK_FONT, 75)  
        f_spec = ImageFont.truetype(FALLBACK_FONT, 38)
        f_price = ImageFont.truetype(FALLBACK_FONT, 95)
        f_contact = ImageFont.truetype(FALLBACK_FONT, 46)
    except:
        f_brand = f_model = f_spec = f_price = f_contact = ImageFont.load_default()

    # 1. HEADER: BRAND & MODEL
    name_parts = name.split(' ', 1)
    brand_t = name_parts[0].upper()
    model_t = name_parts[1].upper() if len(name_parts) > 1 else ""
    draw.text((540, 220), brand_t, font=f_brand, fill=theme_color, anchor="mm")
    draw.text((540, 335), model_t, font=f_model, fill=(60, 60, 60), anchor="mm")

    # 2. IMAGE PLACEMENT
    img_obj.thumbnail((900, 900), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 450), img_obj)

    # 3. SPEC BADGES (Horizontal Row below Image)
    if specs:
        y_pos = 1380
        total_width = 0
        spacing = 30
        badge_padding = 40
        
        # Pre-calculate widths
        badge_data = []
        for s in specs:
            bbox = draw.textbbox((0, 0), s.upper(), font=f_spec)
            w = (bbox[2] - bbox[0]) + (badge_padding * 2)
            h = (bbox[3] - bbox[1]) + 25
            badge_data.append({'text': s.upper(), 'w': w, 'h': h})
            total_width += w
        
        total_width += spacing * (len(specs) - 1)
        current_x = (1080 - total_width) // 2
        
        for data in badge_data:
            # Draw Badge Background (Soft version of theme color)
            draw.rounded_rectangle(
                [current_x, y_pos, current_x + data['w'], y_pos + data['h']],
                radius=15, fill=theme_color + (40,) # 40 = transparent tint
            )
            # Draw Spec Text
            draw.text(
                (current_x + data['w']//2, y_pos + data['h']//2),
                data['text'], font=f_spec, fill=(40, 40, 40), anchor="mm"
            )
            current_x += data['w'] + spacing

    # 4. PRICE BADGE (Bottom Right)
    p_text = f"KSH {int(price):,}"
    p_bbox = draw.textbbox((0,0), p_text, font=f_price)
    pw, ph = (p_bbox[2]-p_bbox[0]) + 80, (p_bbox[3]-p_bbox[1]) + 40
    draw.rounded_rectangle([1080-pw-60, 1550, 1020, 1550+ph], radius=25, fill=theme_color)
    draw.text((1080-60-(pw/2), 1550+(ph/2)), p_text, font=f_price, fill=(255,255,255), anchor="mm")

    # 5. FOOTER
    draw.text((540, 1820), "WhatsApp / Call +254 733 565861 to order", font=f_contact, fill=(40,40,40), anchor="mm")
    return canvas

# ============================================================================
# UI (Simplified)
# ============================================================================
st.set_page_config(page_title="Badge Poster Studio", layout="wide")
st.title("🏷️ Pro Badge Poster Studio")

cat_choice = st.sidebar.selectbox("Category", list(URL_MAP.keys()))

@st.cache_data(ttl=3600)
def load_data(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        df = pd.read_html(io.StringIO(r.text))[0]
        df.columns = ['Full_Cell', 'Price_Raw', 'Date']
        return df
    except: return pd.DataFrame()

df = load_data(URL_MAP[cat_choice])

if not df.empty:
    search_q = st.text_input("🔍 Search model...")
    filtered = df[df['Full_Cell'].str.contains(search_q, case=False)]
    choice = st.selectbox("Pick Product", ["-- Select --"] + filtered['Full_Cell'].tolist())

    if choice != "-- Select --":
        row = filtered[filtered['Full_Cell'] == choice].iloc[0]
        p_name, p_specs = parse_cell(choice)
        p_price = st.number_input("Edit Price", value=int(re.sub(r'[^\d]', '', str(row['Price_Raw'])) or 0))

        st.divider()
        q = f'"{p_name}" white background png'
        res = requests.get(SEARCH_API, params={"q": q, "format": "json", "categories": "images"}).json()
        items = [i for i in res.get('results', []) if any(int(d) >= 900 for d in re.findall(r'\d+', i.get('resolution','')))]
        
        if items:
            cols = st.columns(4)
            for idx, item in enumerate(items[:12]):
                with cols[idx % 4]:
                    st.image(item.get('thumbnail_src', item['img_src']), use_container_width=True)
                    if st.button("Select", key=f"btn_{idx}"):
                        raw = requests.get(item['img_src'], timeout=15).content
                        st.session_state.p = generate_poster(p_name, p_specs, p_price, Image.open(io.BytesIO(raw)).convert("RGBA"))
        else: st.warning("No 900px+ images found.")

if 'p' in st.session_state:
    st.divider()
    st.image(st.session_state.p)
    buf = io.BytesIO()
    st.session_state.p.save(buf, format="PNG")
    st.download_button("Download", buf.getvalue(), "poster.png")
