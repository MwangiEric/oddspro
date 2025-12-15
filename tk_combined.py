"""
ULTIMATE AD STUDIO v2.0 - SIMPLIFIED
=====================================
Professional templates • No over-engineering • Just works
"""

import streamlit as st
import requests, io, tempfile, os, math, random, gc
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip
from rembg import remove

# ============================================================================
# 1. CORE CONFIG - SIMPLE
# ============================================================================

# Video formats (ADDED WhatsApp)
FORMATS = {
    "TikTok/Reels": (1080, 1920),
    "Instagram Post": (1080, 1080),
    "Instagram Story": (1080, 1920),
    "YouTube Short": (1080, 1920),
    "Facebook Post": (1080, 1080),
    "WhatsApp Status": (1080, 1920),
}

FPS = 30
DURATION = 6

# Brand color system
COLOR_PRESETS = {
    "TrippleK Signature": {
        "maroon": (153, 0, 0),
        "gold": (212, 175, 55),
        "bg_light": (248, 248, 250),
        "text_dark": (20, 20, 30),
        "white": (255, 255, 255)
    },
    "Modern Tech": {
        "maroon": (30, 144, 255),  # Blue
        "gold": (255, 140, 0),     # Orange
        "bg_light": (15, 20, 30),
        "text_dark": (240, 240, 245),
        "white": (255, 255, 255)
    },
    "Eco Green": {
        "maroon": (46, 139, 87),   # Green
        "gold": (218, 165, 32),    # Goldenrod
        "bg_light": (245, 255, 250),
        "text_dark": (20, 30, 20),
        "white": (255, 255, 255)
    }
}

# Templates
TEMPLATES = {
    "Minimal Elegance": "Clean lines, subtle animations",
    "Bold & Dynamic": "Energetic, moving shapes", 
    "Luxury Premium": "Sophisticated effects, gold accents",
    "Abstract Geometric": "Modern shapes, mesh gradients",
    "Glassmorphism": "Frosted glass effects",
    "Particle Flow": "Floating particles, dynamic connections"
}

# ============================================================================
# 2. UTILITIES - SIMPLE
# ============================================================================

@st.cache_resource
def load_font(bold=True):
    """Load Poppins font with correct URLs"""
    try:
        # CORRECT Google Fonts URLs for Poppins
        if bold:
            url = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
            font_path = "poppins_bold.ttf"
        else:
            url = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf"
            font_path = "poppins_regular.ttf"
        
        if not os.path.exists(font_path):
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()  # Check if download succeeded
            with open(font_path, 'wb') as f:
                f.write(resp.content)
            print(f"✅ Font downloaded: {font_path}")
        
        return font_path
    except Exception as e:
        print(f"❌ Font loading error: {e}")
        return None

def get_font(size, bold=True):
    """Get font with fallback"""
    try:
        font_path = load_font(bold)
        if font_path:
            return ImageFont.truetype(font_path, int(size))
    except:
        pass
    return ImageFont.load_default()

def ease_out(t):
    """Cubic ease out"""
    return 1 - (1 - t) ** 3

# ============================================================================
# 3. BACKGROUNDS - SIMPLE
# ============================================================================

