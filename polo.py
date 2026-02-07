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

# API Configuration
IMAGAPI_BASE = "https://imagapi.vercel.app/api/v1"

# Session state initialization
defaults = {
    'base_image': None,
    'csv_data': None,
    'generated_ads': [],
    'name_col': 2,
    'price_col': 3,
    'image_col': 4,
    'product_x': 100,
    'product_y': 100,
    'product_w': 300,
    'product_h': 300,
    'product_radius': 0,
    'price_x': 500,
    'price_y': 100,
    'price_size': 48,
    'price_color': '#FFFFFF',
    'price_align': 'left',
    'price_weight': 'bold',
    'price_bg': True,
    'price_bg_color': '#000000',
    'price_padding': 10,
    'price_radius': 8,
    'price_shadow': True,
    'price_line_height': 1.2,
    'use_image_search': False,
    'image_search_col': None,  # Will store new column name
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def search_product_image(query):
    """Search for product image using ImagAPI"""
    if not query or pd.isna(query):
        return None
    
    try:
        url = f"{IMAGAPI_BASE}/assets/search"
        params = {
            "asset_type": "product_images",
            "q": str(query)[:100]  # Limit query length
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        images = data.get("images", [])
        if images and len(images) > 0:
            # Auto-pick first image
            first_image = images[0]
            return {
                'url': first_image.get('url'),
                'thumbnail': first_image.get('thumbnail'),
                'source': first_image.get('source', 'unknown')
            }
        return None
    except Exception as e:
        st.warning(f"Image search failed for '{query[:30]}...': {str(e)[:100]}")
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
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')
    except Exception as e:
        return None

def render_single_ad(base_image, product_image, product_name, price, config):
    """Render a single ad with given parameters"""
    canvas = base_image.copy().convert('RGBA')
    
    # Paste product image
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
        px = max(0, min(config['product_x'], canvas.width - pw))
        py = max(0, min(config['product_y'], canvas.height - ph))
        
        canvas.paste(img, (px, py), img)
    
    # Draw price text
    if price:
        draw = ImageDraw.Draw(canvas)
        font = get_font(config['price_size'], config['price_weight'])
        
        # Handle multiline
        price_str = str(price) if price else ""
        lines = price_str.split('\n')
        
        # Calculate dimensions
        total_height = 0
        line_heights = []
        max_width = 0
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            line_heights.append(h)
            total_height += h * config['price_line_height']
            max_width = max(max_width, w)
        
        # Position
        px = config['price_x']
        py = config['price_y']
        
        # Alignment adjustment
        if config['price_align'] == 'center':
            px = px - max_width // 2
        elif config['price_align'] == 'right':
            px = px - max_width
        
        # Background box
        if config['price_bg']:
            padding = config['price_padding']
            bg_color = ImageColor.getrgb(config['price_bg_color'])
            if len(bg_color) == 3:
                bg_color = (*bg_color, 255)
            
            draw.rounded_rectangle(
                [px - padding, py - padding, 
                 px + max_width + padding, py + total_height + padding],
                radius=config['price_radius'],
                fill=bg_color
            )
        
        # Draw text
        current_y = py
        text_color = ImageColor.getrgb(config['price_color'])
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            
            if config['price_align'] == 'center':
                line_x = px + (max_width - line_w) // 2
            elif config['price_align'] == 'right':
                line_x = px + max_width - line_w
            else:
                line_x = px
            
            # Shadow
            if config['price_shadow']:
                draw.text((line_x + 3, current_y + 3), line, font=font, fill='black')
            
            # Main text
            draw.text((line_x, current_y), line, font=font, fill=text_color)
            
            current_y += line_heights[i] * config['price_line_height']
    
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
st.markdown("Upload CSV with product data and generate ads in bulk")

# Step 1: Upload Base Image
st.header("1️⃣ Upload Base Template Image")
base_file = st.file_uploader("Choose base image (PNG, JPG, WEBP)", type=['png', 'jpg', 'jpeg', 'webp'], key="base")

if base_file:
    st.session_state.base_image = Image.open(base_file).convert('RGBA')
    st.success(f"✅ Base image: {st.session_state.base_image.width}×{st.session_state.base_image.height}px")

# Step 2: Upload CSV
st.header("2️⃣ Upload Product CSV")
csv_file = st.file_uploader("Choose CSV file", type=['csv'], key="csv")

if csv_file:
    try:
        df = pd.read_csv(csv_file)
        st.session_state.csv_data = df
        st.success(f"✅ Loaded {len(df)} products")
        
        # Preview
        with st.expander("Preview CSV Data"):
            st.dataframe(df.head(10))
            cols = {i: col for i, col in enumerate(df.columns)}
            st.json(cols)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")

# Step 3: Image Search Option
if st.session_state.csv_data is not None:
    st.header("3️⃣ Image Source")
    
    df = st.session_state.csv_data
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        use_search = st.checkbox("🔍 Use ImagAPI Image Search", 
                                value=st.session_state.use_image_search,
                                help="Search for product images using product names")
        st.session_state.use_image_search = use_search
    
    with col2:
        if use_search:
            st.info("ImagAPI will search using product names and auto-pick the first image result")
            
            # Show search preview
            if st.button("🔎 Test Search (First Product)"):
                with st.spinner("Searching..."):
                    first_name = df.iloc[0, st.session_state.name_col]
                    result = search_product_image(first_name)
                    if result:
                        st.success(f"Found: {result['url'][:60]}...")
                        # Show thumbnail
                        thumb = load_image_from_url(result['thumbnail'] or result['url'])
                        if thumb:
                            st.image(thumb, width=200)
                    else:
                        st.error("No images found")

# Step 4: Configure Columns
if st.session_state.csv_data is not None:
    st.header("4️⃣ Configure Column Mapping")
    
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
        sample_name = df.iloc[0, st.session_state.name_col] if len(df) > 0 else "N/A"
        st.caption(f"Sample: {str(sample_name)[:30]}...")
    
    with col2:
        st.session_state.price_col = st.selectbox(
            "Price Column",
            range(num_cols),
            format_func=lambda i: f"{i}: {col_names[i]}",
            index=min(st.session_state.price_col, num_cols-1)
        )
        sample_price = df.iloc[0, st.session_state.price_col] if len(df) > 0 else "N/A"
        st.caption(f"Sample: {str(sample_price)[:30]}...")
    
    with col3:
        if st.session_state.use_image_search:
            st.info("📸 Image will come from ImagAPI search")
            st.caption("New column 'imagapi_image_url' will be added to CSV")
        else:
            st.session_state.image_col = st.selectbox(
                "Image URL Column",
                range(num_cols),
                format_func=lambda i: f"{i}: {col_names[i]}",
                index=min(st.session_state.image_col, num_cols-1)
            )
            sample_img = df.iloc[0, st.session_state.image_col] if len(df) > 0 else "N/A"
            st.caption(f"Sample: {str(sample_img)[:50]}...")

# Step 5: Configure Layout
if st.session_state.base_image is not None:
    st.header("5️⃣ Configure Layout")
    
    max_w = st.session_state.base_image.width
    max_h = st.session_state.base_image.height
    
    tab1, tab2 = st.tabs(["📐 Product Image", "💰 Price Text"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.product_x = st.number_input("Product X", 0, max_w, st.session_state.product_x)
            st.session_state.product_y = st.number_input("Product Y", 0, max_h, st.session_state.product_y)
        with col2:
            st.session_state.product_w = st.number_input("Product Width", 10, max_w, st.session_state.product_w)
            st.session_state.product_h = st.number_input("Product Height", 10, max_h, st.session_state.product_h)
        
        st.session_state.product_radius = st.slider("Corner Radius", 0, 100, st.session_state.product_radius)
        
        # Quick position guides
        st.caption("Quick Position:")
        cols = st.columns(5)
        guides = [
            ("↖️ Top Left", 50, 50),
            ("↗️ Top Right", max_w - st.session_state.product_w - 50, 50),
            ("⬇️ Bottom Left", 50, max_h - st.session_state.product_h - 50),
            ("⬇️ Bottom Right", max_w - st.session_state.product_w - 50, max_h - st.session_state.product_h - 50),
            ("⭕ Center", max_w//2 - st.session_state.product_w//2, max_h//2 - st.session_state.product_h//2),
        ]
        
        for i, (label, x, y) in enumerate(guides):
            with cols[i]:
                if st.button(label, key=f"guide_{i}"):
                    st.session_state.product_x = max(0, int(x))
                    st.session_state.product_y = max(0, int(y))
                    st.rerun()
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.price_x = st.number_input("Price X", 0, max_w, st.session_state.price_x)
            st.session_state.price_y = st.number_input("Price Y", 0, max_h, st.session_state.price_y)
            st.session_state.price_size = st.slider("Font Size", 10, 200, st.session_state.price_size)
            st.session_state.price_color = st.color_picker("Text Color", st.session_state.price_color)
        
        with col2:
            st.session_state.price_align = st.selectbox("Alignment", ["left", "center", "right"], 
                                                       index=["left", "center", "right"].index(st.session_state.price_align))
            st.session_state.price_weight = st.selectbox("Font Weight", ["normal", "bold"],
                                                        index=["normal", "bold"].index(st.session_state.price_weight))
            st.session_state.price_line_height = st.slider("Line Height", 0.5, 2.0, st.session_state.price_line_height)
        
        with st.expander("Background Options"):
            st.session_state.price_bg = st.checkbox("Enable Background", st.session_state.price_bg)
            st.session_state.price_bg_color = st.color_picker("BG Color", st.session_state.price_bg_color)
            st.session_state.price_padding = st.slider("Padding", 0, 50, st.session_state.price_padding)
            st.session_state.price_radius = st.slider("BG Radius", 0, 50, st.session_state.price_radius)
            st.session_state.price_shadow = st.checkbox("Text Shadow", st.session_state.price_shadow)

# Step 6: Generate
if st.session_state.base_image is not None and st.session_state.csv_data is not None:
    st.header("6️⃣ Generate Ads")
    
    df = st.session_state.csv_data.copy()
    
    # Preview single ad first
    with st.expander("Preview First Product"):
        if len(df) > 0:
            row = df.iloc[0]
            name = row.iloc[st.session_state.name_col]
            price = row.iloc[st.session_state.price_col]
            
            # Get image
            if st.session_state.use_image_search:
                with st.spinner("Searching image..."):
                    search_result = search_product_image(name)
                    img_url = search_result['url'] if search_result else None
                    if search_result:
                        st.success(f"Found image: {img_url[:50]}...")
            else:
                img_url = row.iloc[st.session_state.image_col]
            
            st.write(f"**Name:** {name}")
            st.write(f"**Price:** {price}")
            st.write(f"**Image:** {str(img_url)[:60]}..." if img_url else "**Image:** None")
            
            product_img = load_image_from_url(img_url)
            
            config = {
                'product_x': st.session_state.product_x,
                'product_y': st.session_state.product_y,
                'product_w': st.session_state.product_w,
                'product_h': st.session_state.product_h,
                'product_radius': st.session_state.product_radius,
                'price_x': st.session_state.price_x,
                'price_y': st.session_state.price_y,
                'price_size': st.session_state.price_size,
                'price_color': st.session_state.price_color,
                'price_align': st.session_state.price_align,
                'price_weight': st.session_state.price_weight,
                'price_bg': st.session_state.price_bg,
                'price_bg_color': st.session_state.price_bg_color,
                'price_padding': st.session_state.price_padding,
                'price_radius': st.session_state.price_radius,
                'price_shadow': st.session_state.price_shadow,
                'price_line_height': st.session_state.price_line_height,
            }
            
            preview = render_single_ad(st.session_state.base_image, product_img, name, price, config)
            st.image(preview, use_column_width=True)
    
    # Generate all
    if st.button("🚀 Generate All Ads", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated = []
        names = []
        search_urls = []  # Store ImagAPI URLs
        
        config = {
            'product_x': st.session_state.product_x,
            'product_y': st.session_state.product_y,
            'product_w': st.session_state.product_w,
            'product_h': st.session_state.product_h,
            'product_radius': st.session_state.product_radius,
            'price_x': st.session_state.price_x,
            'price_y': st.session_state.price_y,
            'price_size': st.session_state.price_size,
            'price_color': st.session_state.price_color,
            'price_align': st.session_state.price_align,
            'price_weight': st.session_state.price_weight,
            'price_bg': st.session_state.price_bg,
            'price_bg_color': st.session_state.price_bg_color,
            'price_padding': st.session_state.price_padding,
            'price_radius': st.session_state.price_radius,
            'price_shadow': st.session_state.price_shadow,
            'price_line_height': st.session_state.price_line_height,
        }
        
        for idx, row in df.iterrows():
            progress = (idx + 1) / len(df)
            progress_bar.progress(min(progress, 0.99))
            
            name = row.iloc[st.session_state.name_col]
            price = row.iloc[st.session_state.price_col]
            
            status_text.text(f"Processing {idx + 1}/{len(df)}: {str(name)[:30]}...")
            
            # Get image URL
            if st.session_state.use_image_search:
                search_result = search_product_image(name)
                img_url = search_result['url'] if search_result else None
                search_urls.append(img_url if img_url else "")
            else:
                img_url = row.iloc[st.session_state.image_col]
                search_urls.append("")  # Empty for non-search mode
            
            # Load and render
            product_img = load_image_from_url(img_url)
            ad = render_single_ad(st.session_state.base_image, product_img, name, price, config)
            
            generated.append(ad)
            names.append(str(name))
        
        progress_bar.empty()
        status_text.empty()
        
        # Add new column to dataframe
        if st.session_state.use_image_search:
            df['imagapi_image_url'] = search_urls
            st.session_state.image_search_col = 'imagapi_image_url'
        
        st.session_state.generated_ads = generated
        st.session_state.csv_data = df  # Update with new column
        
        st.success(f"✅ Generated {len(generated)} ads!")
        
        # Download options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            zip_data = create_zip_download(generated, names)
            st.download_button(
                "📦 Download All Images (ZIP)",
                zip_data,
                f"ads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                "application/zip",
                use_container_width=True
            )
        
        with col2:
            csv_data = get_csv_download_link(df)
            col_name = 'imagapi_image_url' if st.session_state.use_image_search else 'updated'
            st.download_button(
                f"📄 Download Updated CSV ({col_name})",
                csv_data,
                f"products_updated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col3:
            # Show gallery
            with st.expander(f"View All {len(generated)} Ads"):
                for i, (img, name) in enumerate(zip(generated[:10], names[:10])):
                    st.image(img, caption=f"{i+1}. {name[:50]}", use_column_width=True)
