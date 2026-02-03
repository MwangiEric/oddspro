# polotno_full_element_editor.py
import streamlit as st
import json
import requests
import base64
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
from io import BytesIO
import math
import os
from datetime import datetime

# Optional: real SVG rendering
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

st.set_page_config(page_title="Polotno to PIL Converter", layout="wide")

# ───────────────────────────────────────────────
# Session State
# ───────────────────────────────────────────────
defaults = {
    'original_json': None,
    'working_json': None,
    'rendered_image': None,
    'product_name': "TRIPPLE K",
    'product_image_url': "",
    'price': "99,999",
    'background_url': "",
    'transparent_bg': False,
    'font_cache': {}
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ───────────────────────────────────────────────
# Robust Dimension Parsing
# ───────────────────────────────────────────────

def parse_dimension(val, default=0):
    """
    Safely parse dimension values that could be:
    - Numbers (int/float)
    - Strings ("auto", "100%", "1080")
    - None
    """
    if val is None:
        return default
    
    # Handle strings
    if isinstance(val, str):
        val = val.strip().lower()
        if val in ('auto', '', 'none', 'null', 'undefined'):
            return default
        # Remove percentage or px suffix
        val = val.replace('%', '').replace('px', '').strip()
        try:
            return float(val)
        except ValueError:
            return default
    
    # Handle numbers
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def safe_int(val, default=0):
    """Convert to int with safety checks"""
    dim = parse_dimension(val, default)
    # Ensure non-negative
    return max(0, int(dim))

def safe_float(val, default=0.0):
    """Convert to float with safety checks"""
    dim = parse_dimension(val, default)
    return float(dim)

# ───────────────────────────────────────────────
# Image & SVG Loading
# ───────────────────────────────────────────────

def load_image(src, target_w=None, target_h=None, allow_svg=True):
    """Load image from URL, data URI, or SVG with dimension validation"""
    if not src or not isinstance(src, str):
        return None
    
    # Validate target dimensions
    target_w = safe_int(target_w) if target_w else None
    target_h = safe_int(target_h) if target_h else None
    
    try:
        # SVG handling
        if allow_svg and ('svg' in src.lower() or src.startswith('data:image/svg')):
            if not CAIROSVG_AVAILABLE:
                # Return placeholder with valid dimensions
                w = target_w or 200
                h = target_h or 200
                return placeholder_image(w, h, "SVG")
            return render_svg(src, target_w, target_h)

        # Data URI
        if src.startswith('data:image'):
            _, encoded = src.split(',', 1)
            data = base64.b64decode(encoded)
            img = Image.open(BytesIO(data)).convert('RGBA')
            if target_w and target_h:
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

        # URL
        if src.startswith(('http://', 'https://')):
            r = requests.get(src, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            content_type = r.headers.get('content-type', '')
            if 'svg' in content_type or src.endswith('.svg'):
                if CAIROSVG_AVAILABLE:
                    return render_svg(r.content, target_w, target_h)
                return placeholder_image(target_w or 200, target_h or 200, "SVG")
            img = Image.open(BytesIO(r.content)).convert('RGBA')
            if target_w and target_h:
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

    except Exception as e:
        st.warning(f"Load failed: {str(e)[:100]}")
    return None

def render_svg(svg_input, w=None, h=None):
    """Render SVG to PIL Image using cairosvg with dimension validation"""
    if not CAIROSVG_AVAILABLE:
        return None
    
    # Ensure valid dimensions for cairosvg
    w = safe_int(w) if w else None
    h = safe_int(h) if h else None
    
    try:
        if isinstance(svg_input, str):
            if svg_input.startswith('data:image/svg'):
                _, encoded = svg_input.split(',', 1)
                if 'base64' in svg_input:
                    svg_bytes = base64.b64decode(encoded)
                else:
                    svg_bytes = encoded.encode('utf-8')
            else:
                svg_bytes = svg_input.encode('utf-8')
        else:
            svg_bytes = svg_input

        # cairosvg requires positive dimensions if specified
        kwargs = {'bytestring': svg_bytes, 'scale': 2.0}
        if w and w > 0:
            kwargs['output_width'] = w
        if h and h > 0:
            kwargs['output_height'] = h
            
        png = cairosvg.svg2png(**kwargs)
        return Image.open(BytesIO(png)).convert('RGBA')
    except Exception as e:
        st.warning(f"SVG render failed: {str(e)[:100]}")
        return None

def placeholder_image(w, h, text=""):
    """Create placeholder with validated dimensions"""
    w = safe_int(w, 200)
    h = safe_int(h, 200)
    
    # Ensure minimum size
    w = max(w, 10)
    h = max(h, 10)
    
    img = Image.new('RGBA', (w, h), (60, 60, 60, 180))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(10, min(20, w//10)))
    except:
        font = ImageFont.load_default()
    
    # Center text
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((w-tw)//2, (h-th)//2), text, fill=(220,220,220), font=font)
    return img

# ───────────────────────────────────────────────
# Font Loading System
# ───────────────────────────────────────────────

def get_font(font_family, font_size, font_style='normal', font_weight='normal'):
    """Load font with fallback chain"""
    font_size = safe_int(font_size, 24)
    cache_key = f"{font_family}_{font_size}_{font_style}_{font_weight}"
    
    if cache_key in st.session_state.font_cache:
        return st.session_state.font_cache[cache_key]
    
    font = None
    font_paths = []
    
    # Bold variant
    if 'bold' in str(font_weight).lower() or str(font_weight) == '700':
        font_paths.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        ])
    else:
        font_paths.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ])
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except:
                continue
    
    if font is None:
        font = ImageFont.load_default()
    
    st.session_state.font_cache[cache_key] = font
    return font

# ───────────────────────────────────────────────
# Shape Drawing Helpers
# ───────────────────────────────────────────────

def draw_star(draw, cx, cy, outer_r, inner_r, points, fill, stroke=None, stroke_width=1, rotation=0):
    """Draw a star shape"""
    outer_r = safe_float(outer_r)
    inner_r = safe_float(inner_r)
    points = safe_int(points, 5)
    
    coords = []
    for i in range(points * 2):
        angle = math.pi / 2 + (i * math.pi / points) + math.radians(rotation)
        r = outer_r if i % 2 == 0 else inner_r
        x = cx + r * math.cos(angle)
        y = cy - r * math.sin(angle)
        coords.append((x, y))
    draw.polygon(coords, fill=fill, outline=stroke)

def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    """Draw rectangle with rounded corners"""
    x1, y1, x2, y2 = [safe_float(v) for v in xy]
    r = min(safe_float(radius), (x2-x1)/2, (y2-y1)/2)
    
    if r <= 0:
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)
        return
    
    # Draw main rectangle
    draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)
    draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)
    
    # Draw four corners
    draw.pieslice([x1, y1, x1+2*r, y1+2*r], 180, 270, fill=fill)
    draw.pieslice([x2-2*r, y1, x2, y1+2*r], 270, 360, fill=fill)
    draw.pieslice([x1, y2-2*r, x1+2*r, y2], 90, 180, fill=fill)
    draw.pieslice([x2-2*r, y2-2*r, x2, y2], 0, 90, fill=fill)
    
    if outline:
        draw.arc([x1, y1, x1+2*r, y1+2*r], 180, 270, fill=outline, width=width)
        draw.arc([x2-2*r, y1, x2, y1+2*r], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2-2*r, x1+2*r, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2-2*r, y2-2*r, x2, y2], 0, 90, fill=outline, width=width)
        draw.line([x1+r, y1, x2-r, y1], fill=outline, width=width)
        draw.line([x1+r, y2, x2-r, y2], fill=outline, width=width)
        draw.line([x1, y1+r, x1, y2-r], fill=outline, width=width)
        draw.line([x2, y1+r, x2, y2-r], fill=outline, width=width)

