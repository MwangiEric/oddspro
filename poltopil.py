import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import os
import requests
import pandas as pd
from datetime import datetime
import zipfile
import textwrap
import json
import re

st.set_page_config(page_title="Bulk Ad Generator", layout="wide")

# API Configuration
IMAGAPI_BASE = "https://imagapi.vercel.app/api/v1"

# Social Media Presets
SOCIAL_PRESETS = {
    "Instagram Post (Square)": (1080, 1080),
    "Instagram Story": (1080, 1920),
    "Instagram Reel": (1080, 1920),
    "Facebook Post": (1200, 630),
    "Facebook Story": (1080, 1920),
    "WhatsApp Status": (1080, 1920),
    "Twitter/X Post": (1200, 675),
    "LinkedIn Post": (1200, 627),
    "Pinterest Pin": (1000, 1500),
    "YouTube Thumbnail": (1280, 720),
    "Custom": None
}

# Session state initialization
defaults = {
    'base_image': None,
    'csv_data': None,
    'generated_ads': [],
    'canvas_size': (1080, 1080),
    'canvas_preset': "Instagram Post (Square)",
    'name_col': 0,
    'price_col': 1,
    'image_col': 2,
    'use_image_search': False,
    'api_file_type': 'png',
    'polotno_template': None,
    'polotno_fields': {},
    'use_polotno': False,
    'extracted_name': None,  # Store extracted name from first row
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def extract_product_name(full_name):
    """Extract product name (text before first ' - ')"""
    if not full_name or pd.isna(full_name):
        return ""
    text = str(full_name).strip()
    # Split on " - " and take first part
    parts = text.split(' - ', 1)
    return parts[0].strip()

def parse_polotno_json(json_data):
    """Parse Polotno JSON and extract placeholder fields"""
    fields = {
        'product_name': None,
        'price': None,
        'product_image': None
    }
    
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
            
        pages = data.get('pages', [])
        if not pages:
            return fields
            
        # Look through all elements in all pages
        for page in pages:
            elements = page.get('children', [])
            for el in elements:
                el_type = el.get('type', '')
                name = el.get('name', '')
                
                # Check for text placeholders
                if el_type == 'text':
                    if name == '{product_name}' and not fields['product_name']:
                        fields['product_name'] = {
                            'x': el.get('x', 0),
                            'y': el.get('y', 0),
                            'width': el.get('width', 200),
                            'height': el.get('height', 50),
                            'fontSize': el.get('fontSize', 24),
                            'fontFamily': el.get('fontFamily', 'Arial'),
                            'fill': el.get('fill', '#000000'),
                            'align': el.get('align', 'left')
                        }
                    elif name == '{price}' and not fields['price']:
                        fields['price'] = {
                            'x': el.get('x', 0),
                            'y': el.get('y', 0),
                            'width': el.get('width', 200),
                            'height': el.get('height', 50),
                            'fontSize': el.get('fontSize', 36),
                            'fontFamily': el.get('fontFamily', 'Arial'),
                            'fill': el.get('fill', '#000000'),
                            'align': el.get('align', 'left')
                        }
                
                # Check for image placeholder
                elif el_type == 'image' and name == '{product_image_placeholder}':
                    fields['product_image'] = {
                        'x': el.get('x', 0),
                        'y': el.get('y', 0),
                        'width': el.get('width', 400),
                        'height': el.get('height', 400),
                        'borderRadius': el.get('borderRadius', 0)
                    }
        
        return fields
    except Exception as e:
        st.error(f"Error parsing Polotno JSON: {e}")
        return fields

def search_product_image(query, file_type='png'):
    """Search for product image using ImagAPI"""
    if not query or pd.isna(query):
        return None
    
    # Use extracted name for search
    search_query = extract_product_name(query)
    
    try:
        url = f"{IMAGAPI_BASE}/products/search"
        params = {
            "q": str(search_query)[:100],
            "file_type": file_type,
            "limit": 5
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        images = data.get("images", []) or data.get("results", []) or []
        
        if images and len(images) > 0:
            for img in images:
                image_url = (img.get('url') or 
                            img.get('image_url') or 
                            img.get('src') or
                            img.get('link'))
                
                if image_url:
                    return {
                        'url': image_url,
                        'thumbnail': img.get('thumbnail') or image_url,
                        'source': img.get('source', 'imagapi')
                    }
        return None
    except Exception as e:
        st.warning(f"Search failed: {str(e)[:80]}")
        return None

def get_font(size, weight='normal', family='Arial'):
    """Load font with fallback"""
    try:
        # Try to match font family
        font_map = {
            'Arial': ['arial.ttf', 'arialbd.ttf'],
            'Helvetica': ['Helvetica.ttc'],
            'DejaVu': ['DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'],
            'Roboto': ['Roboto-Regular.ttf', 'Roboto-Bold.ttf']
        }
        
        if weight == 'bold':
            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ]
        else:
            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]
        
        for path in paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except:
        pass
    return ImageFont.load_default()

