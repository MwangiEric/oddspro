# simple_ad_creator.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import os
import requests
from datetime import datetime

st.set_page_config(page_title="Simple Ad Creator", layout="wide")

# Session state
if 'bg_image' not in st.session_state:
    st.session_state.bg_image = None
if 'product_image' not in st.session_state:
    st.session_state.product_image = None

def get_font(size, weight='normal'):
    """Load font with fallback"""
    try:
        if weight == 'bold':
            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf"
            ]
        else:
            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf"
            ]
        
        for path in paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except:
        pass
    return ImageFont.load_default()

def load_image_from_source(src):
    """Load image from file upload or URL"""
    if src is None:
        return None
    if isinstance(src, str) and src.startswith('http'):
        try:
            response = requests.get(src, timeout=10)
            return Image.open(BytesIO(response.content)).convert('RGBA')
        except:
            return None
    elif hasattr(src, 'read'):
        return Image.open(src).convert('RGBA')
    return None

def render_ad():
    """Render the final ad"""
    if st.session_state.bg_image is None:
        st.error("Please upload a background image")
        return None
    
    # Start with background
    canvas = st.session_state.bg_image.copy().convert('RGBA')
    
    # Paste product image if available
    if st.session_state.product_image is not None:
        img = st.session_state.product_image.copy()
        
        # Resize product image to specified dimensions
        pw = st.session_state.product_w
        ph = st.session_state.product_h
        img = img.resize((pw, ph), Image.Resampling.LANCZOS)
        
        # Create rounded corners mask if specified
        if st.session_state.product_radius > 0:
            mask = Image.new('L', (pw, ph), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, pw, ph], 
                                       radius=st.session_state.product_radius, fill=255)
            img.putalpha(mask)
        
        # Calculate position (center of specified x,y,w,h box)
        px = st.session_state.product_x
        py = st.session_state.product_y
        
        # Handle out of bounds
        if px + pw > canvas.width:
            px = canvas.width - pw
        if py + ph > canvas.height:
            py = canvas.height - ph
        if px < 0:
            px = 0
        if py < 0:
            py = 0
        
        canvas.paste(img, (px, py), img)
    
    # Draw price text
    if st.session_state.price_text:
        draw = ImageDraw.Draw(canvas)
        
        # Get text dimensions
        font = get_font(st.session_state.price_size, st.session_state.price_weight)
        
        # Handle multiline price
        lines = st.session_state.price_text.split('\n')
        total_height = 0
        line_heights = []
        max_width = 0
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            line_heights.append(h)
            total_height += h * st.session_state.price_line_height
            max_width = max(max_width, w)
        
        # Calculate position
        px = st.session_state.price_x
        py = st.session_state.price_y
        
        # Adjust for alignment
        if st.session_state.price_align == 'center':
            px = px - max_width // 2
        elif st.session_state.price_align == 'right':
            px = px - max_width
        
        # Draw background box if enabled
        if st.session_state.price_bg:
            padding = st.session_state.price_padding
            bg_color = ImageColor.getrgb(st.session_state.price_bg_color)
            draw.rounded_rectangle(
                [px - padding, py - padding, 
                 px + max_width + padding, py + total_height + padding],
                radius=st.session_state.price_radius,
                fill=bg_color
            )
        
        # Draw text
        current_y = py
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            
            if st.session_state.price_align == 'center':
                line_x = px + (max_width - line_w) // 2
            elif st.session_state.price_align == 'right':
                line_x = px + max_width - line_w
            else:
                line_x = px
            
            # Shadow
            if st.session_state.price_shadow:
                shadow_offset = 3
                draw.text((line_x + shadow_offset, current_y + shadow_offset), 
                         line, font=font, fill='black')
            
            # Main text
            text_color = ImageColor.getrgb(st.session_state.price_color)
            draw.text((line_x, current_y), line, font=font, fill=text_color)
            
            current_y += line_heights[i] * st.session_state.price_line_height
    
    return canvas

# UI
st.title("🎨 Simple Ad Creator")
st.markdown("Upload images and position elements manually")

