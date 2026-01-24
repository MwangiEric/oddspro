import streamlit as st
import pandas as pd
import requests
import io
import re
import random
from PIL import Image, ImageDraw, ImageFont
from groq import Groq

# ============================================================================
# CREATIVE THEMES (Pillow Vector Simulation)
# ============================================================================
def draw_tech_style(draw, color):
    # Futuristic Grid & Hexagons
    for i in range(0, 1080, 100):
        draw.line([(i, 0), (i, 1920)], fill=color + (20,), width=1)
    for _ in range(4):
        x, y = random.randint(100, 900), random.randint(200, 1500)
        draw.regular_polygon((x, y, random.randint(100, 250)), n_sides=6, outline=color + (80,), width=3)

def draw_luxury_style(draw, color):
    # Elegant Soft Glows & Minimalist Arcs
    for _ in range(2):
        size = random.randint(800, 1400)
        draw.ellipse([random.randint(-400, 0), 400, size, 1600], fill=color + (15,))
    draw.arc([50, 50, 1030, 1870], start=0, end=360, fill=color + (30,), width=2)

def draw_energy_style(draw, color):
    # Dynamic Speed Lines & Kinetic Triangles
    for i in range(-500, 1500, 120):
        draw.line([(0, i), (1080, i+400)], fill=color + (30,), width=4)
    for _ in range(6):
        pts = [(random.randint(0, 1080), random.randint(0, 1920)) for _ in range(3)]
        draw.polygon(pts, fill=color + (20,), outline=color + (50,))

# ============================================================================
# GROQ CREATIVE BRAIN
# ============================================================================
def get_groq_suggestion(product_name, category):
    if not st.secrets.get("groq_key"): return "TECH", "PREMIUM PERFORMANCE"
    client = Groq(api_key=st.secrets["groq_key"])
    
    prompt = f"""
    Analyze {product_name} ({category}). 
    1. Pick best style: TECH (innovation), LUXURY (premium/sleek), or ENERGY (speed/sound).
    2. Write a 3-word tagline focusing on its #1 feature.
    Format exactly: STYLE | TAGLINE
    """
    try:
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}]).choices[0].message.content
        s, t = res.split('|')
        return s.strip().upper(), t.strip().upper()
    except: return "TECH", "ELITE QUALITY"