# ───────────────────────────────────────────────
# Color Parsing
# ───────────────────────────────────────────────

def parse_color(color_val, default='#000000'):
    """Parse color from various formats"""
    if not color_val:
        return default
    
    if isinstance(color_val, str):
        return color_val
    
    if isinstance(color_val, dict):
        # Handle gradient - return first color
        if color_val.get('type') == 'linear' or color_val.get('colors'):
            colors = color_val.get('colors', [])
            if colors:
                return colors[0].get('color', default)
        return color_val.get('color', default)
    
    return default

def get_rgb(color_str, default=(0, 0, 0)):
    """Convert color string to RGB tuple"""
    if not color_str:
        return default
    
    try:
        # Handle rgba
        if 'rgba' in color_str:
            import re
            nums = re.findall(r'[\d\.]+', color_str)
            if len(nums) >= 3:
                r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
                return (r, g, b)
        
        return ImageColor.getrgb(color_str)
    except:
        return default

# ───────────────────────────────────────────────
# Core Rendering Engine
# ───────────────────────────────────────────────

def apply_opacity(img, opacity):
    """Apply opacity to image"""
    opacity = safe_float(opacity, 1.0)
    if opacity >= 1.0:
        return img
    
    # Ensure image has alpha channel
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    alpha = img.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    img.putalpha(alpha)
    return img

