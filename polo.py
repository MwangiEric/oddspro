# bulk_ad_generator.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import os
import requests
import pandas as pd
from datetime import datetime
import zipfile
import textwrap

st.set_page_config(page_title="Bulk Ad 
# Read the current file and enhance SVG support
with open('/mnt/kimi/output/template_studio.py', 'r') as f:
    content = f.read()

# Find the imports section and add cairosvg
import_section = content.find('import streamlit')
if import_section != -1:
    # Add cairosvg import after other imports
    new_import = '''import streamlit as st
import json
import os
import re
import base64
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
from datetime import datetime

# Try to import cairosvg for SVG rendering
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False
    st.warning("cairosvg not installed. SVG support limited to placeholders.")'''
    
    content = content.replace('import streamlit as st\nimport json\nimport os\nimport re\nfrom PIL import Image, ImageDraw, ImageFont, ImageColor\nfrom io import BytesIO\nfrom datetime import datetime', new_import)

# Find the load_image function and add SVG loading
load_image_section = content.find('def load_image(src):')
if load_image_section != -1:
    # Replace the load_image function
    old_func = '''def load_image(src):
    """Load image from URL or base64"""
    if not src or not isinstance(src, str):
        return None
    
    try:
        if src.startswith('data:image'):
            base64_data = src.split(',')[1]
            img_data = base64.b64decode(base64_data)
            return Image.open(BytesIO(img_data)).convert('RGBA')
        elif src.startswith('http'):
            import requests
            response = requests.get(src, timeout=10)
            return Image.open(BytesIO(response.content)).convert('RGBA')
    except:
        pass
    return None'''
    
    new_func = '''def load_image(src):
    """Load image from URL or base64, including SVG"""
    if not src or not isinstance(src, str):
        return None
    
    try:
        # Handle SVG
        if 'svg' in src.lower() or src.startswith('data:image/svg'):
            return render_svg_to_image(src)
        
        # Handle base64
        if src.startswith('data:image'):
            base64_data = src.split(',')[1]
            img_data = base64.b64decode(base64_data)
            return Image.open(BytesIO(img_data)).convert('RGBA')
        
        # Handle URL
        elif src.startswith('http'):
            import requests
            response = requests.get(src, timeout=10)
            content_type = response.headers.get('content-type', '')
            
            if 'svg' in content_type.lower():
                return render_svg_to_image(response.text)
            else:
                return Image.open(BytesIO(response.content)).convert('RGBA')
    except Exception as e:
        pass
    return None

def render_svg_to_image(svg_data, width=None, height=None):
    """Convert SVG to PIL Image using cairosvg or fallback"""
    if not CAIROSVG_AVAILABLE:
        return None
    
    try:
        # If it's a data URI, extract the SVG
        if svg_data.startswith('data:image/svg'):
            svg_content = svg_data.split(',')[1]
            if svg_data.startswith('data:image/svg+xml;base64'):
                svg_bytes = base64.b64decode(svg_content)
            else:
                svg_bytes = svg_content.encode('utf-8')
        else:
            svg_bytes = svg_data.encode('utf-8') if isinstance(svg_data, str) else svg_data
        
        # Convert to PNG using cairosvg
        png_data = cairosvg.svg2png(bytestring=svg_bytes, 
                                     output_width=width, 
                                     output_height=height)
        
        return Image.open(BytesIO(png_data)).convert('RGBA')
    except Exception as e:
        return None'''
    
    content = content.replace(old_func, new_func)

# Find the draw_shape function and add more figure subtypes
draw_shape_section = content.find('def draw_shape(draw, x, y, w, h, subtype, fill, stroke, stroke_w, radius=0):')
if draw_shape_section != -1:
    old_draw = '''def draw_shape(draw, x, y, w, h, subtype, fill, stroke, stroke_w, radius=0):
    """Draw all shape types"""
    
    if subtype == 'rect':
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
                
    elif subtype == 'circle':
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
        
    elif subtype == 'topTriangle':
        points = [(x+w/2, y), (x, y+h), (x+w, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'bottomTriangle':
        points = [(x, y), (x+w, y), (x+w/2, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'diamond':
        points = [(x+w/2, y), (x+w, y+h/2), (x+w/2, y+h), (x, y+h/2)]
        draw.polygon(points, fill=fill, outline=stroke)'''
    
    new_draw = '''def draw_shape(draw, x, y, w, h, subtype, fill, stroke, stroke_w, radius=0):
    """Draw all figure/shape types"""
    
    # Basic shapes
    if subtype == 'rect' or subtype == 'rectangle':
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
                
    elif subtype == 'circle' or subtype == 'ellipse':
        if stroke and stroke[3] > 0:
            draw.ellipse([x, y, x+w, y+h], fill=fill, outline=stroke, width=int(stroke_w))
        else:
            draw.ellipse([x, y, x+w, y+h], fill=fill)
    
    # Triangles
    elif subtype == 'rightTriangle':
        points = [(x, y), (x+w, y), (x, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'leftTriangle':
        points = [(x, y), (x+w, y), (x+w, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'topTriangle' or subtype == 'triangle':
        points = [(x+w/2, y), (x, y+h), (x+w, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'bottomTriangle':
        points = [(x, y), (x+w, y), (x+w/2, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
    
    # Quadrilaterals
    elif subtype == 'diamond' or subtype == 'rhombus':
        points = [(x+w/2, y), (x+w, y+h/2), (x+w/2, y+h), (x, y+h/2)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'trapezoid' or subtype == 'trapezium':
        offset = w * 0.2
        points = [(x+offset, y), (x+w-offset, y), (x+w, y+h), (x, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'parallelogram':
        offset = w * 0.15
        points = [(x+offset, y), (x+w, y), (x+w-offset, y+h), (x, y+h)]
        draw.polygon(points, fill=fill, outline=stroke)
    
    # Other shapes
    elif subtype == 'pentagon':
        import math
        points = []
        cx, cy = x + w/2, y + h/2
        radius = min(w, h) / 2
        for i in range(5):
            angle = (i * 2 * math.pi / 5) - (math.pi / 2)
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            points.append((px, py))
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'hexagon':
        import math
        points = []
        cx, cy = x + w/2, y + h/2
        radius = min(w, h) / 2
        for i in range(6):
            angle = (i * 2 * math.pi / 6) - (math.pi / 2)
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            points.append((px, py))
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'octagon':
        import math
        points = []
        cx, cy = x + w/2, y + h/2
        radius = min(w, h) / 2
        for i in range(8):
            angle = (i * 2 * math.pi / 8) - (math.pi / 2)
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            points.append((px, py))
        draw.polygon(points, fill=fill, outline=stroke)
        
    elif subtype == 'cross':
        thickness = min(w, h) * 0.2
        # Vertical bar
        draw.rectangle([x+w/2-thickness/2, y, x+w/2+thickness/2, y+h], fill=fill)
        # Horizontal bar
        draw.rectangle([x, y+h/2-thickness/2, x+w, y+h/2+thickness/2], fill=fill)
        
    elif subtype == 'heart':
        import math
        # Simplified heart shape
        cx, cy = x + w/2, y + h/2
        # Two top circles
        r = min(w, h) / 4
        draw.ellipse([cx-w/4-r, cy-h/4-r, cx-w/4+r, cy-h/4+r], fill=fill)
        draw.ellipse([cx+w/4-r, cy-h/4-r, cx+w/4+r, cy-h/4+r], fill=fill)
        # Bottom triangle
        points = [(cx-w/2, cy), (cx, cy+h/2), (cx+w/2, cy)]
        draw.polygon(points, fill=fill)
        
    elif subtype == 'crescent':
        import math
        # Draw two overlapping circles to create crescent
        cx, cy = x + w/2, y + h/2
        r = min(w, h) / 2
        # Main circle
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill)
        # Cutout circle (slightly offset, using background color)
        offset = r * 0.3
        bg_color = (255, 255, 255, 0)  # Transparent
        draw.ellipse([cx-r+offset, cy-r, cx+r+offset, cy+r], fill=bg_color)
        
    elif subtype == 'ring' or subtype == 'donut':
        import math
        cx, cy = x + w/2, y + h/2
        outer_r = min(w, h) / 2
        inner_r = outer_r * 0.6
        # Draw outer circle
        draw.ellipse([cx-outer_r, cy-outer_r, cx+outer_r, cy+outer_r], fill=fill)
        # Cutout inner
        bg_color = (255, 255, 255, 0)
        draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r], fill=bg_color)
        
    else:
        # Default to rectangle for unknown types
        draw.rectangle([x, y, x+w, y+h], fill=fill, outline=stroke, width=int(stroke_w) if stroke else 0)'''
    
    content = content.replace(old_draw, new_draw)

# Find the SVG layer handling and enhance it
svg_section = content.find("elif layer_type == 'svg':")
if svg_section != -1:
    old_svg = '''elif layer_type == 'svg':
                # SVG placeholder
                x, y = layer['x'], layer['y']
                lw, lh = layer['width'], layer['height']
                fill = parse_color(layer.get('fill', 'gray'))
                fill = (fill[0], fill[1], fill[2], int(fill[3] * opacity))
                
                svg_layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(svg_layer)
                draw.rectangle([x, y, x+lw, y+lh], fill=fill, outline='darkgray', width=2)
                
                # Try to render SVG text
                try:
                    font = ImageFont.load_default()
                    draw.text((x+5, y+5), "SVG", fill='white')
                except:
                    pass
                
                img = Image.alpha_composite(img, svg_layer)'''
    
    new_svg = '''elif layer_type == 'svg':
                # Enhanced SVG support
                x, y = layer['x'], layer['y']
                lw, lh = layer['width'], layer['height']
                
                svg_src = layer.get('src', '')
                svg_data = layer.get('svgData', '')
                
                svg_image = None
                
                # Try to render actual SVG
                if svg_src and CAIROSVG_AVAILABLE:
                    svg_image = render_svg_to_image(svg_src, int(lw), int(lh))
                elif svg_data and CAIROSVG_AVAILABLE:
                    svg_image = render_svg_to_image(svg_data, int(lw), int(lh))
                
                if svg_image:
                    # Apply opacity
                    if opacity < 1:
                        alpha = svg_image.split()[-1]
                        alpha = alpha.point(lambda p: int(p * opacity))
                        svg_image.putalpha(alpha)
                    
                    # Apply rotation
                    rotation = layer.get('rotation', 0)
                    if rotation != 0:
                        svg_image = svg_image.rotate(-rotation, expand=True, 
                                                    resample=Image.Resampling.BICUBIC)
                    
                    img.paste(svg_image, (int(x), int(y)), svg_image)
                else:
                    # Fallback: placeholder
                    fill = parse_color(layer.get('fill', 'gray'))
                    fill = (fill[0], fill[1], fill[2], int(fill[3] * opacity))
                    
                    svg_layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(svg_layer)
                    draw.rectangle([x, y, x+lw, y+lh], fill=fill, outline='darkgray', width=2)
                    
                    try:
                        font = ImageFont.load_default()
                        draw.text((x+5, y+5), "SVG", fill='white')
                        draw.text((x+5, y+20), "(install cairosvg)", fill='white')
                    except:
                        pass
                    
                    img = Image.alpha_composite(img, svg_layer)'''
    
    content = content.replace(old_svg, new_svg)

# Write the enhanced file
output_path = '/mnt/kimi/output/template_studio.py'
with open(output_path, 'w') as f:
    f.write(content)

print(f"✅ Enhanced Template Studio saved: {output_path}")
print(f"\n🔧 ENHANCEMENTS:")
print("   ✓ SVG rendering with cairosvg (install: pip install cairosvg)")
print("   ✓ SVG from URL, base64, or inline data")
print("   ✓ 15+ figure shapes supported:")
print("     - Basic: rect, circle, ellipse")
print("     - Triangles: right, left, top, bottom")
print("     - Quadrilaterals: diamond, trapezoid, parallelogram")
print("     - Polygons: pentagon, hexagon, octagon")
print("     - Special: cross, heart, crescent, ring/donut")
print("\n📦 TO INSTALL SVG SUPPORT:")
print("   pip install cairosvg")
print("\n🚀 TO RUN:")
print("   streamlit run template_studio.py")", layout="wide")

# API Configuration - CORRECT ENDPOINT
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
    'product_y': 200,
    'product_w': 400,
    'product_h': 400,
    'product_radius': 20,
    'price_x': 100,
    'price_y': 650,
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
    'name_size': 32,
    'name_color': '#FFFFFF',
    'name_align': 'left',
    'name_weight': 'bold',
    'name_bg': True,
    'name_bg_color': '#000000',
    'name_padding': 12,
    'name_radius': 8,
    'name_shadow': True,
    'name_max_width': 800,  # For text wrapping
    'name_max_lines': 2,
    'use_image_search': False,
    'image_search_col': None,
    'api_file_type': 'png',  # png, jpg, webp
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def search_product_image(query, file_type='png'):
    """Search for product image using ImagAPI - CORRECT ENDPOINT"""
    if not query or pd.isna(query):
        return None
    
    try:
        # CORRECT: Use /products/search endpoint with proper params
        url = f"{IMAGAPI_BASE}/products/search"
        params = {
            "q": str(query)[:100],
            "file_type": file_type,  # png, jpg, webp
            "limit": 5  # Get a few results to have fallback
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Parse response
        images = data.get("images", []) or data.get("results", []) or []
        
        if images and len(images) > 0:
            # Use first valid image
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

def wrap_text_to_lines(text, font, max_width, max_lines=2):
    """Wrap text to fit within max_width, limited to max_lines"""
    if not text:
        return [""]
    
    text = str(text).strip()
    
    # Try to fit on one line first
    bbox = font.getbbox(text)
    if bbox[2] - bbox[0] <= max_width:
        return [text]
    
    # Calculate average char width
    avg_char_width = (bbox[2] - bbox[0]) / len(text) if len(text) > 0 else 10
    chars_per_line = int(max_width / avg_char_width) if avg_char_width > 0 else 20
    
    # Wrap text
    wrapped = textwrap.wrap(text, width=max(chars_per_line, 10), 
                           break_long_words=True, break_on_hyphens=True)
    
    # Limit to max_lines
    if len(wrapped) > max_lines:
        # Join first max_lines-1, then truncate last with ellipsis
        result = wrapped[:max_lines-1]
        last_line = wrapped[max_lines-1]
        # Truncate last line and add ellipsis
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
    
    # Calculate total dimensions
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
    
    # Adjust start Y to not cut off first line
    first_line_h = line_heights[0] if line_heights else font.size
    y = y - first_line_h + font.size  # Adjust baseline
    
    # Draw background
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
    
    # Draw each line
    current_y = y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        
        # Alignment
        line_x = x
        if align == 'center':
            line_x = x - line_w // 2
        elif align == 'right':
            line_x = x - line_w
        
        # Shadow
        if shadow:
            draw.text((line_x + 2, current_y + 2), line, font=font, fill='black')
        
        # Text
        draw.text((line_x, current_y), line, font=font, fill=color)
        
        current_y += line_heights[i] * line_height
    
    return current_y

def render_single_ad(canvas_size, base_image, product_image, product_name, price, config):
    """Render a single ad with given parameters"""
    # Create canvas
    canvas = Image.new('RGBA', canvas_size, (255, 255, 255, 255))
    
    # Paste base image (resize to fit canvas)
    if base_image:
        bg = base_image.copy().resize(canvas_size, Image.Resampling.LANCZOS)
        canvas.paste(bg, (0, 0), bg)
    
    draw = ImageDraw.Draw(canvas)
    
    # Draw Product Name (with text wrapping)
    if config.get('show_product_name') and product_name:
        name_font = get_font(config['name_size'], config['name_weight'])
        name_color = ImageColor.getrgb(config['name_color'])
        name_bg_color = ImageColor.getrgb(config['name_bg_color'])
        
        # Wrap text to max 2 lines
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
            config['name_shadow'], 1.3  # Slightly more line height for names
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
base_file = st.file_uploader("Choose base image - will be resized to canvas", 
                             type=['png', 'jpg', 'jpeg', 'webp'], key="base")

if base_file:
    st.session_state.base_image = Image.open(base_file).convert('RGBA')
    st.success(f"✅ Base image loaded")
else:
    st.session_state.base_image = None

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
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        use_search = st.checkbox("🔍 Use ImagAPI Image Search", 
                                value=st.session_state.use_image_search)
        st.session_state.use_image_search = use_search
    
    with col2:
        if use_search:
            st.session_state.api_file_type = st.selectbox(
                "Image Format", 
                ['png', 'jpg', 'webp'],
                index=['png', 'jpg', 'webp'].index(st.session_state.api_file_type)
            )
    
    if use_search:
        st.info(f"Will search ImagAPI `/products/search` with file_type={st.session_state.api_file_type}")
        
        if st.button("🔎 Test Search (First Product)"):
            with st.spinner("Searching..."):
                first_name = df.iloc[0, st.session_state.name_col]
                result = search_product_image(first_name, st.session_state.api_file_type)
                if result:
                    st.success(f"✅ Found: {result['url'][:60]}...")
                    thumb = load_image_from_url(result['thumbnail'] or result['url'])
                    if thumb:
                        st.image(thumb, width=200, caption="First result")
                else:
                    st.error("❌ No images found")

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
        st.caption(f"Sample: {str(sample)[:40]}...")
    
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
    with st.expander("🏷️ Product Name Settings (2-Line Wrap)", expanded=True):
        st.session_state.show_product_name = st.checkbox("Show Product Name", 
                                                        st.session_state.show_product_name)
        
        if st.session_state.show_product_name:
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.name_x = st.number_input("Name X", 0, cw, st.session_state.name_x)
                st.session_state.name_y = st.number_input("Name Y", 0, ch, st.session_state.name_y)
                st.session_state.name_size = st.slider("Name Font Size", 10, 80, st.session_state.name_size)
            with col2:
                st.session_state.name_align = st.selectbox("Name Align", ["left", "center", "right"], 
                                                          index=["left", "center", "right"].index(st.session_state.name_align))
                st.session_state.name_weight = st.selectbox("Name Weight", ["normal", "bold"],
                                                           index=["normal", "bold"].index(st.session_state.name_weight))
                st.session_state.name_color = st.color_picker("Name Color", st.session_state.name_color)
            
            # Text wrapping settings
            st.session_state.name_max_width = st.slider("Max Text Width", 200, cw-100, st.session_state.name_max_width)
            st.session_state.name_max_lines = st.slider("Max Lines", 1, 3, st.session_state.name_max_lines)
            
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
            ("↖️ Top Left", 50, 180),
            ("↗️ Top Right", cw - st.session_state.product_w - 50, 180),
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
                    result = search_product_image(name, st.session_state.api_file_type)
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
                'name_radius', 'name_shadow', 'name_max_width', 'name_max_lines',
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
            'name_radius', 'name_shadow', 'name_max_width', 'name_max_lines',
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
                result = search_product_image(name, st.session_state.api_file_type)
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
        
        st.success(f"✅ Generated {len(generated)} ads!")
        
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
                f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col3:
            with st.expander(f"View All {min(len(generated), 10)} Ads"):
                for i, (img, name) in enumerate(zip(generated[:10], names[:10])):
                    st.image(img, caption=f"{i+1}. {name[:40]}", use_column_width=True)