def create_background(template_name, width, height, colors, t=0.0):
    """Create animated backgrounds"""
    canvas = Image.new("RGBA", (width, height), colors["bg_light"])
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    maroon, gold = colors["maroon"], colors["gold"]
    
    if template_name == "Minimal Elegance":
        # Horizontal lines
        for i in range(6):
            y = height * (i + 1) / 7
            wave = math.sin(t * 0.5 + i) * 20
            alpha = 20
            draw.line([(0, y + wave), (width, y + wave)], 
                     fill=(*maroon, alpha), width=2)
    
    elif template_name == "Bold & Dynamic":
        # Diagonal stripes
        stripe_width = 120
        offset = (t * 40) % (stripe_width * 2)
        
        for i in range(-5, 15):
            x_start = -height + (i * stripe_width) + offset
            color = maroon if i % 3 == 0 else gold
            alpha = 12 if i % 3 == 0 else 8
            
            points = [
                (x_start, 0),
                (x_start + stripe_width, 0),
                (x_start + stripe_width + height, height),
                (x_start + height, height)
            ]
            draw.polygon(points, fill=(*color, alpha))
    
    elif template_name == "Luxury Premium":
        # Radial burst
        cx, cy = width // 2, height // 2
        max_radius = min(width, height) * 0.4
        
        for i in range(100, 0, -1):
            radius = (i / 100) * max_radius
            alpha = int(25 * (i / 100))
            draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                        fill=(*maroon, alpha))
    
    elif template_name == "Abstract Geometric":
        # Rotating shapes
        for i in range(5):
            angle = (t * 10 + i * 72) % 360
            size = 200 + i * 40
            cx, cy = width // 2, height // 2
            rad = math.radians(angle)
            
            corners = [(-size, -size), (size, -size), (size, size), (-size, size)]
            rotated = [
                (cx + x * math.cos(rad) - y * math.sin(rad), 
                 cy + x * math.sin(rad) + y * math.cos(rad))
                for x, y in corners
            ]
            
            alpha = 10
            color = maroon if i % 2 == 0 else gold
            draw.polygon(rotated, fill=(*color, alpha))
    
    elif template_name == "Glassmorphism":
        # Subtle noise
        for y in range(0, height, 5):
            noise = random.randint(-3, 3)
            alpha = int(5 + noise)
            draw.line([(0, y), (width, y)], fill=(*maroon, alpha))
    
    elif template_name == "Particle Flow":
        # Particles
        for i in range(15):
            x = (i * 137.5 + t * 30) % width
            y = (i * 234.7 + t * 20) % height
            pulse = 3 + math.sin(t * 3 + x) * 1.5
            draw.ellipse([x-pulse, y-pulse, x+pulse, y+pulse], 
                        fill=(*gold, 180))
    
    else:
        # Simple gradient fallback
        for y in range(height):
            alpha = int(30 * (y / height))
            draw.line([(0, y), (width, y)], fill=(*maroon, alpha))
    
    return canvas

# ============================================================================
# 4. TEXT UTILITIES
# ============================================================================

def wrap_text(text, font, max_width):
    """Wrap text to fit width"""
    words = text.split()
    lines, current = [], []
    
    for word in words:
        test = ' '.join(current + [word])
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(' '.join(current))
            current = [word]
    
    if current:
        lines.append(' '.join(current))
    
    return lines

def draw_text_box(draw, text, zone, font_size, text_color, bg_color=None, 
                  padding=20, align="center", bold=True):
    """Draw text in a box"""
    x1, y1, x2, y2 = [int(v) for v in zone]
    max_width = x2 - x1 - padding * 2
    max_height = y2 - y1 - padding * 2
    
    if max_width <= 0 or max_height <= 0:
        return
    
    # Adjust font size
    while font_size > 24:
        font = get_font(font_size, bold)
        lines = wrap_text(text, font, max_width)
        
        total_h = sum(font.getbbox(line)[3] + 10 for line in lines)
        if total_h <= max_height:
            break
        font_size -= 2
    
    font = get_font(font_size, bold)
    lines = wrap_text(text, font, max_width)
    
    # Draw background
    if bg_color:
        draw.rounded_rectangle([x1, y1, x2, y2], 20, fill=bg_color)
    
    # Draw text
    y = y1 + padding
    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        
        if align == "center":
            x = x1 + (max_width + padding * 2 - text_width) // 2
        elif align == "right":
            x = x2 - text_width - padding
        else:  # left
            x = x1 + padding
        
        draw.text((x, y), line, font=font, fill=text_color)
        y += bbox[3] - bbox[1] + 10

# ============================================================================
# 5. IMAGE LOADING - SIMPLE FIX FOR BIGGER PRODUCT IMAGES
# ============================================================================

@st.cache_data(ttl=3600)
def load_image(image_url, target_size, remove_bg=True):
    """Load and process image - FIXED FOR BIGGER IMAGES"""
    try:
        response = requests.get(image_url, timeout=15, 
                              headers={'User-Agent': 'Mozilla/5.0'})
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        
        if remove_bg:
            try:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                bg_removed = remove(img_bytes.getvalue())
                img = Image.open(io.BytesIO(bg_removed)).convert("RGBA")
            except:
                pass
        
        # SIMPLE FIX: Use resize() instead of thumbnail() for bigger images
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Shadow
        shadow = img.copy().filter(ImageFilter.GaussianBlur(20))
        shadow_data = np.array(shadow)
        shadow_data[:, :, 3] = (shadow_data[:, :, 3] * 0.3).astype(np.uint8)
        shadow = Image.fromarray(shadow_data)
        
        return img, shadow
        
    except Exception as e:
        # Fallback
        img = Image.new("RGBA", target_size, (240, 240, 240, 255))
        shadow = img.copy().filter(ImageFilter.GaussianBlur(15))
        return img, shadow