# Layout
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.subheader("📁 Images")
    
    # Background image
    bg_file = st.file_uploader("Background Image", type=['png', 'jpg', 'jpeg', 'webp'])
    if bg_file:
        st.session_state.bg_image = load_image_from_source(bg_file)
        if st.session_state.bg_image:
            st.success(f"✅ {st.session_state.bg_image.width}×{st.session_state.bg_image.height}px")
    
    # Product image
    product_file = st.file_uploader("Product Image (optional)", type=['png', 'jpg', 'jpeg', 'webp'])
    if product_file:
        st.session_state.product_image = load_image_from_source(product_file)
        if st.session_state.product_image:
            st.success(f"✅ {st.session_state.product_image.width}×{st.session_state.product_image.height}px")

with col2:
    st.subheader("📐 Product Image Position")
    
    if st.session_state.bg_image:
        max_w = st.session_state.bg_image.width
        max_h = st.session_state.bg_image.height
    else:
        max_w, max_h = 1080, 1080
    
    st.session_state.product_x = st.number_input("X Position", 0, max_w, 100)
    st.session_state.product_y = st.number_input("Y Position", 0, max_h, 100)
    st.session_state.product_w = st.number_input("Width", 10, max_w, 300)
    st.session_state.product_h = st.number_input("Height", 10, max_h, 300)
    st.session_state.product_radius = st.slider("Corner Radius", 0, 100, 0)
    
    st.markdown("---")
    st.subheader("💰 Price Text")
    
    st.session_state.price_text = st.text_area("Price Text", "99,999\nKES", height=60)
    st.session_state.price_x = st.number_input("Price X", 0, max_w, 500)
    st.session_state.price_y = st.number_input("Price Y", 0, max_h, 100)
    st.session_state.price_size = st.slider("Font Size", 10, 200, 48)
    st.session_state.price_color = st.color_picker("Text Color", "#FFFFFF")
    st.session_state.price_align = st.selectbox("Alignment", ["left", "center", "right"])
    st.session_state.price_weight = st.selectbox("Font Weight", ["normal", "bold"])
    st.session_state.price_line_height = st.slider("Line Height", 0.5, 2.0, 1.2)

with col3:
    st.subheader("👁️ Preview")
    
    # Price background options
    with st.expander("Price Background Options"):
        st.session_state.price_bg = st.checkbox("Enable Background", True)
        st.session_state.price_bg_color = st.color_picker("BG Color", "#000000")
        st.session_state.price_padding = st.slider("Padding", 0, 50, 10)
        st.session_state.price_radius = st.slider("BG Corner Radius", 0, 50, 8)
        st.session_state.price_shadow = st.checkbox("Text Shadow", True)
    
    # Render button
    if st.button("✨ Generate Ad", type="primary", use_container_width=True):
        result = render_ad()
        if result:
            st.image(result, use_column_width=True)
            
            # Downloads
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            
            with col_dl1:
                buf = BytesIO()
                result.save(buf, format="PNG")
                st.download_button("💾 PNG", buf.getvalue(), 
                                 f"ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", 
                                 "image/png", use_container_width=True)
            
            with col_dl2:
                buf = BytesIO()
                result.convert('RGB').save(buf, format="JPEG", quality=95)
                st.download_button("💾 JPG", buf.getvalue(), 
                                 f"ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg", 
                                 "image/jpeg", use_column_width=True)
            
            with col_dl3:
                buf = BytesIO()
                result.save(buf, format="WEBP", quality=95)
                st.download_button("💾 WebP", buf.getvalue(), 
                                 f"ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp", 
                                 "image/webp", use_container_width=True)

# Quick position guides
if st.session_state.bg_image:
    st.markdown("---")
    st.subheader("📍 Quick Position Guides")
    
    w = st.session_state.bg_image.width
    h = st.session_state.bg_image.height
    
    cols = st.columns(4)
    guides = [
        ("Top Left", 50, 50),
        ("Top Right", w - 350, 50),
        ("Bottom Left", 50, h - 350),
        ("Bottom Right", w - 350, h - 350),
        ("Center", w//2 - 150, h//2 - 150),
        ("Top Center", w//2 - 150, 50),
        ("Bottom Center", w//2 - 150, h - 350),
    ]
    
    for i, (name, x, y) in enumerate(guides):
        with cols[i % 4]:
            if st.button(f"📌 {name}", key=f"guide_{i}"):
                st.session_state.product_x = max(0, int(x))
                st.session_state.product_y = max(0, int(y))
                st.session_state.product_w = 300
                st.session_state.product_h = 300
                st.rerun()
