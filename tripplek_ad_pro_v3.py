# ----------------------------------------------
#  pip install streamlit pillow moviepy rembg requests bs4 lxml
# ----------------------------------------------
import streamlit as st
import requests, io, tempfile, os, gc, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip
from rembg import remove
from bs4 import BeautifulSoup
import contextlib
from urllib.parse import urljoin

# --------------------------------------------------------
# BRAND & CONFIG
# --------------------------------------------------------
MAROON, GOLD = (153, 0, 0), (212, 175, 55)
LIGHT_BG, TEXT_DARK = (248, 248, 250), (20, 20, 30)
FPS, DURATION = 30, 5
TOTAL_FRAMES = FPS * DURATION
AUDIO_URL = "https://ik.imagekit.io/ericmwangi/advertising-music-308403.mp3?updatedAt=1764101548797"

PRESETS = {
    "Instagram Story": (1080, 1920),
    "Instagram Reel": (1080, 1920),
    "Instagram Post": (1080, 1080),
    "TikTok": (1080, 1920),
    "YouTube Short": (1080, 1920),
    "Facebook Post": (1080, 1080),
}

# --------------------------------------------------------
# SCRAPER
# --------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def scrape_product(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        name = soup.select_one("h1.product_title")
        name = name.get_text(strip=True) if name else ""
        
        price = soup.select_one("p.price .woocommerce-Price-amount bdi, span.woocommerce-Price-amount bdi")
        price = price.get_text(strip=True) if price else ""
        
        img = soup.select_one("a.woocommerce-product-gallery__image, div.woocommerce-product-gallery__image img")
        img_url = None
        if img:
            img_url = img.get("href") or img.get("src")
            if img_url:
                img_url = urljoin(url, img_url)
        
        specs = [li.get_text(strip=True) for li in soup.select(".woocommerce-product-details__short-description li, #tab-description li") if len(li.get_text(strip=True)) < 100][:5]
        
        return {"name": name, "price": price, "specs": specs, "image_url": img_url or ""}
    except Exception as e:
        st.warning(f"Scraping error: {e}")
        return {"name": "", "price": "", "specs": [], "image_url": ""}