# ============================================================================
# 6. LOGO & WEBSITE (HIDDEN IN BG)
# ============================================================================

LOGO_URL = "https://www.tripplek.co.ke/wp-content/uploads/2024/10/Tripple-K-Com-Logo-255-by-77.png"
WEBSITE = "www.tripplek.co.ke"

@st.cache_resource
def load_logo():
    """Load brand logo"""
    try:
        logo_img, _ = load_image(LOGO_URL, (500, 500), remove_bg=False)
        return logo_img
    except:
        return None

def add_brand_elements(draw, width, height, colors, t):
    """Add logo and website to background (not in UI)"""
    # Logo in top-left
    logo = load_logo()
    if logo:
        logo_x = int(width * 0.05)
        logo_y = int(height * 0.05)
        alpha = int(200 + 55 * math.sin(t * 0.5))
        logo_data = np.array(logo)
        logo_data[:, :, 3] = (logo_data[:, :, 3] * (alpha/255)).astype(np.uint8)
        logo_with_alpha = Image.fromarray(logo_data)
        
        logo_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        logo_layer.paste(logo_with_alpha, (logo_x, logo_y), logo_with_alpha)
        return logo_layer
    
    return None

# ============================================================================
# 7. FRAME GENERATOR - WITH SIMPLE FIXES
# ============================================================================

