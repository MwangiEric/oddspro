# polotno_full_element_editor.py
import streamlit as st
import json
import requests
import base64
import re
import math
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter
from io import BytesIO
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
    'product_name': "SAMSUNG S25",
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
    """Safely parse dimension values"""
    if val is None:
        return default
    if isinstance(val, str):
        val = val.strip().lower()
        if val in ('auto', '', 'none', 'null', 'undefined'):
            return default
        val = val.replace('%', '').replace('px', '').strip()
        try:
            return float(val)
        except ValueError:
            return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def safe_int(val, default=0):
    """Convert to int with safety checks"""
    dim = parse_dimension(val, default)
    return max(0, int(dim))

def safe_float(val, default=0.0):
    """Convert to float with safety checks"""
    dim = parse_dimension(val, default)
    return float(dim)

# ───────────────────────────────────────────────
# Color Handling
# ───────────────────────────────────────────────

def parse_color(color_str, default=(0, 0, 0, 255)):
    """Parse color to RGBA tuple"""
    if not color_str or color_str == 'transparent':
        return (0, 0, 0, 0)
    try:
        # Handle rgba(r,g,b,a) format
        if isinstance(color_str, str) and 'rgba' in color_str:
            nums = re.findall(r"[\d.]+", color_str)
            if len(nums) >= 3:
                r = int(float(nums[0]))
                g = int(float(nums[1]))
                b = int(float(nums[2]))
                a = int(float(nums[3]) * 255) if len(nums) >= 4 else 255
                return (r, g, b, a)
        # Handle rgb(r,g,b) format
        elif isinstance(color_str, str) and color_str.startswith('rgb('):
            nums = re.findall(r"[\d.]+", color_str)
            if len(nums) >= 3:
                return (int(float(nums[0])), int(float(nums[1])), int(float(nums[2])), 255)
        
        # Try PIL ImageColor
        result = ImageColor.getrgb(color_str)
        if len(result) == 3:
            return (result[0], result[1], result[2], 255)
        return result
    except:
        pass
    
    # Fallback regex
    numbers = re.findall(r"[\d.]+", str(color_str))
    if len(numbers) >= 3:
        r = int(float(numbers[0]))
        g = int(float(numbers[1]))
        b = int(float(numbers[2]))
        a = int(float(numbers[3]) * 255) if len(numbers) >= 4 else 255
        return (r, g, b, a)
    
    return default

def get_rgb(color_str, default=(0, 0, 0)):
    """Convert color string to RGB tuple (for backward compatibility)"""
    rgba = parse_color(color_str, (*default, 255))
    return rgba[:3]

def replace_svg_colors(svg_content, color_replacements):
    """Replace colors in SVG content based on colorsReplace mapping"""
    if not color_replacements or not svg_content:
        return svg_content
    
    modified_svg = svg_content
    for old_color, new_color in color_replacements.items():
        rgb = parse_color(new_color)
        if len(rgb) == 4:
            r, g, b, a = rgb
            new_color_str = f"rgba({r},{g},{b},{a/255:.2f})"
        else:
            r, g, b = rgb
            new_color_str = f"rgb({r},{g},{b})"
        
        modified_svg = modified_svg.replace(old_color, new_color_str)
        modified_svg = modified_svg.replace(old_color.replace(' ', ''), new_color_str)
    
    return modified_svg

# ───────────────────────────────────────────────
# Image & SVG Loading
# ───────────────────────────────────────────────

