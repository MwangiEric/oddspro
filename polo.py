# bulk_ad_generator.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import os
import requests
import pandas as pd
from datetime import datetime
import zipfile

st.set_page_config(page_title="Bulk Ad Generator", layout="wide")

# API Configuration - FIXED ENDPOINT
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
    'name_col': 2,
    'price_col': 3,
    'image_col': 4,
    'product_x': 100,
    'product_y': 150,
    'product_w': 400,
    'product_h': 400,
    'product_radius': 20,
    'price_x': 100,
    'price_y': 600,
    'price_size': 48,
    'price_color': '#FFFFFF',
    'price_align': 'left',
    'price_weight': 'bold',
    'price_bg': True,
    'price_bg_color': '#000000',
    'price_padding': 15,
    'price_radius': 10,
    'price_shadow': True,
    'price_line_height': 1.2,
    'show_product_name': True,
    'name_x': 100,
    'name_y': 80,
    'name_size': 36,
    'name_color': '#FFFFFF',
    'name_align': 'left',
    'name_weight': 'bold',
    'name_bg': True,
    'name_bg_color': '#000000',
    'name_padding': 10,
    'name_radius': 8,
    'name_shadow': True,
    'name_max_chars': 40,
    'use_image_search': False,
    'image_search_col': None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def search_product_image(query):
    """Search for product image using ImagAPI - FIXED ENDPOINT"""
    if not query or pd.isna(query):
        return None
    
    try:
        # FIXED: Use correct endpoint /search not /assets/search
        url = f"{IMAGAPI_BASE}/search"
        params = {
            "q": str(query)[:100],
            "limit": 1  # Only need first result
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Parse response - handle different possible structures
        images = data.get("images", []) or data.get("results", []) or data.get("data", [])
        
        if images and len(images) > 0:
            first_image = images[0]
            # Handle different response formats
            image_url = (first_image.get('url') or 
                        first_image.get('image_url') or 
                        first_image.get('src') or
                        first_image.get('link'))
            
            if image_url:
                return {
                    'url': image_url,
                    'thumbnail': first_image.get('thumbnail') or image_url,
                    'source': first_image.get('source', 'imagapi')
                }
        return None
    except Exception as e:
        st.warning(f"Image search failed: {str(e)[:100]}")
        return None

def get_font(size, weight='normal'):
    """Load font with fallback"""
    try:
        if weight == 'bold':
            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
            ]
        else:
            paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
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
        # Handle relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://imagapi.vercel.app' + url
            
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')
    except Exception as e:
        return None

def draw_text_with_style(draw, text, x, y, font, color, align='left', 
                         bg=False, bg_color=(0,0,0), padding=10, radius=8, 
                         shadow=False, max_width=None):
    """Helper to draw styled text with background and shadow"""
    if not text:
        return y
    
    # Calculate text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Truncate if too long
    if max_width and text_w > max_width:
        while text_w > max_width and len(text) > 3:
            text = text[:-4] + "..."
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
    
    # Alignment
    if align == 'center':
        x = x - text_w // 2
    elif align == 'right':
        x = x - text_w
    
    # Draw background
    if bg:
        bg_rect = [x - padding, y - padding, x + text_w + padding, y + text_h + padding]
        draw.rounded_rectangle(bg_rect, radius=radius, fill=bg_color)
    
    # Draw shadow
    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill='black')
    
    # Draw text
    draw.text((x, y), text, font=font, fill=color)
    
    return y + text_h