def rotate_around_center(img, angle):
    """Rotate image around its center"""
    angle = safe_float(angle)
    if angle == 0:
        return img
    
    # Ensure valid image
    if img.width <= 0 or img.height <= 0:
        return img
        
    return img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)

def render_text_element(draw, el, overrides, canvas_w, canvas_h):
    """Render text element with full styling"""
    text = el.get('text', '')
    if not text:
        return
    
    # Apply overrides based on content detection
    is_price = any(marker in text for marker in ['KES', 'ksh', '$', '€', '£']) or \
               (any(c.isdigit() for c in text) and len(text) < 20)
    is_product_name = len(text) > 3 and not is_price and safe_int(el.get('fontSize'), 0) > 30
    
    if is_product_name and overrides.get('product_name'):
        text = overrides['product_name']
    elif is_price and overrides.get('price'):
        text = overrides['price']
    
    # Get styling
    font_size = safe_int(el.get('fontSize'), 24)
    font_family = el.get('fontFamily', 'Arial')
    font_style = el.get('fontStyle', 'normal')
    font_weight = el.get('fontWeight', 'normal')
    fill = get_rgb(parse_color(el.get('fill'), '#ffffff'))
    
    # Position with validation
    x = safe_float(el.get('x'))
    y = safe_float(el.get('y'))
    w = safe_float(el.get('width'))
    h = safe_float(el.get('height'))
    
    # Skip if dimensions are invalid
    if w <= 0 or h <= 0:
        return
    
    rotation = safe_float(el.get('rotation'))
    opacity = safe_float(el.get('opacity'), 1.0)
    
    # Load font
    font = get_font(font_family, font_size, font_style, font_weight)
    
    # Calculate text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Alignment
    align = el.get('align', 'left')
    if align == 'center':
        x += (w - text_w) / 2
    elif align == 'right':
        x += w - text_w
    
    vertical_align = el.get('verticalAlign', 'top')
    if vertical_align == 'middle':
        y += (h - text_h) / 2
    elif vertical_align == 'bottom':
        y += h - text_h
    
    # Handle shadow
    shadow = el.get('shadow')
    if shadow and shadow.get('enabled', False):
        sx = x + safe_float(shadow.get('x', 2))
        sy = y + safe_float(shadow.get('y', 2))
        shadow_color = get_rgb(shadow.get('color', 'rgba(0,0,0,0.5)'))
        draw.text((sx, sy), text, fill=shadow_color, font=font)
    
    # Draw text
    draw.text((x, y), text, fill=fill, font=font)

def render_image_element(canvas, el, overrides):
    """Render image/svg element"""
    src = el.get('src', '')
    if not src:
        return canvas
    
    # Validate all dimensions
    x = safe_float(el.get('x'))
    y = safe_float(el.get('y'))
    w = safe_float(el.get('width'))
    h = safe_float(el.get('height'))
    
    # Skip invalid dimensions
    if w <= 0 or h <= 0:
        return canvas
    
    rotation = safe_float(el.get('rotation'))
    opacity = safe_float(el.get('opacity'), 1.0)
    flip_x = el.get('flipX', False)
    flip_y = el.get('flipY', False)
    
    # Check if this is the main product image
    is_main_product = w > 200 and h > 200
    
    # Apply override if this is the product image slot and override provided
    if is_main_product and overrides.get('product_image'):
        src = overrides['product_image']
    
    # Load image
    img = load_image(src, int(w), int(h))
    if not img:
        return canvas
    
    # Apply transforms
    if flip_x:
        img = img.transpose(Image.Flip.LEFT_RIGHT)
    if flip_y:
        img = img.transpose(Image.Flip.TOP_BOTTOM)
    
    if rotation != 0:
        img = rotate_around_center(img, rotation)
        # Center the rotated image
        new_x = x + (w - img.width) / 2
        new_y = y + (h - img.height) / 2
    else:
        new_x, new_y = x, y
    
    if opacity < 1.0:
        img = apply_opacity(img, opacity)
    
    # Clip to canvas bounds
    paste_x = max(0, int(new_x))
    paste_y = max(0, int(new_y))
    
    # Crop if extending beyond canvas
    crop_left = max(0, -int(new_x))
    crop_top = max(0, -int(new_y))
    crop_right = min(img.width, canvas.width - paste_x + crop_left)
    crop_bottom = min(img.height, canvas.height - paste_y + crop_top)
    
    if crop_left > 0 or crop_top > 0 or crop_right < img.width or crop_bottom < img.height:
        if crop_right > crop_left and crop_bottom > crop_top:
            img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
    
    # Final validation before paste
    if img.width > 0 and img.height > 0 and paste_x < canvas.width and paste_y < canvas.height:
        try:
            canvas.paste(img, (paste_x, paste_y), img)
        except:
            pass
    
    return canvas