def load_image(src, target_w=None, target_h=None, color_replacements=None):
    """Load image from URL, data URI, or SVG with dimension validation"""
    if not src or not isinstance(src, str):
        return None
    
    target_w = safe_int(target_w) if target_w else None
    target_h = safe_int(target_h) if target_h else None
    
    try:
        # SVG handling
        if 'svg' in src.lower() or src.startswith('data:image/svg'):
            return render_svg(src, target_w, target_h, color_replacements)

        # Data URI
        if src.startswith('data:image'):
            if ',' in src:
                _, encoded = src.split(',', 1)
                data = base64.b64decode(encoded)
            else:
                return None
            
            # Check if it's actually an SVG disguised as data URI
            if 'svg' in src.lower():
                svg_data = data.decode('utf-8', errors='ignore')
                return render_svg(svg_data, target_w, target_h, color_replacements)
            
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
                return render_svg(r.content, target_w, target_h, color_replacements)
            
            img = Image.open(BytesIO(r.content)).convert('RGBA')
            if target_w and target_h:
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

    except Exception as e:
        st.warning(f"Load failed: {str(e)[:100]}")
    return None

def render_svg(svg_input, w=None, h=None, color_replacements=None):
    """Render SVG to PIL Image with color replacement support"""
    if not CAIROSVG_AVAILABLE:
        w = safe_int(w, 200)
        h = safe_int(h, 200)
        return placeholder_image(w, h, "SVG")
    
    w = safe_int(w) if w else None
    h = safe_int(h) if h else None
    
    try:
        # Extract SVG content
        if isinstance(svg_input, str):
            if svg_input.startswith('data:image/svg'):
                _, encoded = svg_input.split(',', 1)
                if 'base64' in svg_input:
                    svg_bytes = base64.b64decode(encoded)
                    svg_content = svg_bytes.decode('utf-8', errors='ignore')
                else:
                    svg_content = encoded
            else:
                svg_content = svg_input
        else:
            svg_content = svg_input.decode('utf-8', errors='ignore') if isinstance(svg_input, bytes) else str(svg_input)
        
        # Apply color replacements
        if color_replacements:
            svg_content = replace_svg_colors(svg_content, color_replacements)
        
        # Render with cairosvg
        kwargs = {'bytestring': svg_content.encode('utf-8'), 'scale': 2.0}
        if w and w > 0:
            kwargs['output_width'] = w
        if h and h > 0:
            kwargs['output_height'] = h
            
        png = cairosvg.svg2png(**kwargs)
        return Image.open(BytesIO(png)).convert('RGBA')
    except Exception as e:
        w = safe_int(w, 200)
        h = safe_int(h, 200)
        return placeholder_image(w, h, "SVG Error")