# ============================================================================
# CORE DESIGN ENGINE
# ============================================================================
def generate_poster(name, specs, price, img_obj, style, tagline):
    # Random Sample Color from Image
    img_s = img_obj.convert("RGBA")
    img_s.thumbnail((100, 100))
    pixels = [p[:3] for p in img_s.getdata() if p[3] > 150]
    theme_color = random.choice(pixels) if pixels else (40, 40, 40)

    canvas = Image.new('RGBA', (1080, 1920), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Apply Aesthetic Style
    if "TECH" in style: draw_tech_style(draw, theme_color)
    elif "LUXURY" in style: draw_luxury_style(draw, theme_color)
    else: draw_energy_style(draw, theme_color)

    try:
        f_tag = ImageFont.truetype("poppins.ttf", 48)
        f_brand = ImageFont.truetype("poppins.ttf", 115)
        f_spec = ImageFont.truetype("poppins.ttf", 40)
        f_price = ImageFont.truetype("poppins.ttf", 105)
    except:
        f_tag = f_brand = f_spec = f_price = ImageFont.load_default()

    # 2. Text Content
    draw.text((540, 180), tagline, font=f_tag, fill=theme_color, anchor="mm")
    draw.text((540, 310), name.upper(), font=f_brand, fill=(30, 30, 30), anchor="mm")

    # 3. High-Res Image
    img_obj.thumbnail((880, 880), Image.Resampling.LANCZOS)
    canvas.paste(img_obj, ((1080 - img_obj.width)//2, 500), img_obj)

    # 4. Badge Row (Below Image)
    if specs:
        y_badge = 1400
        clean_specs = [s.replace('/', ' ').replace(',', '').strip() for s in specs if s]
        total_w = sum([draw.textbbox((0,0), s.upper(), font=f_spec)[2] for s in clean_specs]) + (len(clean_specs)*60)
        curr_x = (1080 - total_w) // 2
        for s in clean_specs:
            txt = s.upper()
            tw = draw.textbbox((0,0), txt, font=f_spec)[2] + 40
            draw.rounded_rectangle([curr_x, y_badge, curr_x+tw, y_badge+65], radius=12, fill=theme_color+(35,))
            draw.text((curr_x + tw//2, y_badge+32), txt, font=f_spec, fill=(50,50,50), anchor="mm")
            curr_x += tw + 25

    # 5. Price & Footer
    draw.text((540, 1620), f"KSH {int(price):,}", font=f_price, fill=theme_color, anchor="mm")
    draw.text((540, 1820), "ORDER: +254 733 565861", font=f_tag, fill=(60,60,60), anchor="mm")
    
    return canvas

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Oraimo Pro Studio", layout="wide")
st.title("🎬 AI Director Poster Studio")

# Global State for Groq
if 'groq_style' not in st.session_state: st.session_state.groq_style = "TECH"
if 'tagline' not in st.session_state: st.session_state.tagline = "PREMIUM CHOICE"

cat_choice = st.sidebar.selectbox("Category", list(URL_MAP.keys()))
df = fetch_data(URL_MAP[cat_choice]) # Assuming fetch_data is defined as before

if not df.empty:
    search = st.text_input("Find Product...")
    filtered = df[df['Full_Cell'].str.contains(search, case=False)]
    choice = st.selectbox("Pick Item", ["-- Select --"] + filtered['Full_Cell'].tolist())

    if choice != "-- Select --":
        # 1. Parse & Groq Analysis
        p_name = choice.split(',')[0].strip()
        p_specs = choice.split(',')[1:4]
        p_price = st.number_input("Edit Price", value=int(re.sub(r'[^\d]', '', str(filtered[filtered['Full_Cell']==choice]['Price_Raw'].values[0])) or 0))

        col1, col2 = st.columns([2, 1])
        with col2:
            st.write("### AI Suggestions")
            if st.button("Ask Groq for Theme"):
                st.session_state.groq_style, st.session_state.tagline = get_groq_suggestion(p_name, cat_choice)
            
            st.session_state.groq_style = st.radio("Override Theme Style:", ["TECH", "LUXURY", "ENERGY"], 
                                                   index=["TECH", "LUXURY", "ENERGY"].index(st.session_state.groq_style))
            st.session_state.tagline = st.text_input("Edit Tagline", value=st.session_state.tagline)

        # 2. Image Selection (900px+ Thumbnails)
        with col1:
            st.write("### Choose High-Res Image")
            res = requests.get(SEARCH_API, params={"q": f"{p_name} white background png", "format": "json"}).json()
            items = [i for i in res.get('results', []) if any(int(d) >= 900 for d in re.findall(r'\d+', i.get('resolution','')))]
            
            if items:
                img_cols = st.columns(3)
                for idx, item in enumerate(items[:6]):
                    with img_cols[idx % 3]:
                        st.image(item['thumbnail_src'], use_container_width=True)
                        if st.button("Generate Poster", key=f"gen_{idx}"):
                            raw = requests.get(item['img_src'], timeout=15).content
                            st.session_state.final = generate_poster(p_name, p_specs, p_price, Image.open(io.BytesIO(raw)).convert("RGBA"), st.session_state.groq_style, st.session_state.tagline)

if 'final' in st.session_state:
    st.divider()
    st.image(st.session_state.final)
    buf = io.BytesIO()
    st.session_state.final.save(buf, format="PNG")
    st.download_button("Download Story Poster", buf.getvalue(), "poster.png")