def render_single_ad(canvas_size, base_image, product_image, product_name, price, config):
    """Render a single ad with given parameters"""
    # Create canvas with specified size
    canvas = Image.new('RGBA', canvas_size, (255, 255, 255, 255))
    
    # Paste base image (resize to fit canvas)
    if base_image:
        bg = base_image.copy().resize(canvas_size, Image.Resampling.LANCZOS)
        canvas.paste(bg, (0, 0), bg)
    
    draw = ImageDraw.Draw(canvas)
    
    # Draw Product Name
    if config.get('show_product_name') and product_name:
        name_font = get_font(config['name_size'], config['name_weight'])
        name_color = ImageColor.getrgb(config['name_color'])
        name_bg_color = ImageColor.getrgb(config['name_bg_color'])
        
        # Truncate name if too long
        name_text = str(product_name)
        if len(name_text) > config.get('name_max_chars', 50):
            name_text = name_text[:47] + "..."
        
        draw_text_with_style(
            draw, name_text, config['name_x'], config['name_y'],
            name_font, name_color, config['name_align'],
            config['name_bg'], name_bg_color, config['name_padding'],
            config['name_radius'], config['name_shadow'],
            max_width=canvas_size[0] - config['name_x'] - 50
        )
    
    # Paste Product Image
    if product_image is not None:
        img = product_image.copy()
        
        # Resize
        pw = config['product_w']
        ph = config['product_h']
        img = img.resize((pw, ph), Image.Resampling.LANCZOS)
        
        # Rounded corners
        if config['product_radius'] > 0:
            mask = Image.new('L', (pw, ph), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, pw, ph], 
                                       radius=config['product_radius'], fill=255)
            img.putalpha(mask)
        
        # Position with bounds checking
        px = max(0, min(config['product_x'], canvas_size[0] - pw))
        py = max(0, min(config['product_y'], canvas_size[1] - ph))
        
        canvas.paste(img, (px, py), img)
    
    # Draw Price
    if price:
        price_font = get_font(config['price_size'], config['price_weight'])
        price_color = ImageColor.getrgb(config['price_color'])
        price_bg_color = ImageColor.getrgb(config['price_bg_color'])
        
        # Handle multiline price
        price_str = str(price)
        lines = price_str.split('\n')
        
        current_y = config['price_y']
        max_line_width = 0
        
        # Calculate max width for background
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=price_font)
            max_line_width = max(max_line_width, bbox[2] - bbox[0])
        
        # Draw background box for all lines
        if config['price_bg'] and lines:
            total_height = sum(draw.textbbox((0, 0), line, font=price_font)[3] - 
                              draw.textbbox((0, 0), line, font=price_font)[1] 
                              for line in lines)
            total_height += (len(lines) - 1) * int(config['price_size'] * (config['price_line_height'] - 1))
            
            bg_x = config['price_x']
            if config['price_align'] == 'center':
                bg_x = config['price_x'] - max_line_width // 2 - config['price_padding']
            elif config['price_align'] == 'right':
                bg_x = config['price_x'] - max_line_width - config['price_padding']
            
            bg_rect = [
                bg_x,
                current_y - config['price_padding'],
                bg_x + max_line_width + config['price_padding'] * 2,
                current_y + total_height + config['price_padding']
            ]
            draw.rounded_rectangle(bg_rect, radius=config['price_radius'], fill=price_bg_color)
        
        # Draw each line
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=price_font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            
            line_x = config['price_x']
            if config['price_align'] == 'center':
                line_x = config['price_x'] - line_w // 2
            elif config['price_align'] == 'right':
                line_x = config['price_x'] - line_w
            
            # Shadow
            if config['price_shadow']:
                draw.text((line_x + 2, current_y + 2), line, font=price_font, fill='black')
            
            # Main text
            draw.text((line_x, current_y), line, font=price_font, fill=price_color)
            
            current_y += int(line_h * config['price_line_height'])
    
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

# UI
st.title("📦 Bulk Ad Generator")
st.markdown("Upload CSV with product data and generate ads for social media")

# Step 1: Canvas Size Selection
st.header("1️⃣ Choose Canvas Size")

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

st.info(f"Canvas size: {st.session_state.canvas_size[0]}×{st.session_state.canvas_size[1]}px")

# Step 2: Upload Base Image
st.header("2️⃣ Upload Base Template Image (Optional)")
base_file = st.file_uploader("Choose base image (PNG, JPG, WEBP) - will be resized to canvas", 
                             type=['png', 'jpg', 'jpeg', 'webp'], key="base")

if base_file:
    st.session_state.base_image = Image.open(base_file).convert('RGBA')
    st.success(f"✅ Base image loaded")
else:
    st.session_state.base_image = None
    st.info("No base image - will use solid color background")

# Step 3: Upload CSV
st.header("3️⃣ Upload Product CSV")
csv_file = st.file_uploader("Choose CSV file", type=['csv'], key="csv")

if csv_file:
    try:
        df = pd.read_csv(csv_file)
        st.session_state.csv_data = df
        st.success(f"✅ Loaded {len(df)} products")
        
        with st.expander("Preview CSV Data"):
            st.dataframe(df.head(10))
            cols = {i: col for i, col in enumerate(df.columns)}
            st.json(cols)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")

# Step 4: Image Source
if st.session_state.csv_data is not None:
    st.header("4️⃣ Image Source")
    
    df = st.session_state.csv_data
    
    use_search = st.checkbox("🔍 Use ImagAPI Image Search (Auto-search by product name)", 
                            value=st.session_state.use_image_search)
    st.session_state.use_image_search = use_search
    
    if use_search:
        st.info("Will search ImagAPI using product names and auto-pick first result")
        
        if st.button("🔎 Test Search (First Product)"):
            with st.spinner("Searching..."):
                first_name = df.iloc[0, st.session_state.name_col]
                result = search_product_image(first_name)
                if result:
                    st.success(f"✅ Found: {result['url'][:60]}...")
                    thumb = load_image_from_url(result['thumbnail'] or result['url'])
                    if thumb:
                        st.image(thumb, width=200, caption="First search result")
                else:
                    st.error("❌ No images found. Try different search term.")