def load_image_from_url(url):
    """Load image from URL with timeout"""
    if not url or pd.isna(url):
        return None
    try:
        url = str(url).strip()
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://imagapi.vercel.app' + url
            
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')
    except Exception as e:
        return None

def wrap_text_to_lines(text, font, max_width, max_lines=2):
    """Wrap text to fit within max_width"""
    if not text:
        return [""]
    
    text = str(text).strip()
    bbox = font.getbbox(text)
    if bbox[2] - bbox[0] <= max_width:
        return [text]
    
    avg_char_width = (bbox[2] - bbox[0]) / len(text) if len(text) > 0 else 10
    chars_per_line = int(max_width / avg_char_width) if avg_char_width > 0 else 20
    
    wrapped = textwrap.wrap(text, width=max(chars_per_line, 10), 
                           break_long_words=True, break_on_hyphens=True)
    
    if len(wrapped) > max_lines:
        result = wrapped[:max_lines-1]
        last_line = wrapped[max_lines-1]
        while len(last_line) > 3:
            test_line = last_line + "..."
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                result.append(test_line)
                break
            last_line = last_line[:-1]
        else:
            result.append("...")
        return result
    
    return wrapped

def draw_text_block(draw, lines, x, y, font, color, align='left', 
                    bg=False, bg_color=(0,0,0), padding=10, radius=8, 
                    shadow=False, line_height=1.2):
    """Draw multiple lines of text with styling"""
    if not lines:
        return y
    
    max_width = 0
    total_height = 0
    line_heights = []
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_width = max(max_width, w)
        line_heights.append(h)
        total_height += h * line_height
    
    first_line_h = line_heights[0] if line_heights else font.size
    y = y - first_line_h + font.size
    
    if bg:
        bg_x = x
        if align == 'center':
            bg_x = x - max_width // 2 - padding
        elif align == 'right':
            bg_x = x - max_width - padding
        
        bg_rect = [
            bg_x,
            y - padding,
            bg_x + max_width + padding * 2,
            y + total_height + padding
        ]
        draw.rounded_rectangle(bg_rect, radius=radius, fill=bg_color)
    
    current_y = y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        
        line_x = x
        if align == 'center':
            line_x = x - line_w // 2
        elif align == 'right':
            line_x = x - line_w
        
        if shadow:
            draw.text((line_x + 2, current_y + 2), line, font=font, fill='black')
        
        draw.text((line_x, current_y), line, font=font, fill=color)
        current_y += line_heights[i] * line_height
    
    return current_y