def create_frame(t, width, height, content, colors, template_name, product_img=None):
    """Create a single frame"""
    # Background with brand elements
    bg = create_background(template_name, width, height, colors, t)
    
    # Add brand logo
    logo_layer = add_brand_elements(ImageDraw.Draw(bg), width, height, colors, t)
    if logo_layer:
        bg = Image.alpha_composite(bg, logo_layer)
    
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    # Add website in bottom
    if t > 2.0:
        font = get_font(int(height * 0.015), False)
        alpha = int(200 * min(1, (t - 2.0) * 2))
        draw.text((width // 2, int(height * 0.97)), WEBSITE, 
                 font=font, fill=(*colors["text_dark"], alpha), anchor="mm")
    
    # Animation timeline
    if t < 0.3:
        return np.array(Image.alpha_composite(bg, canvas))
    
    # 1. TITLE (fade in)
    title_progress = ease_out(min(1, (t - 0.3) * 2))
    if title_progress > 0 and content.get("title"):
        title_y = int(height * 0.12 - height * 0.05 * (1 - title_progress))
        bg_alpha = int(200 * title_progress)
        
        draw_text_box(
            draw, content["title"].upper(),
            [width * 0.1, title_y, width * 0.9, title_y + int(height * 0.06)],
            int(height * 0.03), colors["white"], (*colors["maroon"], bg_alpha),
            align="center", bold=True
        )
    
    # 2. PRODUCT IMAGE (float) - BIGGER AND BETTER POSITIONED
    product_progress = ease_out(min(1, (t - 0.6) * 1.5))
    if product_progress > 0 and product_img:
        float_offset = math.sin(t * 1.5) * (height * 0.02)
        product_x = int(width * 0.35)  # More centered for bigger image
        product_y = height // 2 + int(float_offset)
        
        img_data = np.array(product_img)
        img_data[:, :, 3] = (img_data[:, :, 3] * product_progress).astype(np.uint8)
        img_with_alpha = Image.fromarray(img_data)
        
        canvas.paste(img_with_alpha, 
                    (product_x - product_img.width // 2, 
                     product_y - product_img.height // 2), 
                    img_with_alpha)
    
    # 3. FEATURES (slide in)
    features_progress = ease_out(min(1, (t - 1.0) * 2))
    if features_progress > 0 and content.get("features"):
        features_x = int(width * 0.6 + width * 0.1 * (1 - features_progress))-50
        features_y = int(height * 0.35)
        feature_h = int(height * 0.035)
        
        for i, feature in enumerate(content["features"][:4]):
            feature_delay = i * 0.1
            feature_progress = ease_out(min(1, (t - 1.0 - feature_delay) * 3))
            
            if feature_progress > 0:
                y = features_y + i * int(feature_h * 1.2)
                offset = int(width * 0.1 * (1 - feature_progress))
                
                bg_alpha = int(240 * feature_progress)
                draw_text_box(
                    draw, f"• {feature}",
                    [features_x + offset, y, features_x + offset + int(width * 0.47), y + feature_h],
                    int(height * 0.015), colors["text_dark"], (*colors["bg_light"], bg_alpha),
                    padding=int(height * 0.015), align="left", bold=False
                )
    
    # 4. PRICE (pulse)
    price_progress = ease_out(min(1, (t - 1.8) * 2))
    if price_progress > 0 and content.get("price"):
        pulse = 1 + 0.05 * math.sin(t * 3)
        price_width = int(width * 0.30 * pulse)
        price_height = int(height * 0.05 * pulse)
        
        price_x = int(width * 0.05)
        price_y = int(height * 0.83)
        
        bg_alpha = int(240 * price_progress)
        draw_text_box(
            draw, content["price"],
            [price_x, price_y, price_x + price_width, price_y + price_height],
            int(height * 0.02 * pulse), colors["white"], (*colors["maroon"], bg_alpha),
            align="center", bold=True
        )
    
    # 5. CTA (bounce)
    cta_progress = ease_out(min(1, (t - 2.2) * 2))
    if cta_progress > 0 and content.get("cta"):
        bounce = 1 + 0.1 * math.sin(t * 6) if cta_progress > 0 else 1.0
        cta_width = int(width * 0.30 * bounce)
        cta_height = int(height * 0.05 * bounce)
        
        cta_x = int(width * 0.65)
        cta_y = int(height * 0.83)
        
        bg_alpha = int(240 * cta_progress)
        draw_text_box(
            draw, content["cta"],
            [cta_x, cta_y, cta_x + cta_width, cta_y + cta_height],
            int(height * 0.025 * bounce), colors["white"], (*colors["gold"], bg_alpha),
            align="center", bold=True
        )

    # Add simple badges
    add_simple_badges(draw, width, height, colors, t)
    
    decorations_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    decorations_layer = add_decorations(decorations_layer, width, height, colors, t, content)
    canvas = Image.alpha_composite(canvas, decorations_layer)

    # Contact info (bottom-left)
    contact_progress = ease_out(min(1, (t - 2.5) * 2))
    if contact_progress > 0:
        font = get_font(int(height * 0.015), False)
        alpha = int(200 * contact_progress)
        
        # Phone icon and number
        phone_y = int(height * 0.90)
        if content.get("phone"):
            # Phone icon
            draw.ellipse([int(width * 0.05), phone_y - int(height * 0.015),
                         int(width * 0.05) + int(height * 0.03), phone_y + int(height * 0.015)],
                        fill=(*colors["maroon"], alpha))
            draw.text((int(width * 0.05) + int(height * 0.015), phone_y),
                     "📞", fill=colors["white"], font=font, anchor="mm")
            
            # Phone number text
            draw.text((int(width * 0.05) + int(height * 0.04), phone_y),
                     content["phone"], 
                     font=font, fill=(*colors["text_dark"], alpha),
                     anchor="lm")

    return np.array(Image.alpha_composite(bg, canvas))

def add_simple_badges(draw, width, height, colors, t):
    """Add simple badges without loading external icons"""
    # "HOT" badge in top-right
    if t > 0.8:
        badge_size = int(height * 0.07)
        badge_x = width - badge_size - int(width * 0.05)
        badge_y = int(height * 0.05)
        
        # Red circle
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                    fill=(255, 50, 50, 220))
        
        # White "HOT" text
        font = get_font(int(height * 0.03), True)
        draw.text((badge_x + badge_size//2, badge_y + badge_size//2),
                 "HOT", fill=colors["white"], 
                 font=font, anchor="mm")
    
    # "NEW" sticker
    if t > 1.0:
        sticker_size = int(height * 0.06)
        sticker_x = int(width * 0.65)
        sticker_y = int(height * 0.40)
        
        # Gold circle
        draw.ellipse([sticker_x, sticker_y, 
                     sticker_x + sticker_size, sticker_y + sticker_size],
                    fill=(*colors["gold"], 220))
        
        # Black "NEW" text
        font = get_font(int(height * 0.025), True)
        draw.text((sticker_x + sticker_size//2, sticker_y + sticker_size//2),
                 "NEW", fill=(0, 0, 0), font=font, anchor="mm")

def add_decorations(canvas, width, height, colors, t, content):
    """Add badges, icons, and decorations with contact info"""
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    # 1. "HOT DEAL" badge (top-right)
    badge_progress = ease_out(min(1, (t - 0.5) * 3))
    if badge_progress > 0:
        badge_size = int(height * 0.08)
        badge_x = width - badge_size - int(width * 0.05)
        badge_y = int(height * 0.05)
        
        # Red badge with gold text
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
                    fill=(255, 50, 50, int(220 * badge_progress)))
        
        font = get_font(int(height * 0.025), True)
        draw.text((badge_x + badge_size//2, badge_y + badge_size//2),
                 "HOT\nDEAL", fill=colors["white"], 
                 font=font, anchor="mm", align="center")
    
    # 2. Social media icons with handles (bottom-right corner)
    social_progress = ease_out(min(1, (t - 2.0) * 2))
    if social_progress > 0:
        icon_size = int(height * 0.045)
        spacing = int(width * 0.02)
        alpha = int(220 * social_progress)
        
        # Instagram
        if content.get("instagram"):
            insta_x = width - int(width * 0.07)
            insta_y = int(height * 0.85)
            
            # Instagram icon
            draw.ellipse([insta_x - icon_size//2, insta_y - icon_size//2,
                         insta_x + icon_size//2, insta_y + icon_size//2],
                        fill=(225, 48, 108, alpha))
            font_icon = get_font(int(height * 0.02), True)
            draw.text((insta_x, insta_y), "IG", 
                     fill=colors["white"], font=font_icon, anchor="mm")
            
            # Instagram handle
            font_handle = get_font(int(height * 0.022), False)
            draw.text((insta_x - int(width * 0.01), insta_y + icon_size//2 + int(height * 0.01)),
                     content["instagram"], 
                     fill=(*colors["text_dark"], alpha), 
                     font=font_handle, anchor="rm")
        
        # Facebook
        if content.get("facebook"):
            fb_x = width - int(width * 0.07)
            fb_y = int(height * 0.90)
            
            # Facebook icon
            draw.ellipse([fb_x - icon_size//2, fb_y - icon_size//2,
                         fb_x + icon_size//2, fb_y + icon_size//2],
                        fill=(66, 103, 178, alpha))
            draw.text((fb_x, fb_y), "FB", 
                     fill=colors["white"], font=font_icon, anchor="mm")
            
            # Facebook handle
            draw.text((fb_x - int(width * 0.01), fb_y + icon_size//2 + int(height * 0.01)),
                     content["facebook"], 
                     fill=(*colors["text_dark"], alpha), 
                     font=font_handle, anchor="rm")
        
        # WhatsApp
        if content.get("phone"):
            wa_x = width - int(width * 0.07)
            wa_y = int(height * 0.95)
            
            # WhatsApp icon
            draw.ellipse([wa_x - icon_size//2, wa_y - icon_size//2,
                         wa_x + icon_size//2, wa_y + icon_size//2],
                        fill=(37, 211, 102, alpha))
            draw.text((wa_x, wa_y), "WA", 
                     fill=colors["white"], font=font_icon, anchor="mm")
            
            # WhatsApp number
            draw.text((wa_x - int(width * 0.01), wa_y + icon_size//2 + int(height * 0.01)),
                     f"{content['phone']}", 
                     fill=(*colors["text_dark"], alpha), 
                     font=font_handle, anchor="rm")
    
    # 3. "NEW" sticker on product
    new_progress = ease_out(min(1, (t - 0.8) * 2))
    if new_progress > 0 and content.get("title"):
        sticker_size = int(height * 0.06)
        sticker_x = int(width * 0.65)
        sticker_y = int(height * 0.45)
        
        draw.ellipse([sticker_x, sticker_y, 
                     sticker_x + sticker_size, sticker_y + sticker_size],
                    fill=(*colors["maroon"], int(220 * new_progress)))
        
        font = get_font(int(height * 0.025), True)
        draw.text((sticker_x + sticker_size//2, sticker_y + sticker_size//2),
                 "NEW", fill=colors["white"], font=font, anchor="mm")
    
    # 4. Add location/address (bottom-left)
    location_progress = ease_out(min(1, (t - 2.5) * 2))
    if location_progress > 0 and content.get("location"):
        font = get_font(int(height * 0.01), False)
        alpha = int(200 * location_progress)
        
        # Location icon
        loc_icon_size = int(height * 0.03)
        loc_x = int(width * 0.05)
        loc_y = int(height * 0.95)
        
        # Map pin icon
        draw.ellipse([loc_x, loc_y - loc_icon_size//2,
                     loc_x + loc_icon_size, loc_y + loc_icon_size//2],
                    fill=(*colors["maroon"], alpha))
        
        # Location text
        draw.text((loc_x + loc_icon_size + int(width * 0.01), loc_y),
                 content["location"], 
                 font=font, fill=(*colors["text_dark"], alpha),
                 anchor="lm")
    
    # 5. Seasonal decorations (snowflakes)
    if content.get("seasonal", False):
        # Snowflakes
        for i in range(10):
            snow_x = (i * 137.5 + t * 50) % width
            snow_y = (t * 100 + i * 50) % height
            draw.ellipse([snow_x-2, snow_y-2, snow_x+2, snow_y+2],
                        fill=(255, 255, 255, 150))
    
    return canvas

# ============================================================================
# 8. VIDEO GENERATOR
# ============================================================================

@st.cache_resource
def download_audio():
    """Download background music"""
    try:
        audio_url = "https://ik.imagekit.io/ericmwangi/advertising-music-308403.mp3?updatedAt=1764101548797"
        response = requests.get(audio_url, timeout=20)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.write(response.content)
        temp_file.close()
        return temp_file.name
    except:
        return None

def generate_video(content, colors, template_name, format_name, 
                  product_image_url, duration=6, add_audio=True):
    """Generate video"""
    width, height = FORMATS[format_name]
    total_frames = FPS * duration
    
    # Load product image at BIGGER SIZE
    product_img, _ = load_image(
        product_image_url, 
        (int(width * 0.8), int(height * 0.7))  # BIGGER: 80% width, 70% height
    )
    
    # Generate frames
    frames = []
    progress_bar = st.progress(0, text="🎬 Rendering video...")
    
    for i in range(total_frames):
        t = i / FPS
        frame = create_frame(t, width, height, content, colors, 
                           template_name, product_img)
        frames.append(frame)
        
        if i % 10 == 0:
            progress_bar.progress((i + 1) / total_frames)
    
    progress_bar.progress(1.0)
    
    # Create video
    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_video.close()
    
    try:
        clip = ImageSequenceClip(frames, fps=FPS)
        
        # Add audio
        if add_audio:
            audio_path = download_audio()
            if audio_path and os.path.exists(audio_path):
                try:
                    audio_clip = AudioFileClip(audio_path)
                    audio_clip = audio_clip.subclip(0, min(audio_clip.duration, clip.duration))
                    clip = clip.set_audio(audio_clip)
                except:
                    pass
        
        clip.write_videofile(
            temp_video.name,
            codec="libx264",
            bitrate="5000k",
            ffmpeg_params=["-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p"],
            logger=None,
            verbose=False,
            threads=2
        )
        clip.close()
        
        return temp_video.name
        
    except Exception as e:
        st.error(f"Video generation failed: {e}")
        return None
    
    finally:
        del frames
        gc.collect()

# ============================================================================
# 9. STREAMLIT UI - CLEAN & SIMPLE
# ============================================================================

def main():
    st.set_page_config(
        page_title="Ultimate Ad Studio",
        page_icon="🎬",
        layout="wide"
    )
    
    # Simple CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #990000 0%, #D4AF37 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    .stButton > button {
        background: linear-gradient(135deg, #990000 0%, #D4AF37 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎬 ULTIMATE AD STUDIO</h1>
        <p>Create professional ad videos in minutes</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main layout
    col_config, col_preview = st.columns([1, 2])
    
    with col_config:
        st.markdown("### ⚙️ Configuration")
        
        # Product Details
        product_name = st.text_input("Product Name", "iPhone 16 Pro Max")
        product_price = st.text_input("Price", "KSh 149,999")
        product_image = st.text_input("Product Image URL", 
                                     "https://www.tripplek.co.ke/wp-content/uploads/2023/07/Untitled-design-2023-05-09T132832.435.jpg")
        
        features_text = st.text_area("Features (one per line)", 
                                    "A18 Pro Chip\n48MP Camera\n1TB Storage\n5G Ready", 
                                    height=100)
        features = [f.strip() for f in features_text.split("\n") if f.strip()]
        
        cta_text = st.text_input("Call-to-Action", "SHOP NOW")

        phone_number = st.text_input("Phone Number", "0715130013")
        location = st.text_input("Shop Location", "Nairobi CBD, Moi Avenue")

        instagram_handle = st.text_input("Instagram", "@tripplek")
        facebook_handle = st.text_input("Facebook", "TrippleK Communications")
        
        # Seasonal toggle - ONLY ONCE in config
        seasonal_decor = st.toggle("🎄 Seasonal Decorations", False, key="seasonal_toggle")
        
        # Design Settings
        color_preset = st.selectbox("Color Palette", list(COLOR_PRESETS.keys()), key="color_preset")
        colors = COLOR_PRESETS[color_preset]
        
        template = st.selectbox("Template", list(TEMPLATES.keys()), key="template")
        
        format_name = st.selectbox("Video Format", list(FORMATS.keys()), key="format")
        
        col1, col2 = st.columns(2)
        with col1:
            remove_bg = st.toggle("Remove BG", value=True, key="remove_bg")
        with col2:
            add_audio = st.toggle("Add Music", value=True, key="add_music")
        
        duration = st.slider("Duration (seconds)", 3, 15, 6, key="duration_slider")
        
        # Generate Button
        generate_btn = st.button("🚀 GENERATE VIDEO", 
                                type="primary", 
                                use_container_width=True,
                                key="generate_btn")
    
    with col_preview:
        st.markdown("### 👁️ Preview")
        
        try:
            # Prepare content - USE seasonal_decor from config
            content = {
                "title": product_name,
                "price": product_price,
                "features": features[:4],
                "cta": cta_text,
                "phone": phone_number,
                "location": location,
                "instagram": instagram_handle,
                "facebook": facebook_handle,
                "seasonal": seasonal_decor  # From config toggle
            }
            
            # USE ACTUAL FORMAT DIMENSIONS
            preview_width, preview_height = FORMATS[format_name]
            
            # LOAD IMAGE AT BIGGER SIZE
            product_img, _ = load_image(
                product_image if product_image else "https://via.placeholder.com/400x600",
                (int(preview_width * 0.8), int(preview_height * 0.7)),  # BIGGER
                remove_bg=remove_bg
            )
            
            # Create frame
            preview_frame = create_frame(3.0, preview_width, preview_height, 
                                    content, colors, template, product_img)
            
            # Show preview
            st.image(preview_frame, use_container_width=True)
            
            # Show actual format info
            st.caption(f"Template: {template} • Format: {format_name} ({preview_width}x{preview_height})")
            
        except Exception as e:
            st.error(f"Could not generate preview: {e}")
            st.info("Check your inputs and try again")
    
    # Generate video
    if generate_btn:
        if not product_name.strip():
            st.error("Please enter a product name")
            return
            
        with st.spinner("Creating your video..."):
            # Prepare content - USE seasonal_decor from config
            content = {
                "title": product_name,
                "price": product_price,
                "features": features[:4],
                "cta": cta_text,
                "phone": phone_number,
                "location": location,
                "instagram": instagram_handle,
                "facebook": facebook_handle,
                "seasonal": seasonal_decor  # From config toggle
            }
            
            # Generate video
            video_path = generate_video(
                content, colors, template, format_name,
                product_image, duration, add_audio
            )
            
            if video_path and os.path.exists(video_path):
                st.success("✅ Video ready!")
                
                # Show video
                st.video(video_path)
                
                # Download button
                with open(video_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Video",
                        f,
                        file_name=f"Ad_{product_name[:20].replace(' ', '_')}.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                
                # Cleanup
                try:
                    os.remove(video_path)
                except:
                    pass
            else:
                st.error("Failed to generate video")

if __name__ == "__main__":
    main()