def render_shape_element(draw, el):
    """Render shape/figure element"""
    # Validate dimensions
    x = safe_float(el.get('x'))
    y = safe_float(el.get('y'))
    w = safe_float(el.get('width'))
    h = safe_float(el.get('height'))
    
    if w <= 0 or h <= 0:
        return
    
    rotation = safe_float(el.get('rotation'))
    
    subtype = (el.get('subType') or el.get('subtype', 'rect')).lower()
    fill = get_rgb(parse_color(el.get('fill'), '#888888'))
    stroke = get_rgb(parse_color(el.get('stroke')))
    stroke_width = safe_int(el.get('strokeWidth'), 0)
    corner_radius = safe_float(el.get('cornerRadius'), 0)
    
    # Draw based on type
    if subtype in ('rect', 'rectangle'):
        if corner_radius > 0:
            draw_rounded_rect(draw, [x, y, x+w, y+h], corner_radius, fill, stroke, stroke_width)
        else:
            draw.rectangle([x, y, x+w, y+h], fill=fill, outline=stroke, width=stroke_width)
    
    elif subtype in ('circle', 'ellipse'):
        draw.ellipse([x, y, x+w, y+h], fill=fill, outline=stroke, width=stroke_width)
    
    elif subtype == 'star':
        points = safe_int(el.get('points'), 5)
        outer_r = min(w, h) / 2
        inner_r = outer_r * 0.4
        cx, cy = x + w/2, y + h/2
        draw_star(draw, cx, cy, outer_r, inner_r, points, fill, stroke, stroke_width, rotation)
    
    elif subtype in ('triangle', 'topTriangle'):
        points = [(x+w/2, y), (x+w, y+h), (x, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
    
    elif subtype == 'line':
        x1, y1 = x, y
        x2, y2 = x + w, y + h
        draw.line([(x1, y1), (x2, y2)], fill=stroke or fill, width=max(1, stroke_width))

def render_polotno(pjson: dict, overrides: dict) -> Image.Image:
    """
    Main render function - converts Polotno JSON to PIL Image
    """
    pages = pjson.get('pages', [])
    if not pages:
        return Image.new('RGBA', (800, 600), (255, 255, 255, 255))
    
    page = pages[0]
    
    # Parse page dimensions with validation
    w = safe_int(page.get('width'), 1080)
    h = safe_int(page.get('height'), 1080)
    
    # Ensure minimum canvas size
    w = max(w, 100)
    h = max(h, 100)
    
    # Create canvas
    bg_url = overrides.get('background_url', '')
    transparent = overrides.get('transparent_bg', False)
    
    # Try to load background image first
    if bg_url:
        bg = load_image(bg_url, w, h)
        if bg:
            canvas = bg.convert('RGBA')
        else:
            canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    else:
        # Check for background in JSON
        bg_color = page.get('background', '#ffffff')
        if isinstance(bg_color, str) and bg_color.startswith('http'):
            bg = load_image(bg_color, w, h)
            if bg:
                canvas = bg.convert('RGBA')
            else:
                canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
        else:
            if transparent:
                canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            else:
                try:
                    rgb = get_rgb(bg_color, (255, 255, 255))
                    canvas = Image.new('RGBA', (w, h), (*rgb, 255))
                except:
                    canvas = Image.new('RGBA', (w, h), (255, 255, 255, 255))
    
    # Sort children by z-index
    children = page.get('children', [])
    children.sort(key=lambda x: safe_int(x.get('z'), 0))
    
    # Process each element
    for el in children:
        try:
            el_type = el.get('type', '').lower()
            
            if el_type == 'text':
                draw = ImageDraw.Draw(canvas)
                render_text_element(draw, el, overrides, w, h)
            
            elif el_type in ('image', 'svg'):
                canvas = render_image_element(canvas, el, overrides)
            
            elif el_type in ('figure', 'shape', 'rect', 'circle'):
                draw = ImageDraw.Draw(canvas)
                render_shape_element(draw, el)
            
            elif el_type == 'group':
                # Handle groups
                group_x = safe_float(el.get('x'))
                group_y = safe_float(el.get('y'))
                for child in el.get('children', []):
                    child_copy = child.copy()
                    child_copy['x'] = safe_float(child.get('x', 0)) + group_x
                    child_copy['y'] = safe_float(child.get('y', 0)) + group_y
                    
                    child_type = child_copy.get('type', '').lower()
                    if child_type == 'text':
                        draw = ImageDraw.Draw(canvas)
                        render_text_element(draw, child_copy, overrides, w, h)
                    elif child_type in ('image', 'svg'):
                        canvas = render_image_element(canvas, child_copy, overrides)
                    elif child_type in ('figure', 'shape'):
                        draw = ImageDraw.Draw(canvas)
                        render_shape_element(draw, child_copy)
        
        except Exception as e:
            # Silently skip problematic elements
            continue
    
    return canvas

# ───────────────────────────────────────────────
# UI Components
# ───────────────────────────────────────────────

st.title("🎨 Polotno to PIL Converter")
st.markdown("Convert Polotno JSON designs to high-quality images")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.transparent_bg = st.checkbox(
        "Transparent Background", 
        value=st.session_state.transparent_bg
    )

# Main layout
col_load, col_edit = st.columns([1, 1])

with col_load:
    st.subheader("📁 Load Design")
    
    uploaded = st.file_uploader("Upload Polotno .json", type=["json"])
    raw_json = st.text_area("Or paste JSON", height=200)
    
    if st.button("🚀 Load", type="primary", use_container_width=True):
        content = None
        if uploaded:
            content = uploaded.read().decode('utf-8')
        elif raw_json.strip():
            content = raw_json.strip()
        
        if content:
            try:
                data = json.loads(content)
                st.session_state.original_json = data
                st.session_state.working_json = json.loads(json.dumps(data))
                
                # Extract page dimensions for display
                pages = data.get('pages', [])
                if pages:
                    page = pages[0]
                    w = safe_int(page.get('width'), 0)
                    h = safe_int(page.get('height'), 0)
                    st.success(f"✅ Loaded {len(pages)} page(s) • {w}×{h}px")
                else:
                    st.success("✅ Loaded!")
            except Exception as e:
                st.error(f"❌ Error: {e}")

with col_edit:
    st.subheader("✏️ Customize")
    
    if st.session_state.original_json:
        st.session_state.product_name = st.text_input(
            "Product Name", 
            value=st.session_state.product_name
        )
        st.session_state.price = st.text_input(
            "Price", 
            value=st.session_state.price
        )
        st.session_state.product_image_url = st.text_input(
            "Product Image URL (optional)",
            value=st.session_state.product_image_url,
            placeholder="Leave empty to use template"
        )
    else:
        st.info("Load a design first")

# Render section
st.markdown("---")

if st.session_state.original_json:
    col_render, col_preview = st.columns([1, 2])
    
    with col_render:
        st.subheader("🎬 Render")
        
        if st.button("✨ Render", type="primary", use_container_width=True):
            overrides = {
                'product_name': st.session_state.product_name,
                'price': st.session_state.price,
                'product_image': st.session_state.product_image_url,
                'background_url': st.session_state.background_url,
                'transparent_bg': st.session_state.transparent_bg
            }
            
            with st.spinner("Rendering..."):
                try:
                    img = render_polotno(st.session_state.original_json, overrides)
                    st.session_state.rendered_image = img
                    st.success(f"✅ {img.width}×{img.height}px")
                except Exception as e:
                    st.error(f"❌ Render failed: {e}")
                    st.exception(e)
    
    with col_preview:
        if st.session_state.rendered_image:
            st.subheader("👁️ Preview")
            st.image(st.session_state.rendered_image, use_column_width=True)
            
            # Downloads
            col1, col2, col3 = st.columns(3)
            
            with col1:
                buf = BytesIO()
                st.session_state.rendered_image.save(buf, format="PNG")
                st.download_button(
                    "💾 PNG",
                    buf.getvalue(),
                    f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    "image/png",
                    use_container_width=True
                )
            
            with col2:
                buf = BytesIO()
                rgb_img = st.session_state.rendered_image.convert('RGB')
                rgb_img.save(buf, format="JPEG", quality=95)
                st.download_button(
                    "💾 JPG",
                    buf.getvalue(),
                    f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                    "image/jpeg",
                    use_container_width=True
                )
            
            with col3:
                buf = BytesIO()
                st.session_state.rendered_image.save(buf, format="WEBP", quality=95)
                st.download_button(
                    "💾 WebP",
                    buf.getvalue(),
                    f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp",
                    "image/webp",
                    use_container_width=True
                )
else:
    st.info("📂 Load a Polotno JSON file to start")