def render_single_ad(canvas_size, base_image, product_image, product_name, price, config):
    """Render a single ad with given parameters"""
    canvas = Image.new('RGBA', canvas_size, (255, 255, 255, 255))
    
    # Paste base image
    if base_image:
        bg = base_image.copy().resize(canvas_size, Image.Resampling.LANCZOS)
        canvas.paste(bg, (0, 0), bg)
    
    draw = ImageDraw.Draw(canvas)
    
    # Check if using Polotno template
    if config.get('use_polotno') and config.get('polotno_fields'):
        fields = config['polotno_fields']
        
        # Draw Product Name
        if fields.get('product_name') and product_name and config.get('show_product_name', True):
            field = fields['product_name']
            name_font = get_font(field.get('fontSize', 32), 'bold', field.get('fontFamily', 'Arial'))
            name_color = field.get('fill', '#FFFFFF')
            if isinstance(name_color, str):
                name_color = ImageColor.getrgb(name_color)
            
            max_width = field.get('width', 800)
            wrapped_lines = wrap_text_to_lines(
                str(product_name), 
                name_font, 
                max_width,
                config.get('name_max_lines', 2)
            )
            
            # Simple text drawing for Polotno (no background/shadow for now)
            x, y = field.get('x', 100), field.get('y', 100)
            align = field.get('align', 'left')
            
            current_y = y
            for line in wrapped_lines:
                bbox = draw.textbbox((0, 0), line, font=name_font)
                line_w = bbox[2] - bbox[0]
                
                line_x = x
                if align == 'center':
                    line_x = x - line_w // 2
                elif align == 'right':
                    line_x = x - line_w
                
                draw.text((line_x, current_y), line, font=name_font, fill=name_color)
                current_y += name_font.size * 1.2
        
        # Draw Price
        if fields.get('price') and price:
            field = fields['price']
            price_font = get_font(field.get('fontSize', 48), 'bold', field.get('fontFamily', 'Arial'))
            price_color = field.get('fill', '#FFFFFF')
            if isinstance(price_color, str):
                price_color = ImageColor.getrgb(price_color)
            
            x, y = field.get('x', 100), field.get('y', 650)
            align = field.get('align', 'left')
            price_str = str(price)
            lines = price_str.split('\n')
            
            current_y = y
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=price_font)
                line_w = bbox[2] - bbox[0]
                
                line_x = x
                if align == 'center':
                    line_x = x - line_w // 2
                elif align == 'right':
                    line_x = x - line_w
                
                draw.text((line_x, current_y), line, font=price_font, fill=price_color)
                current_y += price_font.size * 1.2
        
        # Paste Product Image
        if fields.get('product_image') and product_image is not None:
            field = fields['product_image']
            img = product_image.copy()
            
            pw = int(field.get('width', 400))
            ph = int(field.get('height', 400))
            img = img.resize((pw, ph), Image.Resampling.LANCZOS)
            
            radius = field.get('borderRadius', 0)
            if radius > 0:
                mask = Image.new('L', (pw, ph), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, pw, ph], radius=int(radius), fill=255)
                img.putalpha(mask)
            
            px = int(field.get('x', 100))
            py = int(field.get('y', 200))
            canvas.paste(img, (px, py), img)
    
    else:
        # Legacy manual positioning
        # Draw Product Name
        if config.get('show_product_name') and product_name:
            name_font = get_font(config['name_size'], config['name_weight'])
            name_color = ImageColor.getrgb(config['name_color'])
            name_bg_color = ImageColor.getrgb(config['name_bg_color'])
            
            wrapped_lines = wrap_text_to_lines(
                str(product_name), 
                name_font, 
                config.get('name_max_width', canvas_size[0] - 200),
                config.get('name_max_lines', 2)
            )
            
            draw_text_block(
                draw, wrapped_lines, 
                config['name_x'], config['name_y'],
                name_font, name_color, config['name_align'],
                config['name_bg'], name_bg_color, 
                config['name_padding'], config['name_radius'],
                config['name_shadow'], 1.3
            )
        
        # Paste Product Image
        if product_image is not None:
            img = product_image.copy()
            pw = config['product_w']
            ph = config['product_h']
            img = img.resize((pw, ph), Image.Resampling.LANCZOS)
            
            if config['product_radius'] > 0:
                mask = Image.new('L', (pw, ph), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, pw, ph], 
                                           radius=config['product_radius'], fill=255)
                img.putalpha(mask)
            
            px = max(0, min(config['product_x'], canvas_size[0] - pw))
            py = max(0, min(config['product_y'], canvas_size[1] - ph))
            canvas.paste(img, (px, py), img)
        
        # Draw Price
        if price:
            price_font = get_font(config['price_size'], config['price_weight'])
            price_color = ImageColor.getrgb(config['price_color'])
            price_bg_color = ImageColor.getrgb(config['price_bg_color'])
            
            price_str = str(price)
            lines = price_str.split('\n')
            
            draw_text_block(
                draw, lines,
                config['price_x'], config['price_y'],
                price_font, price_color, config['price_align'],
                config['price_bg'], price_bg_color,
                config['price_padding'], config['price_radius'],
                config['price_shadow'], config['price_line_height']
            )
    
    return canvas