# Step 5: Configure Columns
if st.session_state.csv_data is not None:
    st.header("5️⃣ Configure Column Mapping")
    
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
        st.caption(f"Sample: {str(sample)[:30]}...")
    
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
        if not st.session_state.use_image_search:
            st.session_state.image_col = st.selectbox(
                "Image URL Column",
                range(num_cols),
                format_func=lambda i: f"{i}: {col_names[i]}",
                index=min(st.session_state.image_col, num_cols-1)
            )

# Step 6: Configure Layout
if st.session_state.csv_data is not None:
    st.header("6️⃣ Configure Layout")
    
    cw, ch = st.session_state.canvas_size
    
    # Product Name Settings
    with st.expander("🏷️ Product Name Settings", expanded=True):
        st.session_state.show_product_name = st.checkbox("Show Product Name", 
                                                        st.session_state.show_product_name)
        
        if st.session_state.show_product_name:
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.name_x = st.number_input("Name X", 0, cw, st.session_state.name_x)
                st.session_state.name_y = st.number_input("Name Y", 0, ch, st.session_state.name_y)
                st.session_state.name_size = st.slider("Name Font Size", 10, 100, st.session_state.name_size)
            with col2:
                st.session_state.name_align = st.selectbox("Name Align", ["left", "center", "right"], 
                                                          index=["left", "center", "right"].index(st.session_state.name_align))
                st.session_state.name_weight = st.selectbox("Name Weight", ["normal", "bold"],
                                                           index=["normal", "bold"].index(st.session_state.name_weight))
                st.session_state.name_color = st.color_picker("Name Color", st.session_state.name_color)
            
            st.session_state.name_max_chars = st.slider("Max Characters", 20, 100, st.session_state.name_max_chars)
            
            col3, col4 = st.columns(2)
            with col3:
                st.session_state.name_bg = st.checkbox("Name Background", st.session_state.name_bg)
                st.session_state.name_bg_color = st.color_picker("Name BG Color", st.session_state.name_bg_color)
            with col4:
                st.session_state.name_padding = st.slider("Name Padding", 0, 30, st.session_state.name_padding)
                st.session_state.name_radius = st.slider("Name Radius", 0, 30, st.session_state.name_radius)
                st.session_state.name_shadow = st.checkbox("Name Shadow", st.session_state.name_shadow)
    
    # Product Image Settings
    with st.expander("📐 Product Image Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.product_x = st.number_input("Product X", 0, cw, st.session_state.product_x)
            st.session_state.product_y = st.number_input("Product Y", 0, ch, st.session_state.product_y)
        with col2:
            st.session_state.product_w = st.number_input("Product Width", 10, cw, st.session_state.product_w)
            st.session_state.product_h = st.number_input("Product Height", 10, ch, st.session_state.product_h)
        
        st.session_state.product_radius = st.slider("Product Corner Radius", 0, 100, st.session_state.product_radius)
        
        # Quick position guides
        st.caption("Quick Position:")
        cols = st.columns(5)
        guides = [
            ("↖️ Top Left", 50, 150),
            ("↗️ Top Right", cw - st.session_state.product_w - 50, 150),
            ("⬇️ Bottom Left", 50, ch - st.session_state.product_h - 150),
            ("⬇️ Bottom Right", cw - st.session_state.product_w - 50, ch - st.session_state.product_h - 150),
            ("⭕ Center", cw//2 - st.session_state.product_w//2, ch//2 - st.session_state.product_h//2),
        ]
        
        for i, (label, x, y) in enumerate(guides):
            with cols[i]:
                if st.button(label, key=f"guide_prod_{i}"):
                    st.session_state.product_x = max(0, int(x))
                    st.session_state.product_y = max(0, int(y))
                    st.rerun()
    
    # Price Settings
    with st.expander("💰 Price Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.price_x = st.number_input("Price X", 0, cw, st.session_state.price_x)
            st.session_state.price_y = st.number_input("Price Y", 0, ch, st.session_state.price_y)
            st.session_state.price_size = st.slider("Price Font Size", 10, 150, st.session_state.price_size)
        with col2:
            st.session_state.price_align = st.selectbox("Price Align", ["left", "center", "right"], 
                                                       index=["left", "center", "right"].index(st.session_state.price_align))
            st.session_state.price_weight = st.selectbox("Price Weight", ["normal", "bold"],
                                                        index=["normal", "bold"].index(st.session_state.price_weight))
            st.session_state.price_color = st.color_picker("Price Color", st.session_state.price_color)
        
        col3, col4 = st.columns(2)
        with col3:
            st.session_state.price_bg = st.checkbox("Price Background", st.session_state.price_bg)
            st.session_state.price_bg_color = st.color_picker("Price BG Color", st.session_state.price_bg_color)
        with col4:
            st.session_state.price_padding = st.slider("Price Padding", 0, 50, st.session_state.price_padding)
            st.session_state.price_radius = st.slider("Price Radius", 0, 50, st.session_state.price_radius)
            st.session_state.price_shadow = st.checkbox("Price Shadow", st.session_state.price_shadow)

# Step 7: Generate
if st.session_state.csv_data is not None:
    st.header("7️⃣ Generate Ads")
    
    df = st.session_state.csv_data.copy()
    
    # Preview
    with st.expander("👁️ Preview First Product"):
        if len(df) > 0:
            row = df.iloc[0]
            name = row.iloc[st.session_state.name_col]
            price = row.iloc[st.session_state.price_col]
            
            # Get image
            if st.session_state.use_image_search:
                with st.spinner("Searching image..."):
                    result = search_product_image(name)
                    img_url = result['url'] if result else None
            else:
                img_url = row.iloc[st.session_state.image_col]
            
            st.write(f"**Name:** {name}")
            st.write(f"**Price:** {price}")
            st.write(f"**Image:** {str(img_url)[:50] if img_url else 'None'}...")
            
            product_img = load_image_from_url(img_url)
            
            config = {k: v for k, v in st.session_state.items() if k in [
                'show_product_name', 'name_x', 'name_y', 'name_size', 'name_color',
                'name_align', 'name_weight', 'name_bg', 'name_bg_color', 'name_padding',
                'name_radius', 'name_shadow', 'name_max_chars',
                'product_x', 'product_y', 'product_w', 'product_h', 'product_radius',
                'price_x', 'price_y', 'price_size', 'price_color', 'price_align',
                'price_weight', 'price_bg', 'price_bg_color', 'price_padding',
                'price_radius', 'price_shadow', 'price_line_height'
            ]}
            
            preview = render_single_ad(st.session_state.canvas_size, 
                                      st.session_state.base_image, 
                                      product_img, name, price, config)
            st.image(preview, use_column_width=True)
    
    # Generate all
    if st.button("🚀 Generate All Ads", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated = []
        names = []
        search_urls = []
        
        config = {k: v for k, v in st.session_state.items() if k in [
            'show_product_name', 'name_x', 'name_y', 'name_size', 'name_color',
            'name_align', 'name_weight', 'name_bg', 'name_bg_color', 'name_padding',
            'name_radius', 'name_shadow', 'name_max_chars',
            'product_x', 'product_y', 'product_w', 'product_h', 'product_radius',
            'price_x', 'price_y', 'price_size', 'price_color', 'price_align',
            'price_weight', 'price_bg', 'price_bg_color', 'price_padding',
            'price_radius', 'price_shadow', 'price_line_height'
        ]}
        
        for idx, row in df.iterrows():
            progress = (idx + 1) / len(df)
            progress_bar.progress(min(progress, 0.99))
            
            name = row.iloc[st.session_state.name_col]
            price = row.iloc[st.session_state.price_col]
            
            status_text.text(f"Processing {idx + 1}/{len(df)}: {str(name)[:30]}...")
            
            # Get image
            if st.session_state.use_image_search:
                result = search_product_image(name)
                img_url = result['url'] if result else None
                search_urls.append(img_url if img_url else "")
            else:
                img_url = row.iloc[st.session_state.image_col]
                search_urls.append("")
            
            # Render
            product_img = load_image_from_url(img_url)
            ad = render_single_ad(st.session_state.canvas_size, 
                                 st.session_state.base_image, 
                                 product_img, name, price, config)
            
            generated.append(ad)
            names.append(str(name))
        
        progress_bar.empty()
        status_text.empty()
        
        # Add new column
        if st.session_state.use_image_search:
            df['imagapi_image_url'] = search_urls
        
        st.session_state.generated_ads = generated
        st.session_state.csv_data = df
        
        st.success(f"✅ Generated {len(generated)} ads at {st.session_state.canvas_size[0]}×{st.session_state.canvas_size[1]}px!")
        
        # Downloads
        col1, col2, col3 = st.columns(3)
        
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
                f"products_{st.session_state.canvas_size[0]}x{st.session_state.canvas_size[1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col3:
            with st.expander(f"View All {min(len(generated), 10)} Ads"):
                for i, (img, name) in enumerate(zip(generated[:10], names[:10])):
                    st.image(img, caption=f"{i+1}. {name[:40]}", use_column_width=True)