# --------------------------------------------------------
# IMAGE LOAD
# --------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_image(url, max_size, remove_bg=False):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        if remove_bg:
            img = remove(img)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        st.warning(f"Image error: {e}")
        w, h = 400, 600
        fb = Image.new("RGBA", (w, h), (200, 200, 200, 100))
        draw = ImageDraw.Draw(fb)
        draw.text((w//2, h//2), "IMAGE", fill=MAROON, anchor="mm")
        return fb

# --------------------------------------------------------
# FONT
# --------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _font_bytes(bold=True):
    url = f"https://github.com/google/fonts/raw/main/ofl/inter/Inter-{'Bold' if bold else 'Medium'}.ttf"
    return requests.get(url, timeout=20).content

def get_font(size, bold=True):
    try:
        return ImageFont.truetype(io.BytesIO(_font_bytes(bold)), max(24, int(size)))
    except:
        return ImageFont.load_default()

def wrap_text(text, font, max_w):
    words = text.split()
    lines, current = [], []
    for word in words:
        test = ' '.join(current + [word])
        if font.getbbox(test)[2] <= max_w:
            current.append(word)
        else:
            if current:
                lines.append(' '.join(current))
            current = [word]
    if current:
        lines.append(' '.join(current))
    return lines

def draw_text_box(canvas, text, zone, size, color, bg, pad=20, align="center"):
    x1, y1, x2, y2 = [int(v) for v in zone]
    max_w, max_h = x2-x1-pad*2, y2-y1-pad*2
    if max_w <= 0 or max_h <= 0:
        return
    
    draw = ImageDraw.Draw(canvas)
    while size > 20:
        font = get_font(size, True)
        lines = wrap_text(text, font, max_w)
        total_h = sum(font.getbbox(l)[3] + 10 for l in lines)
        if total_h <= max_h:
            break
        size -= 2
    
    font = get_font(size, True)
    lines = wrap_text(text, font, max_w)
    
    draw.rounded_rectangle([x1, y1, x2, y2], 20, fill=bg)
    
    y = y1 + pad
    for line in lines:
        bbox = font.getbbox(line)
        tw = bbox[2] - bbox[0]
        x = x1 + (x2-x1-tw)//2 if align == "center" else x1 + pad
        draw.text((x, y), line, font=font, fill=color)
        y += bbox[3] - bbox[1] + 10

# --------------------------------------------------------
# EASING
# --------------------------------------------------------
def ease_out(t):
    return 1 - pow(1 - t, 3)

def ease_in_out(t):
    return 4*t*t*t if t < 0.5 else 1 - pow(-2*t + 2, 3)/2

# --------------------------------------------------------
# PARTICLES
# --------------------------------------------------------
@st.cache_resource(show_spinner=False)
def gen_particles(n=50):
    return [(random.uniform(0, 360), random.uniform(100, 250), random.randint(3, 8), 
             random.uniform(0.5, 1.5), random.randint(100, 200)) for _ in range(n)]

def draw_particles(draw, center, t, particles, color):
    cx, cy = center
    for angle, dist, size, speed, opacity in particles:
        a = angle + t * 30 * speed
        d = dist * (1 + 0.2 * math.sin(t * speed * 2))
        x = cx + int(d * math.cos(math.radians(a)))
        y = cy + int(d * math.sin(math.radians(a)))
        op = int(opacity * (1 + 0.3 * math.sin(t * speed * 3)))
        draw.ellipse([x-size, y-size, x+size, y+size], fill=(*color, op))

# --------------------------------------------------------
# TEMPLATE 1: MINIMAL
# --------------------------------------------------------
def template_minimal(t, data, adj, particles, w, h):
    base = Image.new("RGB", (w, h), LIGHT_BG)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Animated circles
    for i in range(8):
        x = int(w * (0.1 + 0.8 * i / 7))
        y = int(h * 0.5 + 200 * math.sin(t * 0.5 + i))
        size = 60 + int(30 * math.sin(t + i))
        draw.ellipse([x-size, y-size, x+size, y+size], fill=(*GOLD, 20))
    
    # Logo
    fade = min(1, t / 0.5)
    logo_x = int(w * 0.05 * adj['logo_x'])
    logo_y = int(h * 0.05 * adj['logo_y'])
    logo_w = int(w * 0.25 * adj['logo_scale'])
    logo = data['logo'].copy()
    logo.thumbnail((logo_w, int(logo_w * 0.3)), Image.Resampling.LANCZOS)
    if fade < 1:
        logo = Image.fromarray((np.array(logo) * fade).astype(np.uint8))
    canvas.paste(logo, (logo_x, logo_y), logo)
    
    # Title
    name_appear = min(1, max(0, (t - 0.3) * 2))
    if name_appear > 0:
        name_y = int(h * 0.05 * adj['title_y'] - 50 * (1 - ease_out(name_appear)))
        draw_text_box(canvas, data['name'].upper(), 
                     [w*0.05, name_y, w*0.95, name_y + int(h * 0.12)],
                     int(80 * adj['title_size']), MAROON, (*GOLD, int(200 * name_appear)))
    
    # Phone
    phone_appear = min(1, max(0, (t - 0.6) * 1.5))
    if phone_appear > 0:
        phone_x = int(w * 0.35 * adj['phone_x'])
        phone_y = int(h * 0.5 * adj['phone_y'] + 15 * math.sin(t * 1.5))
        phone_w = int(w * 0.4 * adj['phone_scale'])
        
        phone = data['phone'].copy()
        phone.thumbnail((phone_w, int(h * 0.5)), Image.Resampling.LANCZOS)
        
        scale = 0.5 + 0.5 * ease_out(phone_appear)
        if scale < 1:
            phone = phone.resize((int(phone.width * scale), int(phone.height * scale)), Image.Resampling.LANCZOS)
        
        # Particles
        p_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_particles(ImageDraw.Draw(p_layer), (phone_x, phone_y), t, particles, GOLD)
        p_layer = p_layer.filter(ImageFilter.GaussianBlur(3))
        canvas.paste(p_layer, (0, 0), p_layer)
        
        # Shadow
        shadow = phone.filter(ImageFilter.GaussianBlur(40))
        shadow = Image.fromarray((np.array(shadow) * 0.3).astype(np.uint8))
        canvas.paste(shadow, (phone_x - phone.width//2 + 20, phone_y - phone.height//2 + 40), shadow)
        canvas.paste(phone, (phone_x - phone.width//2, phone_y - phone.height//2), phone)
    
    # Features
    feat_x = int(w * 0.6 * adj['features_x'])
    feat_y = int(h * 0.35 * adj['features_y'])
    feat_w, feat_h = int(w * 0.35), int(h * 0.08)
    
    for i, spec in enumerate(data['specs'][:5]):
        spec_appear = min(1, max(0, (t - 1.0 - i * 0.1) * 3))
        if spec_appear > 0:
            offset = int(100 * (1 - ease_out(spec_appear)))
            y = feat_y + i * int(feat_h * 1.1)
            zone = [feat_x + offset, y, feat_x + offset + feat_w, y + feat_h]
            draw_text_box(canvas, spec, zone, int(32 * adj['features_size']), 
                         TEXT_DARK, (*LIGHT_BG, int(250 * spec_appear)), align="left")
            draw.rounded_rectangle([feat_x + offset, y, feat_x + offset + 5, y + feat_h], 
                                  3, fill=(*MAROON, int(255 * spec_appear)))
    
    # Price
    price_appear = min(1, max(0, (t - 1.8) * 2))
    if price_appear > 0:
        p_x, p_y = int(w * 0.05), int(h * 0.85 * adj['price_y'])
        p_w, p_h = int(w * 0.35 * adj['price_scale']), int(h * 0.1)
        scale = 0.7 + 0.3 * ease_out(price_appear)
        zone = [p_x + int(p_w * (1-scale)/2), p_y + int(p_h * (1-scale)/2),
                p_x + int(p_w * (1+scale)/2), p_y + int(p_h * (1+scale)/2)]
        draw_text_box(canvas, data['price'], zone, int(70 * adj['price_size']), 
                     (255, 255, 255), (*MAROON, int(240 * price_appear)))
    
    # CTA
    cta_appear = min(1, max(0, (t - 2.0) * 2))
    if cta_appear > 0:
        cta_x, cta_y = int(w * 0.45), int(h * 0.85 * adj['cta_y'])
        cta_w, cta_h = int(w * 0.5 * adj['cta_scale']), int(h * 0.1)
        pulse = 1 + 0.08 * math.sin(t * 4)
        zone = [cta_x, cta_y, cta_x + int(cta_w * pulse), cta_y + cta_h]
        draw_text_box(canvas, "SHOP NOW →", zone, int(60 * adj['cta_size']), 
                     (255, 255, 255), (*GOLD, int(240 * cta_appear)))
    
    # Website
    if t > 2.2:
        font = get_font(30, False)
        draw.text((w//2, int(h * 0.97)), "www.tripplek.co.ke", font=font, 
                 fill=(*TEXT_DARK, int(200 * min(1, (t - 2.2) * 2))), anchor="mm")
    
    return np.array(Image.alpha_composite(base.convert("RGBA"), canvas))

# --------------------------------------------------------
# TEMPLATE 2: BOLD
# --------------------------------------------------------
def template_bold(t, data, adj, particles, w, h):
    base = Image.new("RGB", (w, h), LIGHT_BG)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Diagonal stripes
    offset = int(t * 50) % 200
    for i in range(-5, 15):
        x = i * 200 + offset
        draw.polygon([(x, 0), (x + 100, 0), (x - 100, h), (x - 200, h)], fill=(*GOLD, 15))
    
    # Logo
    logo_appear = min(1, t / 0.4)
    logo_x = int(w * 0.05 * adj['logo_x'] - 100 * (1 - ease_out(logo_appear)))
    logo_y = int(h * 0.05 * adj['logo_y'])
    logo_w = int(w * 0.25 * adj['logo_scale'])
    logo = data['logo'].copy()
    logo.thumbnail((logo_w, int(logo_w * 0.3)), Image.Resampling.LANCZOS)
    canvas.paste(logo, (logo_x, logo_y), logo)
    
    # Title (skewed)
    name_appear = min(1, max(0, (t - 0.3) * 2))
    if name_appear > 0:
        n_x = int(w * 0.05 - 200 * (1 - ease_out(name_appear)))
        n_y = int(h * 0.15 * adj['title_y'] + 100 * (1 - ease_out(name_appear)))
        n_h = int(h * 0.15)
        draw.polygon([(n_x, n_y), (w*0.95, n_y - 20), (w*0.95, n_y + n_h), (n_x, n_y + n_h + 20)],
                    fill=(*MAROON, int(240 * name_appear)))
        draw_text_box(canvas, data['name'].upper(), [n_x, n_y, w*0.95, n_y + n_h],
                     int(90 * adj['title_size']), (255, 255, 255), (0, 0, 0, 0))
    
    # Phone (rotate in)
    phone_appear = min(1, max(0, (t - 0.7) * 1.5))
    if phone_appear > 0:
        p_x, p_y = int(w * 0.35 * adj['phone_x']), int(h * 0.55 * adj['phone_y'])
        p_w = int(w * 0.45 * adj['phone_scale'])
        
        phone = data['phone'].copy()
        phone.thumbnail((p_w, int(h * 0.55)), Image.Resampling.LANCZOS)
        
        angle = -90 * (1 - ease_out(phone_appear))
        if abs(angle) > 1:
            phone = phone.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        
        p_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_particles(ImageDraw.Draw(p_layer), (p_x, p_y), t, particles, MAROON)
        p_layer = p_layer.filter(ImageFilter.GaussianBlur(4))
        canvas.paste(p_layer, (0, 0), p_layer)
        canvas.paste(phone, (p_x - phone.width//2, p_y - phone.height//2), phone)
    
    # Features (pop in)
    f_x = int(w * 0.63 * adj['features_x'])
    f_y = int(h * 0.30 * adj['features_y'])
    f_w, f_h = int(w * 0.32), int(h * 0.09)
    
    for i, spec in enumerate(data['specs'][:5]):
        s_appear = min(1, max(0, (t - 1.2 - i * 0.08) * 4))
        if s_appear > 0:
            scale = 0.5 + 0.5 * ease_out(s_appear)
            y = f_y + i * int(f_h * 1.15)
            zone = [f_x + int(f_w * (1-scale)/2), y + int(f_h * (1-scale)/2),
                   f_x + int(f_w * (1+scale)/2), y + int(f_h * (1+scale)/2)]
            draw_text_box(canvas, spec, zone, int(36 * adj['features_size']),
                         TEXT_DARK, (*GOLD, int(250 * s_appear)), align="left")
    
    # Price
    pr_appear = min(1, max(0, (t - 2.0) * 2))
    if pr_appear > 0:
        draw_text_box(canvas, data['price'], 
                     [int(w * 0.05), int(h * 0.85 * adj['price_y']), 
                      int(w * 0.45 * adj['price_scale']), int(h * 0.96)],
                     int(80 * adj['price_size']), (255, 255, 255), (*MAROON, int(250 * pr_appear)))
    
    # CTA
    cta_appear = min(1, max(0, (t - 2.2) * 2))
    if cta_appear > 0:
        draw_text_box(canvas, "BUY NOW →",
                     [int(w * 0.48), int(h * 0.85 * adj['cta_y']),
                      int(w * 0.95 * adj['cta_scale']), int(h * 0.96)],
                     int(65 * adj['cta_size']), (255, 255, 255), (*GOLD, int(250 * cta_appear)))
    
    if t > 2.4:
        font = get_font(32, False)
        draw.text((w//2, int(h * 0.97)), "www.tripplek.co.ke", font=font,
                 fill=(*TEXT_DARK, int(200 * min(1, (t - 2.4) * 2))), anchor="mm")
    
    return np.array(Image.alpha_composite(base.convert("RGBA"), canvas))

# --------------------------------------------------------
# TEMPLATE 3: LUXURY
# --------------------------------------------------------
def template_luxury(t, data, adj, particles, w, h):
    base = Image.new("RGB", (w, h), (250, 248, 245))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Vignette
    cx, cy = w//2, h//2
    max_d = math.sqrt(cx**2 + cy**2)
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for y in range(0, h, 20):
        for x in range(0, w, 20):
            d = math.sqrt((x - cx)**2 + (y - cy)**2)
            v_draw.ellipse([x, y, x+20, y+20], fill=(10, 10, 15, int(40 * d / max_d)))
    vignette = vignette.filter(ImageFilter.GaussianBlur(30))
    base.paste(vignette, (0, 0), vignette)
    
    # Floating circles
    for i in range(6):
        a = t * 20 + i * 60
        d = 150 + 50 * math.sin(t + i)
        x = cx + int(d * math.cos(math.radians(a)))
        y = cy + int(d * math.sin(math.radians(a)))
        s = 40 + int(20 * math.sin(t * 2 + i))
        draw.ellipse([x-s, y-s, x+s, y+s], fill=(*GOLD, 25))
    
    # Logo (center top)
    logo_appear = min(1, t / 0.5)
    logo_w = int(w * 0.3 * adj['logo_scale'])
    logo = data['logo'].copy()
    logo.thumbnail((logo_w, int(logo_w * 0.3)), Image.Resampling.LANCZOS)
    if logo_appear < 1:
        logo = Image.fromarray((np.array(logo) * logo_appear).astype(np.uint8))
    canvas.paste(logo, ((w - logo.width) // 2, int(h * 0.05 * adj['logo_y'])), logo)
    
    # Title (slide up)
    name_appear = min(1, max(0, (t - 0.4) * 2))
    if name_appear > 0:
        n_y = int(h * 0.13 * adj['title_y'] + 80 * (1 - ease_out(name_appear)))
        draw.line([(w*0.15, n_y + int(h * 0.11)), (w*0.85, n_y + int(h * 0.11))],
                 fill=(*GOLD, int(255 * name_appear)), width=3)
        draw_text_box(canvas, data['name'].upper(), [w*0.1, n_y, w*0.9, n_y + int(h * 0.1)],
                     int(75 * adj['title_size']), MAROON, (0, 0, 0, 0))
    
    # Phone (center)
    phone_appear = min(1, max(0, (t - 0.8) * 1.5))
    if phone_appear > 0:
        p_x = int(w * 0.35 * adj['phone_x'])
        p_y = int(h * 0.55 * adj['phone_y'] + 20 * math.sin(t * 1.2))
        p_w = int(w * 0.4 * adj['phone_scale'])
        
        phone = data['phone'].copy()
        phone.thumbnail((p_w, int(h * 0.5)), Image.Resampling.LANCZOS)
        
        if phone_appear < 1:
            phone = Image.fromarray((np.array(phone) * phone_appear).astype(np.uint8))
        
        p_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_particles(ImageDraw.Draw(p_layer), (p_x, p_y), t, particles, GOLD)
        p_layer = p_layer.filter(ImageFilter.GaussianBlur(5))
        canvas.paste(p_layer, (0, 0), p_layer)
        
        canvas.paste(phone, (p_x - phone.width//2, p_y - phone.height//2), phone)
    
    # Features (elegant stack)
    f_x = int(w * 0.58 * adj['features_x'])
    f_y = int(h * 0.35 * adj['features_y'])
    f_w, f_h = int(w * 0.38), int(h * 0.075)
    
    for i, spec in enumerate(data['specs'][:5]):
        s_appear = min(1, max(0, (t - 1.3 - i * 0.12) * 3))
        if s_appear > 0:
            y = f_y + i * int(f_h * 1.2)
            offset = int(80 * (1 - ease_out(s_appear)))
            zone = [f_x + offset, y, f_x + offset + f_w, y + f_h]
            draw_text_box(canvas, spec, zone, int(30 * adj['features_size']),
                         TEXT_DARK, (255, 255, 255, int(230 * s_appear)), align="left")
            draw.rounded_rectangle([f_x + offset - 10, y, f_x + offset - 5, y + f_h],
                                  2, fill=(*GOLD, int(255 * s_appear)))
    
    # Price (gold frame)
    pr_appear = min(1, max(0, (t - 2.1) * 2))
    if pr_appear > 0:
        p_zone = [int(w * 0.05), int(h * 0.86 * adj['price_y']),
                 int(w * 0.42 * adj['price_scale']), int(h * 0.95)]
        draw.rounded_rectangle([p_zone[0]-5, p_zone[1]-5, p_zone[2]+5, p_zone[3]+5],
                              25, outline=(*GOLD, int(255 * pr_appear)), width=4)
        draw_text_box(canvas, data['price'], p_zone, int(75 * adj['price_size']),
                     MAROON, (255, 255, 255, int(240 * pr_appear)))
    
    # CTA (elegant button)
    cta_appear = min(1, max(0, (t - 2.3) * 2))
    if cta_appear > 0:
        c_zone = [int(w * 0.46), int(h * 0.86 * adj['cta_y']),
                 int(w * 0.95 * adj['cta_scale']), int(h * 0.95)]
        draw_text_box(canvas, "DISCOVER →", c_zone, int(58 * adj['cta_size']),
                     (255, 255, 255), (*MAROON, int(240 * cta_appear)))
    
    if t > 2.5:
        font = get_font(28, False)
        draw.text((w//2, int(h * 0.975)), "www.tripplek.co.ke", font=font,
                 fill=(*TEXT_DARK, int(180 * min(1, (t - 2.5) * 2))), anchor="mm")
    
    return np.array(Image.alpha_composite(base.convert("RGBA"), canvas))

# --------------------------------------------------------
# BUILD
# --------------------------------------------------------
def download_audio(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(r.content)
        tmp.close()
        return tmp.name
    except:
        return None

def build_video(template_func, data, adj, particles, preset):
    w, h = PRESETS[preset]
    frames = []
    bar = st.progress(0, "Rendering...")
    
    for i in range(TOTAL_FRAMES):
        frames.append(template_func(i/FPS, data, adj, particles, w, h))
        bar.progress((i+1)/TOTAL_FRAMES, f"Frame {i+1}/{TOTAL_