def create_zip_download(images, names):
    """Create a ZIP file with all generated images"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, (img, name) in enumerate(zip(images, names)):
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name[:50]
            filename = f"{i+1:03d}_{safe_name}.png"
            zip_file.writestr(filename, img_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def get_csv_download_link(df):
    """Generate CSV download"""
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("📦 Bulk Ad Generator")
    st.markdown("Configure your ad generation settings here.")
    
    st.header("1️⃣ Canvas Size")
    preset = st.selectbox("Platform Preset", list(SOCIAL_PRESETS.keys()), 
                          index=list(SOCIAL_PRESETS.keys()).index(st.session_state.canvas_preset))
    
    if preset == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            custom_w = st.number_input("Width", 100, 4000, st.session_state.canvas_size[0])
        with col2:
            custom_h = st.number_input("Height", 100, 4000, st.session_state.canvas_size[1])
        st.session_state.canvas_size = (custom_w, custom_h)
    else:
        st.session_state.canvas_size = SOCIAL_PRESETS[preset]
        st.session_state.canvas_preset = preset
    
    st.info(f"Canvas: {st.session_state.canvas_size[0]}×{st.session_state.canvas_size[1]}px")
    
    # Polotno Template Upload
    st.header("2️⃣ Polotno Template")
    polotno_file = st.file_uploader("Upload Polotno JSON", type=['json'], key="polotno")
    
    if polotno_file:
        try:
            json_content = json.load(polotno_file)
            fields = parse_polotno_json(json_content)
            st.session_state.polotno_template = json_content
            st.session_state.polotno_fields = fields
            st.session_state.use_polotno = True
            
            st.success("✅ Polotno template loaded!")
            
            # Show detected fields
            with st.expander("Detected Fields"):
                if fields['product_name']:
                    st.write(f"📛 Product Name: x={fields['product_name']['x']:.0f}, y={fields['product_name']['y']:.0f}")
                if fields['price']:
                    st.write(f"💰 Price: x={fields['price']['x']:.0f}, y={fields['price']['y']:.0f}")
                if fields['product_image']:
                    st.write(f"🖼️ Image: x={fields['product_image']['x']:.0f}, y={fields['product_image']['y']:.0f}")
            
            if not any(fields.values()):
                st.warning("⚠️ No placeholders found. Expected: {product_name}, {price}, {product_image_placeholder}")
        except Exception as e:
            st.error(f"Error loading Polotno file: {e}")
            st.session_state.use_polotno = False
    
    # Base Image Upload (only if not using Polotno)
    if not st.session_state.use_polotno:
        st.header("3️⃣ Base Template")
        base_file = st.file_uploader("Upload base image", 
                                     type=['png', 'jpg', 'jpeg', 'webp'], key="base")
        if base_file:
            st.session_state.base_image = Image.open(base_file).convert('RGBA')
            st.success("✅ Base image loaded")
    
    # CSV Upload
    st.header("4️⃣ Product Data")
    csv_file = st.file_uploader("Upload CSV", type=['csv'], key="csv")
    
    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            st.session_state.csv_data = df
            st.success(f"✅ Loaded {len(df)} products")
            
            # Show extracted name example
            if len(df) > 0:
                sample_full = df.iloc[0, 0]  # Assume first col
                sample_extracted = extract_product_name(sample_full)
                st.caption(f"Name extraction: '{str(sample_full)[:30]}...' → '{sample_extracted[:30]}...'")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")

# ==================== MAIN CONTENT ====================
st.title("📦 Bulk Ad Generator")
st.markdown("Upload CSV with product data and generate ads for social media")

# Show current configuration
if st.session_state.use_polotno:
    st.success("🎨 Using Polotno template for layout")
elif st.session_state.base_image:
    st.info("🖼️ Using uploaded base image")
else:
    st.info("⚪ Using blank canvas")

# Column Mapping (if CSV loaded)
if st.session_state.csv_data is not None:
    st.header("Column Mapping")
    
    df = st.session_state.csv_data
    num_cols = len(df.columns)
    col_names = list(df.columns)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.session_state.name_col = st.selectbox(
            "Product Name Column",
            range(num_cols),
            format_func=lambda i: f"{i}: {col_names[i]}",
            index=min(st.session_state.name_col, num_cols-1)
        )
        sample = df.iloc[0, st.session_state.name_col] if len(df) > 0 else "N/A"
        extracted = extract_product_name(sample)
        st.caption(f"Sample: {str(sample)[:30]}...")
        st.caption(f"Extracted: {str(extracted)[:30]}...")
    
    with col2:
        st.session_state.price_col = st.selectbox(
            "Price Column",
            range(num_cols),
            format_func=lambda i: f"{i}: {col_names[i]}",
            index=min(st.session_state.price_col, num_cols-1)
        )
        sample = df.iloc[0, st.session_state.price_col] if len(df) > 0 else "N/A"
        st.caption(f"Sample: {str(sample)[:30]}...")
    
    with col3:
        use_search = st.checkbox("🔍 Use ImagAPI Search", 
                                value=st.session_state.use_image_search)
        st.session_state.use_image_search = use_search
        
        if use_search:
            st.session_state.api_file_type = st.selectbox(
                "Image Format", 
                ['png', 'jpg', 'webp'],
                index=['png', 'jpg', 'webp'].index(st.session_state.api_file_type)
            )
            st.caption(f"Searching: '{extracted[:20]}...'")
        else:
            st.session_state.image_col = st.selectbox(
                "Image URL Column",
                range(num_cols),
                format_func=lambda i: f"{i}: {col_names[i]}",
                index=min(st.session_state.image_col, num_cols-1)
            )

# Manual Layout Settings (only if not using Polotno)
if st.session_state.csv_data is not None and not st.session_state.use_polotno:
    st.header("Manual Layout Settings")
    
    cw, ch = st.session_state.canvas_size
    
    with st.expander("🏷️ Product Name Settings"):
        st.session_state.show_product_name = st.checkbox("Show Product Name", 
                                                        st.session_state.show_product_name)
        
        if st.session_state.show_product_name:
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.name_x = st.number_input("Name X", 0, cw, st.session_state.name_x)
                st.session_state.name_y = st.number_input("Name Y", 0, ch, st.session_state.name_y)
                st.session_state.name_size = st.slider("Font Size", 10, 80, 32)
            with col2:
                st.session_state.name_align = st.selectbox("Align", ["left", "center", "right"])
                st.session_state.name_weight = st.selectbox("Weight", ["normal", "bold"])
                st.session_state.name_color = st.color_picker("Color", '#FFFFFF')
            
            st.session_state.name_max_width = st.slider("Max Width", 200, cw-100, 800)
            st.session_state.name_max_lines = st.slider("Max Lines", 1, 3, 2)
    
    with st.expander("📐 Product Image Settings"):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.product_x = st.number_input("Image X", 0, cw, 100)
            st.session_state.product_y = st.number_input("Image Y", 0, ch, 200)
        with col2:
            st.session_state.product_w = st.number_input("Width", 10, cw, 400)
            st.session_state.product_h = st.number_input("Height", 10, ch, 400)
        
        st.session_state.product_radius = st.slider("Corner Radius", 0, 100, 20)
    
    with st.expander("💰 Price Settings"):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.price_x = st.number_input("Price X", 0, cw, 100)
            st.session_state.price_y = st.number_input("Price Y", 0, ch, 650)
            st.session_state.price_size = st.slider("Price Font Size", 10, 150, 48)
        with col2:
            st.session_state.price_align = st.selectbox("Price Align", ["left", "center", "right"])
            st.session_state.price_weight = st.selectbox("Price Weight", ["normal", "bold"])
            st.session_state.price_color = st.color_picker("Price Color", '#FFFFFF')

# Preview and Generate
if st.session_state.csv_data is not None:
    st.header("Preview & Generate")
    
    df = st.session_state.csv_data.copy()
    
    # Preview first product
    with st.expander("👁️ Preview First Product"):
        if len(df) > 0:
            row = df.iloc[0]
            full_name = row.iloc[st.session_state.name_col]
            name = extract_product_name(full_name)
            price = row.iloc[st.session_state.price_col]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Full Name:** {full_name}")
                st.write(f"**Extracted:** {name}")
                st.write(f"**Price:** {price}")
            
            # Get image
            if st.session_state.use_image_search:
                with st.spinner("Searching image..."):
                    result = search_product_image(full_name, st.session_state.api_file_type)
                    img_url = result['url'] if result else None
                    if result:
                        st.success(f"Found: {result['url'][:50]}...")
            else:
                img_url = row.iloc[st.session_state.image_col]
            
            with col2:
                st.write(f"**Image URL:** {str(img_url)[:50] if img_url else 'None'}...")
            
            product_img = load_image_from_url(img_url)
            
            # Build config
            config = {
                'use_polotno': st.session_state.use_polotno,
                'polotno_fields': st.session_state.polotno_fields,
                'show_product_name': st.session_state.get('show_product_name', True),
                'name_max_lines': st.session_state.get('name_max_lines', 2),
            }
            
            # Add manual settings if not using Polotno
            if not st.session_state.use_polotno:
                config.update({
                    'name_x': st.session_state.name_x, 'name_y': st.session_state.name_y,
                    'name_size': st.session_state.name_size, 'name_color': st.session_state.name_color,
                    'name_align': st.session_state.name_align, 'name_weight': st.session_state.name_weight,
                    'name_bg': True, 'name_bg_color': '#000000', 'name_padding': 12,
                    'name_radius': 8, 'name_shadow': True, 'name_max_width': st.session_state.name_max_width,
                    'product_x': st.session_state.product_x, 'product_y': st.session_state.product_y,
                    'product_w': st.session_state.product_w, 'product_h': st.session_state.product_h,
                    'product_radius': st.session_state.product_radius,
                    'price_x': st.session_state.price_x, 'price_y': st.session_state.price_y,
                    'price_size': st.session_state.price_size, 'price_color': st.session_state.price_color,
                    'price_align': st.session_state.price_align, 'price_weight': st.session_state.price_weight,
                    'price_bg': True, 'price_bg_color': '#000000', 'price_padding': 15,
                    'price_radius': 10, 'price_shadow': True, 'price_line_height': 1.2,
                })
            
            preview = render_single_ad(
                st.session_state.canvas_size, 
                st.session_state.base_image, 
                product_img, name, price, config
            )
            st.image(preview, use_column_width=True)
    
    # Generate All
    if st.button("🚀 Generate All Ads", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated = []
        names = []
        search_urls = []
        
        config = {
            'use_polotno': st.session_state.use_polotno,
            'polotno_fields': st.session_state.polotno_fields,
            'show_product_name': st.session_state.get('show_product_name', True),
            'name_max_lines': st.session_state.get('name_max_lines', 2),
        }
        
        if not st.session_state.use_polotno:
            config.update({
                'name_x': st.session_state.name_x, 'name_y': st.session_state.name_y,
                'name_size': st.session_state.name_size, 'name_color': st.session_state.name_color,
                'name_align': st.session_state.name_align, 'name_weight': st.session_state.name_weight,
                'name_bg': True, 'name_bg_color': '#000000', 'name_padding': 12,
                'name_radius': 8, 'name_shadow': True, 'name_max_width': st.session_state.name_max_width,
                'product_x': st.session_state.product_x, 'product_y': st.session_state.product_y,
                'product_w': st.session_state.product_w, 'product_h': st.session_state.product_h,
                'product_radius': st.session_state.product_radius,
                'price_x': st.session_state.price_x, 'price_y': st.session_state.price_y,
                'price_size': st.session_state.price_size, 'price_color': st.session_state.price_color,
                'price_align': st.session_state.price_align, 'price_weight': st.session_state.price_weight,
                'price_bg': True, 'price_bg_color': '#000000', 'price_padding': 15,
                'price_radius': 10, 'price_shadow': True, 'price_line_height': 1.2,
            })
        
        for idx, row in df.iterrows():
            progress = (idx + 1) / len(df)
            progress_bar.progress(min(progress, 0.99))
            
            full_name = row.iloc[st.session_state.name_col]
            name = extract_product_name(full_name)
            price = row.iloc[st.session_state.price_col]
            
            status_text.text(f"Processing {idx + 1}/{len(df)}: {str(name)[:30]}...")
            
            # Get image
            if st.session_state.use_image_search:
                result = search_product_image(full_name, st.session_state.api_file_type)
                img_url = result['url'] if result else None
                search_urls.append(img_url if img_url else "")
            else:
                img_url = row.iloc[st.session_state.image_col]
                search_urls.append("")
            
            # Render
            product_img = load_image_from_url(img_url)
            ad = render_single_ad(
                st.session_state.canvas_size, 
                st.session_state.base_image, 
                product_img, name, price, config
            )
            
            generated.append(ad)
            names.append(str(name))
        
        progress_bar.empty()
        status_text.empty()
        
        # Add search URLs to CSV
        if st.session_state.use_image_search:
            df['imagapi_image_url'] = search_urls
            df['extracted_name'] = df.iloc[:, st.session_state.name_col].apply(extract_product_name)
        
        st.session_state.generated_ads = generated
        st.session_state.csv_data = df
        
        st.success(f"✅ Generated {len(generated)} ads!")
        
        # Downloads
        col1, col2 = st.columns(2)
        
        with col1:
            zip_data = create_zip_download(generated, names)
            st.download_button(
                "📦 Download All Images (ZIP)",
                zip_data,
                f"ads_{st.session_state.canvas_size[0]}x{st.session_state.canvas_size[1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                "application/zip",
                use_container_width=True
            )
        
        with col2:
            csv_data = get_csv_download_link(df)
            st.download_button(
                "📄 Download Updated CSV",
                csv_data,
                f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        # Show gallery
        with st.expander(f"View All {min(len(generated), 12)} Ads"):
            cols = st.columns(3)
            for i, (img, name) in enumerate(zip(generated[:12], names[:12])):
                with cols[i % 3]:
                    st.image(img, caption=f"{i+1}. {name[:40]}", use_column_width=True)