def placeholder_image(w, h, text=""):
    """Create placeholder with validated dimensions"""
    w = max(safe_int(w, 200), 10)
    h = max(safe_int(h, 200), 10)
    
    img = Image.new('RGBA', (w, h), (60, 60, 60, 180))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(10, min(20, w//10)))
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((w-tw)//2, (h-th)//2), text, fill=(220,220,220), font=font)
    return img

# ───────────────────────────────────────────────
# Font Loading System
# ───────────────────────────────────────────────

def get_font(size, family='Poppins', weight='normal', style='normal'):
    """Load font with fallback chain"""
    size = safe_int(size, 32)
    cache_key = f"{family}_{size}_{weight}_{style}"
    
    if cache_key in st.session_state.font_cache:
        return st.session_state.font_cache[cache_key]
    
    font = None
    font_paths = []
    
    # Map weight to font file
    weight_map = {
        'normal': ['poppins_regular.ttf', 'DejaVuSans.ttf', 'Arial.ttf'],
        'regular': ['poppins_regular.ttf', 'DejaVuSans.ttf', 'Arial.ttf'],
        'bold': ['poppins_bold.ttf', 'DejaVuSans-Bold.ttf', 'Arial_Bold.ttf'],
        'semibold': ['poppins_semi_bold.ttf', 'DejaVuSans-Bold.ttf'],
        'semi-bold': ['poppins_semi_bold.ttf', 'DejaVuSans-Bold.ttf'],
        'italic': ['poppins_regular.ttf', 'DejaVuSans.ttf']
    }
    
    font_names = weight_map.get(weight.lower(), weight_map['normal'])
    
    # Check in fonts directory first
    fonts_dir = "assets/fonts"
    for name in font_names:
        path = os.path.join(fonts_dir, name)
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                break
            except:
                pass
    
    # Fallback to system fonts
    if font is None:
        system_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf"
        ]
        for path in system_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except:
                    pass
    
    if font is None:
        font = ImageFont.load_default()
    
    st.session_state.font_cache[cache_key] = font
    return font

# ───────────────────────────────────────────────
# Shape Drawing Helpers (from your template)
# ───────────────────────────────────────────────

def draw_shape(draw, x, y, w, h, subtype, fill, stroke, stroke_w, radius=0):
    """Draw all shape types"""
    
    if subtype in ('rect', 'rectangle'):
        if radius > 0:
            if stroke and stroke[3] > 0:
                draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, 
                                     fill=fill, outline=stroke, width=int(stroke_w))
            else:
                draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=fill)
        else:
            if stroke and stroke[3] > 0:
                draw.rectangle([x, y, x+w, y+h], fill=fill, outline=stroke, width=int(stroke_w))
            else:
                draw.rectangle([x, y, x+w, y+h], fill=fill)
                
    elif subtype in ('circle', 'ellipse'):
        if stroke and stroke[3] > 0:
            draw.ellipse([x, y, x+w, y+h], fill=fill, outline=stroke, width=int(stroke_w))
        else:
            draw.ellipse([x, y, x+w, y+h], fill=fill)
            
    elif subtype == 'rightTriangle':
        points = [(x, y), (x+w, y), (x, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'leftTriangle':
        points = [(x, y), (x+w, y), (x+w, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype in ('topTriangle', 'triangle'):
        points = [(x+w/2, y), (x, y+h), (x+w, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'bottomTriangle':
        points = [(x, y), (x+w, y), (x+w/2, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype in ('diamond', 'rhombus'):
        points = [(x+w/2, y), (x+w, y+h/2), (x+w/2, y+h), (x, y+h/2)]
        draw.polygon(points, fill=fill, outline=stroke)

def draw_star(draw, cx, cy, outer_r, inner_r, num_points, fill, rotation=0):
    """Draw star polygon"""
    points = []
    for i in range(num_points * 2):
        angle = (i * math.pi / num_points) - (math.pi / 2) + math.radians(rotation)
        r = outer_r if i % 2 == 0 else inner_r
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        points.append((px, py))
    draw.polygon(points, fill=fill)

def draw_polygon(draw, cx, cy, w, h, sides, fill, rotation=0):
    """Draw regular polygon"""
    points = []
    radius = min(w, h) / 2
    for i in range(sides):
        angle = (i * 2 * math.pi / sides) - (math.pi / 2) + math.radians(rotation)
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        points.append((px, py))
    draw.polygon(points, fill=fill)

def draw_arrow(draw, x, y, w, h, direction, fill, stroke, stroke_w):
    """Draw arrow shape"""
    if direction == 'right':
        points = [(x, y+h/3), (x+w/2, y+h/3), (x+w/2, y), (x+w, y+h/2), 
                  (x+w/2, y+h), (x+w/2, y+2*h/3), (x, y+2*h/3)]
    elif direction == 'left':
        points = [(x+w, y+h/3), (x+w/2, y+h/3), (x+w/2, y), (x, y+h/2),
                  (x+w/2, y+h), (x+w/2, y+2*h/3), (x+w, y+2*h/3)]
    elif direction == 'up':
        points = [(x+w/3, y+h), (x+w/3, y+h/2), (x, y+h/2), 
                  (x+w/2, y), (x+w, y+h/2), (x+2*w/3, y+h/2), (x+2*w/3, y+h)]
    else:  # down
        points = [(x+w/3, y), (x+w/3, y+h/2), (x, y+h/2),
                  (x+w/2, y+h), (x+w, y+h/2), (x+2*w/3, y+h/2), (x+2*w/3, y)]
    
    draw.polygon(points, fill=fill, outline=stroke)

# ───────────────────────────────────────────────
# Core Rendering Functions
# ───────────────────────────────────────────────

def apply_opacity(img, opacity):
    """Apply opacity to image"""
    opacity = safe_float(opacity, 1.0)
    if opacity >= 1.0:
        return img
    
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
    
    if img.width <= 0 or img.height <= 0:
        return img
        
    return img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)

def render_text_element(draw, el, overrides, canvas_w, canvas_h):
    """Render text element with multiline support"""
    text = el.get('text', '')
    if not text:
        return
    
    # Apply overrides
    is_price = any(marker in text for marker in ['KES', 'ksh', '$', '€', '£', ',']) and any(c.isdigit() for c in text)
    is_product_name = len(text) > 3 and not is_price and safe_int(el.get('fontSize'), 0) > 25
    
    if is_product_name and overrides.get('product_name'):
        text = overrides['product_name']
    elif is_price and overrides.get('price'):
        text = overrides['price']
    
    # Get styling
    font_size = safe_int(el.get('fontSize'), 32)
    font_family = el.get('fontFamily', 'Poppins')
    font_style = el.get('fontStyle', 'normal')
    font_weight = el.get('fontWeight', 'normal')
    color = parse_color(el.get('fill', 'black'))
    color = (color[0], color[1], color[2], int(color[3] * safe_float(el.get('opacity'), 1)))
    
    # Position
    x = safe_float(el.get('x'))
    y = safe_float(el.get('y'))
    w = safe_float(el.get('width'))
    h = safe_float(el.get('height'))
    
    if w <= 0 or h <= 0:
        return
    
    rotation = safe_float(el.get('rotation'))
    line_height = safe_float(el.get('lineHeight'), 1.2)
    letter_spacing = safe_float(el.get('letterSpacing', 0))
    
    # Load font
    font = get_font(font_size, font_family, font_weight, font_style)
    
    # Handle multiline text
    lines = text.split('\n')
    
    # Calculate total height
    total_height = 0
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_height += lh * line_height
    
    # Vertical alignment
    vertical_align = el.get('verticalAlign', 'top')
    current_y = y
    if vertical_align == 'middle':
        current_y = y + (h - total_height) / 2
    elif vertical_align == 'bottom':
        current_y = y + h - total_height
    
    # Draw each line
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0] + (len(line) * letter_spacing)
        text_h = line_heights[i]
        
        # Horizontal alignment
        align = el.get('align', 'left')
        if align == 'center':
            line_x = x + (w - text_w) / 2
        elif align == 'right':
            line_x = x + w - text_w
        else:
            line_x = x
        
        # Shadow
        shadow = el.get('shadow')
        if shadow and shadow.get('enabled', False):
            sx = line_x + safe_float(shadow.get('x', 2))
            sy = current_y + safe_float(shadow.get('y', 2))
            shadow_color = parse_color(shadow.get('color', 'rgba(0,0,0,0.5)'))
            draw.text((sx, sy), line, fill=shadow_color, font=font)
        
        # Apply letter spacing by drawing character by character if needed
        if letter_spacing > 0:
            char_x = line_x
            for char in line:
                draw.text((char_x, current_y), char, fill=color, font=font)
                char_bbox = draw.textbbox((0, 0), char, font=font)
                char_w = char_bbox[2] - char_bbox[0]
                char_x += char_w + letter_spacing
        else:
            draw.text((line_x, current_y), line, fill=color, font=font)
        
        current_y += text_h * line_height

def render_image_element(canvas, el, overrides):
    """Render image/svg element"""
    src = el.get('src', '')
    if not src:
        return canvas
    
    x = safe_float(el.get('x'))
    y = safe_float(el.get('y'))
    w = safe_float(el.get('width'))
    h = safe_float(el.get('height'))
    
    if w <= 0 or h <= 0:
        return canvas
    
    rotation = safe_float(el.get('rotation'))
    opacity = safe_float(el.get('opacity'), 1.0)
    flip_x = el.get('flipX', False)
    flip_y = el.get('flipY', False)
    corner_radius = safe_float(el.get('cornerRadius', 0))
    color_replacements = el.get('colorsReplace')
    
    # Check if this is main product image
    is_main_product = w > 200 and h > 200 and el.get('type') == 'image'
    
    if is_main_product and overrides.get('product_image'):
        src = overrides['product_image']
    
    # Load image
    img = load_image(src, int(w), int(h), color_replacements)
    if not img:
        # Draw placeholder
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([x, y, x+w, y+h], outline='red', width=3)
        return canvas
    
    # Apply flips
    if flip_x:
        img = img.transpose(Image.Flip.LEFT_RIGHT)
    if flip_y:
        img = img.transpose(Image.Flip.TOP_BOTTOM)
    
    # Apply rotation
    if rotation != 0:
        img = rotate_around_center(img, rotation)
        new_x = x + (w - img.width) / 2
        new_y = y + (h - img.height) / 2
    else:
        new_x, new_y = x, y
    
    # Apply opacity
    if opacity < 1.0:
        img = apply_opacity(img, opacity)
    
    # Apply corner radius mask
    if corner_radius > 0:
        mask = Image.new('L', (img.width, img.height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, img.width, img.height], 
                                   radius=corner_radius, fill=255)
        img.putalpha(mask)
    
    # Clip to canvas bounds
    paste_x = max(0, int(new_x))
    paste_y = max(0, int(new_y))
    
    crop_left = max(0, -int(new_x))
    crop_top = max(0, -int(new_y))
    crop_right = min(img.width, canvas.width - paste_x + crop_left)
    crop_bottom = min(img.height, canvas.height - paste_y + crop_top)
    
    if crop_left > 0 or crop_top > 0 or crop_right < img.width or crop_bottom < img.height:
        if crop_right > crop_left and crop_bottom > crop_top:
            img = img.crop((crop_left, crop_top, crop_right, crop_bottom))
    
    if img.width > 0 and img.height > 0 and paste_x < canvas.width and paste_y < canvas.height:
        try:
            canvas.paste(img, (paste_x, paste_y), img)
        except:
            pass
    
    return canvas

def render_shape_element(draw, el):
    """Render shape/figure element"""
    x = safe_float(el.get('x'))
    y = safe_float(el.get('y'))
    w = safe_float(el.get('width'))
    h = safe_float(el.get('height'))
    
    if w <= 0 or h <= 0:
        return
    
    rotation = safe_float(el.get('rotation'))
    opacity = safe_float(el.get('opacity'), 1.0)
    
    subtype = (el.get('subType') or el.get('subtype', 'rect')).lower()
    fill = parse_color(el.get('fill', '#888888'))
    fill = (fill[0], fill[1], fill[2], int(fill[3] * opacity))
    
    stroke_str = el.get('stroke', 'transparent')
    stroke = parse_color(stroke_str) if stroke_str != 'transparent' else None
    if stroke:
        stroke = (stroke[0], stroke[1], stroke[2], int(stroke[3] * opacity))
    
    stroke_width = safe_int(el.get('strokeWidth'), 0)
    corner_radius = safe_float(el.get('cornerRadius'), 0)
    
    # Draw based on type
    if subtype in ('rect', 'rectangle', 'circle', 'rightTriangle', 'leftTriangle', 
                   'topTriangle', 'bottomTriangle', 'triangle', 'diamond', 'rhombus'):
        draw_shape(draw, x, y, w, h, subtype, fill, stroke, stroke_width, corner_radius)
    
    elif subtype == 'star':
        cx, cy = x + w/2, y + h/2
        outer_r = min(w, h) / 2
        inner_r = outer_r * el.get('innerRadius', 0.5)
        draw_star(draw, cx, cy, outer_r, inner_r, 
                 safe_int(el.get('numPoints', 5)), fill, rotation)
    
    elif subtype == 'polygon':
        cx, cy = x + w/2, y + h/2
        draw_polygon(draw, cx, cy, w, h, 
                    safe_int(el.get('sides', 6)), fill, rotation)
    
    elif subtype == 'arrow':
        direction = el.get('direction', 'right')
        draw_arrow(draw, x, y, w, h, direction, fill, stroke, stroke_width)
    
    elif subtype == 'line':
        x1 = x + safe_float(el.get('x1', 0))
        y1 = y + safe_float(el.get('y1', 0))
        x2 = x + safe_float(el.get('x2', w))
        y2 = y + safe_float(el.get('y2', h))
        draw.line([(x1, y1), (x2, y2)], fill=stroke or fill, width=max(1, stroke_width))

# ───────────────────────────────────────────────
# Main Render Function - FIXED ROOT LEVEL DIMENSIONS
# ───────────────────────────────────────────────

def render_polotno(pjson: dict, overrides: dict) -> Image.Image:
    """Main render function - reads canvas dimensions from ROOT level"""
    
    # Get canvas dimensions from ROOT of JSON (not from pages)
    canvas_width = safe_int(pjson.get('width'), 1080)
    canvas_height = safe_int(pjson.get('height'), 1920)
    
    pages = pjson.get('pages', [])
    if not pages:
        return Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 255))
    
    page = pages[0]
    w, h = canvas_width, canvas_height
    
    # Create canvas
    bg_url = overrides.get('background_url', '')
    transparent = overrides.get('transparent_bg', False)
    
    if bg_url:
        bg = load_image(bg_url, w, h)
        if bg:
            canvas = bg.convert('RGBA')
        else:
            canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    else:
        # Check for background in page
        page_bg = page.get('background', 'white')
        if isinstance(page_bg, str) and page_bg.startswith('http'):
            bg = load_image(page_bg, w, h)
            if bg:
                canvas = bg.convert('RGBA')
            else:
                canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
        else:
            if transparent:
                canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            else:
                bg_color = parse_color(page_bg, (255, 255, 255, 255))
                canvas = Image.new('RGBA', (w, h), bg_color)
    
    # Sort children by z-index
    children = page.get('children', [])
    children.sort(key=lambda x: safe_int(x.get('z'), 0))
    
    # Process each element recursively
    def process_element(el, parent_x=0, parent_y=0):
        """Recursively process elements including groups"""
        if not isinstance(el, dict):
            return
        
        elem_type = el.get('type', '').lower()
        x = parent_x + safe_float(el.get('x', 0))
        y = parent_y + safe_float(el.get('y', 0))
        
        # Update element position for rendering
        el_copy = el.copy()
        el_copy['x'] = x
        el_copy['y'] = y
        
        if not el.get('visible', True):
            return
        
        if elem_type == 'group':
            # Process children with offset
            for child in el.get('children', []):
                process_element(child, x, y)
                
        elif elem_type == 'text':
            draw = ImageDraw.Draw(canvas)
            render_text_element(draw, el_copy, overrides, w, h)
        
        elif elem_type in ('image', 'svg'):
            nonlocal canvas
            canvas = render_image_element(canvas, el_copy, overrides)
        
        elif elem_type in ('figure', 'shape', 'rect', 'circle', 'star', 'polygon', 'arrow'):
            draw = ImageDraw.Draw(canvas)
            render_shape_element(draw, el_copy)
        
        elif elem_type == 'line':
            draw = ImageDraw.Draw(canvas)
            render_shape_element(draw, el_copy)  # line is handled in shape function
    
    for child in children:
        try:
            process_element(child)
        except Exception as e:
            continue
    
    return canvas

# ───────────────────────────────────────────────
# UI Components
# ───────────────────────────────────────────────

st.title("🎨 Polotno to PIL Converter")
st.markdown("Convert Polotno JSON designs to high-quality images")

with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.transparent_bg = st.checkbox(
        "Transparent Background", 
        value=st.session_state.transparent_bg
    )

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
                
                # Show canvas dimensions from root
                root_w = safe_int(data.get('width'), 0)
                root_h = safe_int(data.get('height'), 0)
                
                pages = data.get('pages', [])
                st.success(f"✅ Loaded {len(pages)} page(s) • Canvas: {root_w}×{root_h}px")
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
