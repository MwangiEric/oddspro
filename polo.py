import streamlit as st
import json
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import re
from urllib.parse import unquote
import numpy as np
import tempfile
import os
from functools import lru_cache

st.set_page_config(page_title="Polotno Template Renderer", layout="wide")

try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip

# ============== UTILS ==============

@lru_cache(maxsize=32)
def get_font(size, font_family):
    """Cache fonts."""
    try:
        font_paths = [
            f"/usr/share/fonts/truetype/{font_family.replace(' ', '')}/{font_family.replace(' ', '')}-Regular.ttf",
            f"/usr/share/fonts/truetype/{font_family.lower().replace(' ', '')}/{font_family.lower().replace(' ', '')}-regular.ttf",
            f"/System/Library/Fonts/{font_family.replace(' ', '')}.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, int(size))
                except:
                    continue
        try:
            return ImageFont.truetype(font_family, int(size))
        except:
            pass
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

def load_image_from_url(url):
    """Load image from URL."""
    if not url:
        return None
    try:
        clean_url = unquote(url.replace('&amp;', '&').strip())
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(clean_url, timeout=15, headers=headers)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        return img
    except:
        return None

def hex_to_rgba(color_str):
    """Convert color formats to RGBA."""
    if not color_str:
        return (0, 0, 0, 255)
    try:
        if color_str.startswith('rgba'):
            match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', color_str)
            if match:
                r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                a = int(float(match.group(4)) * 255)
                return (r, g, b, a)
        if color_str.startswith('rgb'):
            match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
            if match:
                return tuple(int(match.group(i)) for i in range(1, 4)) + (255,)
        color_str = color_str.lstrip('#')
        if len(color_str) == 6:
            return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(color_str) == 8:
            return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4, 6))
    except:
        pass
    return (0, 0, 0, 255)

def extract_variables(text):
    """Extract {{variable}} patterns."""
    if not text:
        return []
    return re.findall(r'\{\{(\w+)\}\}', text)

def is_image_variable(var_name):
    """Check if variable is an image variable."""
    return var_name.startswith('image') and var_name[5:].isdigit()

# ============== RENDERING ==============

def render_text_overlay(draw, element, data):
    """Render text element onto existing image."""
    text = element.get('text', '')
    name = element.get('name', '')
    
    # Get template text from name or text field
    template = name if name and '{{' in name else text
    
    # Replace variables
    for var in extract_variables(template):
        value = data.get(var, '')
        template = template.replace(f'{{{var}}}', str(value))
    
    if not template.strip():
        return
    
    x = element.get('x', 0)
    y = element.get('y', 0)
    w = element.get('width', 100)
    h = element.get('height', 50)
    
    font_size = element.get('fontSize', 20)
    font_family = element.get('fontFamily', 'Roboto')
    fill = hex_to_rgba(element.get('fill', 'rgba(0,0,0,1)'))
    align = element.get('align', 'left')
    
    font = get_font(int(font_size), font_family)
    
    # Calculate position
    try:
        bbox = draw.textbbox((0, 0), template, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width, text_height = draw.textsize(template, font=font)
    
    if align == 'center':
        text_x = x + (w - text_width) / 2
    elif align == 'right':
        text_x = x + w - text_width
    else:
        text_x = x
    
    text_y = y + (h - text_height) / 2
    
    # Draw with optional shadow/outline for readability
    shadow = element.get('shadowEnabled', False)
    if shadow:
        shadow_color = element.get('shadowColor', 'black')
        shadow_blur = element.get('shadowBlur', 5)
        shadow_x = element.get('shadowOffsetX', 0)
        shadow_y = element.get('shadowOffsetY', 0)
        # Simple shadow
        draw.text((text_x + shadow_x, text_y + shadow_y), template, 
                 fill=shadow_color, font=font)
    
    draw.text((text_x, text_y), template, fill=fill[:3], font=font)

def render_image_overlay(base_img, element, data):
    """Render image element onto base image."""
    name = element.get('name', '')
    
    # Check if it's a template variable
    if not (name and '{{' in name):
        return  # Skip non-variable images (base template handles it)
    
    var_name = name.replace('{{', '').replace('}}', '')
    img_url = data.get(var_name)
    
    if not img_url:
        return
    
    x = int(element.get('x', 0))
    y = int(element.get('y', 0))
    w = int(element.get('width', 100))
    h = int(element.get('height', 100))
    
    # Load and resize image
    img_to_render = load_image_from_url(img_url)
    if not img_to_render:
        return
    
    img_to_render = img_to_render.resize((w, h), Image.Resampling.LANCZOS)
    
    # Handle rounded corners if specified
    corner_radius = element.get('cornerRadius', 0)
    if corner_radius > 0:
        # Create mask for rounded corners
        mask = Image.new('L', (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius=corner_radius, fill=255)
        img_to_render.putalpha(mask)
    
    # Paste onto base
    if img_to_render.mode == 'RGBA':
        base_img.paste(img_to_render, (x, y), img_to_render)
    else:
        base_img.paste(img_to_render, (x, y))

def render_svg_overlay(draw, element):
    """Render SVG shape."""
    x = element.get('x', 0)
    y = element.get('y', 0)
    width = element.get('width', 100)
    height = element.get('height', 100)
    
    colors_replace = element.get('colorsReplace', {})
    fill_color = (0, 161, 255, 255)
    
    if colors_replace:
        for old_color, new_color in colors_replace.items():
            fill_color = hex_to_rgba(new_color)
    
    # Handle opacity
    opacity = element.get('opacity', 1)
    if opacity < 1:
        fill_color = (*fill_color[:3], int(fill_color[3] * opacity))
    
    draw.rectangle([x, y, x + width, y + height], fill=fill_color[:3])

def render_poster(base_image, template_data, data):
    """Render final poster by overlaying variables on base image."""
    # Convert base to RGBA for compositing
    if base_image.mode != 'RGBA':
        result = base_image.convert('RGBA')
    else:
        result = base_image.copy()
    
    pages = template_data.get('pages', [])
    if not pages:
        return result.convert('RGB')
    
    page = pages[0]
    children = page.get('children', [])
    
    # Sort: SVGs first, then images, then text (text on top)
    elements = sorted(children, key=lambda e: {
        'svg': 0, 'image': 1, 'text': 2
    }.get(e.get('type'), 3))
    
    # Render each element
    for element in elements:
        elem_type = element.get('type')
        
        if elem_type == 'svg':
            draw = ImageDraw.Draw(result)
            render_svg_overlay(draw, element)
        
        elif elem_type == 'image':
            render_image_overlay(result, element, data)
        
        elif elem_type == 'text':
            draw = ImageDraw.Draw(result)
            render_text_overlay(draw, element, data)
    
    return result.convert('RGB')

def parse_template_variables(template_data):
    """Extract all template variables."""
    variables = {}
    
    pages = template_data.get('pages', [])
    for page in pages:
        for child in page.get('children', []):
            name = child.get('name', '')
            if name and '{{' in name:
                var = name.replace('{{', '').replace('}}', '')
                variables[var] = {
                    'type': child.get('type'),
                    'is_image': is_image_variable(var)
                }
    
    return variables

# ============== UI ==============

def main():
    st.title("🎨 Polotno Poster Generator")
    st.markdown("Upload your **base image template** + **Polotno JSON** to generate posters with dynamic variables.")
    
    with st.sidebar:
        st.header("📁 Upload Files")
        
        # Base image template
        base_image_file = st.file_uploader(
            "1. Base Image Template", 
            type=['png', 'jpg', 'jpeg'],
            help="This is your background image. All variables will be overlaid on this."
        )
        
        # Polotno JSON
        template_file = st.file_uploader(
            "2. Polotno JSON", 
            type=['json'],
            help="Contains layout positions and variable placeholders like {{name}}, {{price}}, {{image1}}"
        )
        
        st.divider()
        
        st.header("🌐 Data Source")
        data_source = st.radio("Choose:", ["Manual Entry", "JSON Feed URL"])
        
        if data_source == "JSON Feed URL":
            feed_url = st.text_input(
                "Feed URL",
                value="https://myrhub.vercel.app/kenyatronics/view/samsung-galaxy-s26-ultra-12gb-ram-512gb-69-inch-dynamic-amoled-200mp-camera?format=json",
                help="RSS/JSON feed with product data"
            )
            
            if st.button("📥 Load from Feed", use_container_width=True):
                with st.spinner("Fetching..."):
                    try:
                        response = requests.get(feed_url, timeout=10)
                        data = response.json()
                        
                        if data.get('items'):
                            content = json.loads(data['items'][0]['content_html'])
                            
                            new_data = {
                                'name': content.get('name', ''),
                                'price': f"KSh {content.get('price', '')}",
                                'ram': content.get('ram', ''),
                                'rom': content.get('rom', ''),
                                'spec1': content.get('ram', ''),
                                'spec2': content.get('rom', ''),
                            }
                            
                            # Add images
                            for i, img in enumerate(content.get('images', []), 1):
                                new_data[f'image{i}'] = img
                            
                            st.session_state.data = new_data
                            st.success(f"Loaded: {new_data.get('name', 'Unknown')}")
                    except Exception as e:
                        st.error(f"Failed: {str(e)[:100]}")
        
        st.divider()
        
        generate_btn = st.button("🚀 Generate Poster", type="primary", use_container_width=True)
    
    # Main content area
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📝 Edit Variables")
        
        # Parse template
        template_data = None
        if template_file:
            try:
                template_data = json.load(template_file)
                st.caption(f"Template: {template_data.get('width', 0)}×{template_data.get('height', 0)}")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
        
        # Show base image preview
        base_image = None
        if base_image_file:
            base_image = Image.open(base_image_file)
            st.image(base_image, caption="Base Template", width=300)
        
        # Variable editing
        if template_data:
            variables = parse_template_variables(template_data)
            
            if variables:
                st.write("**Detected Variables:**")
                
                # Initialize data in session state if not exists
                if 'data' not in st.session_state:
                    st.session_state.data = {}
                
                for var, info in variables.items():
                    current = st.session_state.data.get(var, '')
                    
                    if info['is_image']:
                        st.markdown(f"**{{{var}}}** (Image)")
                        if current:
                            st.image(current, width=150)
                        new_url = st.text_input(
                            f"Image URL for {var}", 
                            value=str(current),
                            key=f"var_{var}"
                        )
                        if new_url:
                            st.session_state.data[var] = new_url
                    else:
                        new_val = st.text_input(
                            f"{{{var}}}",
                            value=str(current),
                            key=f"var_{var}"
                        )
                        st.session_state.data[var] = new_val
            else:
                st.info("No template variables ({{name}}, etc.) found in JSON")
        else:
            st.info("Upload Polotno JSON to see variables")
    
    with col2:
        st.subheader("🖼️ Preview")
        
        if generate_btn and base_image and template_data:
            data = st.session_state.get('data', {})
            
            with st.spinner("Generating poster..."):
                result = render_poster(base_image, template_data, data)
                
                if result:
                    st.image(result, use_container_width=True)
                    
                    # Download buttons
                    col_dl1, col_dl2 = st.columns(2)
                    
                    with col_dl1:
                        buf = io.BytesIO()
                        result.save(buf, format='PNG')
                        st.download_button(
                            "⬇️ PNG",
                            buf.getvalue(),
                            file_name="poster.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    
                    with col_dl2:
                        buf = io.BytesIO()
                        result.save(buf, format='JPEG', quality=95)
                        st.download_button(
                            "⬇️ JPG",
                            buf.getvalue(),
                            file_name="poster.jpg",
                            mime="image/jpeg",
                            use_container_width=True
                        )
        
        elif not base_image:
            st.info("Upload a base image template to start")
        elif not template_data:
            st.info("Upload a Polotno JSON with variable placeholders")

if __name__ == "__main__":
    main()
