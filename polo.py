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
import hashlib

# Page config must be first
st.set_page_config(page_title="Polotno Template Renderer", layout="wide")

# MoviePy imports
try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip

# Constants
CACHE_DIR = tempfile.gettempdir()

@st.cache_data(ttl=3600)
def fetch_product_data(feed_url):
    """Fetch and cache product data from JSON feed."""
    try:
        response = requests.get(feed_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get('items') and len(data['items']) > 0:
            item = data['items'][0]
            content = json.loads(item['content_html'])
            
            product_data = {
                'name': content.get('name', ''),
                'price': f"KSh {content.get('price', '')}" if content.get('price') else '',
            }
            
            for key, value in content.items():
                if key not in product_data:
                    product_data[key] = value
            
            images = content.get('images', [])
            product_data['images'] = images
            
            for i, img_url in enumerate(images, 1):
                product_data[f'image{i}'] = img_url
            
            if 'ram' in content:
                product_data['spec1'] = content['ram']
            if 'rom' in content or 'storage' in content:
                product_data['spec2'] = content.get('rom') or content.get('storage', '')
                
            return product_data
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def load_image_from_url(url):
    """Cache loaded images."""
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

def decode_base64_image(base64_string):
    """Decode base64 image."""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        image_data = base64.b64decode(base64_string)
        img = Image.open(io.BytesIO(image_data))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        return img
    except:
        return None

def extract_variables(text):
    """Extract {{variable}} patterns."""
    if not text:
        return []
    return re.findall(r'\{\{(\w+)\}\}', text)

def substitute_variables(text, data):
    """Replace variables with data."""
    if not text or not data:
        return text
    
    result = text
    for var in extract_variables(text):
        value = data.get(var, '')
        result = result.replace(f'{{{var}}}', str(value))
    
    return result

def is_image_variable(var_name):
    """Check if variable is an image variable."""
    return var_name.startswith('image') and var_name[5:].isdigit()

def render_svg_element(draw, element):
    """Render SVG rectangle."""
    x = element.get('x', 0)
    y = element.get('y', 0)
    width = element.get('width', 100)
    height = element.get('height', 100)
    
    colors_replace = element.get('colorsReplace', {})
    fill_color = (0, 161, 255, 255)
    
    if colors_replace:
        for old_color, new_color in colors_replace.items():
            fill_color = hex_to_rgba(new_color)
    
    draw.rectangle([x, y, x + width, y + height], fill=fill_color[:3])

def render_element_to_array(element, data, canvas_width, canvas_height, is_text_editable=False):
    """Render element to numpy array for video frames."""
    x = int(element.get('x', 0))
    y = int(element.get('y', 0))
    w = int(element.get('width', 100))
    h = int(element.get('height', 100))
    
    # Create transparent RGBA image
    img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    
    elem_type = element.get('type')
    
    if elem_type == 'svg':
        draw = ImageDraw.Draw(img)
        render_svg_element(draw, element)
    
    elif elem_type == 'image':
        name = element.get('name', '')
        src = element.get('src', '')
        
        img_to_render = None
        
        if name and '{{' in name:
            var_name = name.replace('{{', '').replace('}}', '')
            img_url = data.get(var_name)
            if img_url:
                img_to_render = load_image_from_url(img_url)
        else:
            if src.startswith('http'):
                img_to_render = load_image_from_url(src)
            elif src.startswith('data:image'):
                img_to_render = decode_base64_image(src)
        
        if img_to_render:
            img_to_render = img_to_render.resize((w, h), Image.Resampling.LANCZOS)
            img.paste(img_to_render, (x, y), img_to_render)
    
    elif elem_type == 'text':
        draw = ImageDraw.Draw(img)
        text = element.get('text', '')
        name = element.get('name', '')
        
        # Use name if it's a template, otherwise use text
        template_text = name if name and '{{' in name else text
        
        # If editable and has variables, use edited value
        if is_text_editable and name and '{{' in name:
            var_name = name.replace('{{', '').replace('}}', '')
            if not is_image_variable(var_name):
                final_text = data.get(var_name, substitute_variables(template_text, data))
            else:
                final_text = substitute_variables(template_text, data)
        else:
            final_text = substitute_variables(template_text, data)
        
        if not final_text or final_text.strip() == '':
            return None
        
        font_size = element.get('fontSize', 20)
        font_family = element.get('fontFamily', 'Roboto')
        fill = hex_to_rgba(element.get('fill', 'rgba(0,0,0,1)'))
        align = element.get('align', 'left')
        
        font = get_font(int(font_size), font_family)
        
        try:
            bbox = draw.textbbox((0, 0), final_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width, text_height = draw.textsize(final_text, font=font)
        
        if align == 'center':
            text_x = x + (w - text_width) / 2
        elif align == 'right':
            text_x = x + w - text_width
        else:
            text_x = x
        
        text_y = y + (h - text_height) / 2
        
        draw.text((text_x, text_y), final_text, fill=fill[:3], font=font)
    
    return np.array(img)

def parse_animations(element):
    """Parse enabled animations."""
    animations = element.get('animations', [])
    enabled = []
    for anim in animations:
        if anim.get('enabled', False):
            enabled.append({
                'type': anim.get('type'),
                'name': anim.get('name'),
                'delay': anim.get('delay', 0) / 1000,
                'duration': anim.get('duration', 500) / 1000,
            })
    return enabled

def apply_animation_effect(elem_array, element, anim, progress, canvas_width, canvas_height):
    """Apply animation effect to element array."""
    anim_name = anim['name']
    anim_type = anim['type']
    
    x = int(element.get('x', 0))
    y = int(element.get('y', 0))
    w = int(element.get('width', 100))
    h = int(element.get('height', 100))
    
    # Extract region
    region = elem_array[y:y+h, x:x+w].copy()
    
    if region.size == 0:
        return elem_array
    
    if anim_name == 'fade':
        if anim_type == 'enter':
            alpha = progress
        elif anim_type == 'exit':
            alpha = 1 - progress
        else:
            alpha = 0.5 + 0.5 * np.sin(progress * 2 * np.pi)
        
        # Apply alpha to region
        elem_array[y:y+h, x:x+w] = (region * alpha).astype(np.uint8)
    
    elif anim_name == 'zoom':
        if anim_type == 'enter':
            scale = 0.5 + 0.5 * progress
        elif anim_type == 'exit':
            scale = 1.0 - 0.5 * progress
        else:
            scale = 1.0 + 0.1 * np.sin(progress * 2 * np.pi)
        
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        
        # Resize region
        from PIL import Image as PILImage
        pil_region = PILImage.fromarray(region)
        pil_region = pil_region.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
        resized = np.array(pil_region)
        
        # Center crop/paste
        y_offset = (new_h - h) // 2
        x_offset = (new_w - w) // 2
        
        # Clear original region
        elem_array[y:y+h, x:x+w] = 0
        
        # Calculate paste bounds
        src_y1 = max(0, y_offset)
        src_y2 = min(h + y_offset, new_h)
        src_x1 = max(0, x_offset)
        src_x2 = min(w + x_offset, new_w)
        dst_y1 = max(0, -y_offset)
        dst_y2 = min(h, new_h - y_offset)
        dst_x1 = max(0, -x_offset)
        dst_x2 = min(w, new_w - x_offset)
        
        if dst_y2 > dst_y1 and dst_x2 > dst_x1:
            elem_array[y+dst_y1:y+dst_y2, x+dst_x1:x+dst_x2] = resized[src_y1:src_y2, src_x1:src_x2]
    
    elif anim_name == 'blink':
        alpha = 0.5 + 0.5 * np.sin(progress * 2 * np.pi)
        elem_array[y:y+h, x:x+w] = (region * alpha).astype(np.uint8)
    
    return elem_array

def render_video_optimized(template_data, edited_data, fps=30, progress_bar=None):
    """Optimized video rendering with pre-caching."""
    width = int(template_data.get('width', 1080))
    height = int(template_data.get('height', 1080))
    
    pages = template_data.get('pages', [])
    if not pages:
        return None
    
    page = pages[0]
    total_duration = page.get('duration', 5000) / 1000
    bg_color = hex_to_rgba(page.get('background', 'rgba(255,255,255,1)'))
    
    children = page.get('children', [])
    total_frames = int(total_duration * fps)
    
    # Pre-render all static elements to single array
    static_elements = []
    animated_elements = []
    
    for child in children:
        anims = parse_animations(child)
        if anims:
            animated_elements.append((child, anims))
        else:
            static_elements.append(child)
    
    # Pre-render static layer once
    static_layer = np.zeros((height, width, 4), dtype=np.uint8)
    static_layer[:, :] = bg_color
    
    for elem in static_elements:
        elem_array = render_element_to_array(elem, edited_data, width, height, is_text_editable=True)
        if elem_array is not None:
            # Alpha composite
            alpha = elem_array[:, :, 3:4] / 255.0
            static_layer = (elem_array * alpha + static_layer * (1 - alpha)).astype(np.uint8)
    
    # Pre-render animated elements (full opacity)
    animated_layers = []
    for elem, anims in animated_elements:
        elem_array = render_element_to_array(elem, edited_data, width, height, is_text_editable=True)
        animated_layers.append((elem, anims, elem_array))
    
    # Generate frames
    frames = []
    for frame_idx in range(total_frames):
        time = frame_idx / fps
        
        # Start with static layer
        frame = static_layer.copy()
        
        # Apply animated elements
        for elem, anims, elem_array in animated_layers:
            if elem_array is None:
                continue
                
            x = int(elem.get('x', 0))
            y = int(elem.get('y', 0))
            w = int(elem.get('width', 100))
            h = int(elem.get('height', 100))
            
            # Find active animation
            applied = False
            for anim in anims:
                delay = anim['delay']
                duration = anim['duration']
                anim_type = anim['type']
                
                if anim_type in ['enter', 'exit']:
                    if time >= delay and time <= delay + duration:
                        progress = (time - delay) / duration
                        elem_copy = elem_array.copy()
                        elem_copy = apply_animation_effect(elem_copy, elem, anim, progress, width, height)
                        # Composite
                        alpha = elem_copy[:, :, 3:4] / 255.0
                        frame = (elem_copy * alpha + frame * (1 - alpha)).astype(np.uint8)
                        applied = True
                        break
                    elif time > delay + duration and anim_type == 'enter':
                        # After enter, show full
                        alpha = elem_array[:, :, 3:4] / 255.0
                        frame = (elem_array * alpha + frame * (1 - alpha)).astype(np.uint8)
                        applied = True
                        break
                    elif time < delay and anim_type == 'exit':
                        alpha = elem_array[:, :, 3:4] / 255.0
                        frame = (elem_array * alpha + frame * (1 - alpha)).astype(np.uint8)
                        applied = True
                        break
                else:  # loop
                    loop_time = (time - delay) % duration if time >= delay else 0
                    progress = loop_time / duration
                    elem_copy = elem_array.copy()
                    elem_copy = apply_animation_effect(elem_copy, elem, anim, progress, width, height)
                    alpha = elem_copy[:, :, 3:4] / 255.0
                    frame = (elem_copy * alpha + frame * (1 - alpha)).astype(np.uint8)
                    applied = True
                    break
            
            if not applied:
                # No animation applied, show full
                alpha = elem_array[:, :, 3:4] / 255.0
                frame = (elem_array * alpha + frame * (1 - alpha)).astype(np.uint8)
        
        # Convert to RGB
        frames.append(frame[:, :, :3])
        
        if progress_bar and frame_idx % 10 == 0:
            progress_bar.progress(min(1.0, frame_idx / total_frames))
    
    if progress_bar:
        progress_bar.progress(1.0)
    
    # Create video clip
    def make_frame(t):
        idx = min(int(t * fps), len(frames) - 1)
        return frames[idx]
    
    try:
        clip = VideoClip(make_frame, duration=total_duration)
        clip = clip.with_fps(fps)
    except:
        clip = VideoClip(make_frame, duration=total_duration)
        clip.fps = fps
    
    return clip

def analyze_template(template_data):
    """Analyze template for variables and animations."""
    variables = {}
    animated_count = 0
    
    pages = template_data.get('pages', [])
    duration = pages[0].get('duration', 5000) / 1000 if pages else 5
    
    for page in pages:
        for child in page.get('children', []):
            name = child.get('name', '')
            text = child.get('text', '')
            
            # Check for variables in name
            if name and '{{' in name:
                var = name.replace('{{', '').replace('}}', '')
                elem_type = child.get('type')
                variables[var] = {'type': elem_type, 'is_image': is_image_variable(var)}
            
            # Check for animations
            if child.get('animations'):
                if any(a.get('enabled') for a in child.get('animations', [])):
                    animated_count += 1
    
    return variables, animated_count, duration

def main():
    st.title("🎬 Polotno Template Renderer")
    
    # Sidebar for controls
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Template input
        st.subheader("Template")
        template_file = st.file_uploader("Upload JSON", type=['json'])
        template_json_str = st.text_area("Or paste JSON", height=150)
        
        # Data feed
        st.subheader("Data Feed")
        feed_url = st.text_input(
            "Feed URL",
            value="https://myrhub.vercel.app/kenyatronics/view/xiaomi-redmi-note-15-pro-5g-8gb-ram-256gb-rom-683-inch-amoled-display-200mp-camera?format=json"
        )
        
        load_data = st.button("📥 Load Data", use_container_width=True)
        
        # Output settings
        st.subheader("Output")
        output_type = st.radio("Type", ["Image (PNG)", "Video (MP4)"], index=1)
        
        if output_type == "Video (MP4)":
            fps = st.slider("FPS", 15, 60, 30)
            quality = st.select_slider("Quality", options=["Fast", "Balanced", "High"], value="Balanced")
        
        debug = st.checkbox("Debug Mode", value=False)
        
        generate = st.button("🚀 Generate", type="primary", use_container_width=True)
    
    # Main content area
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📝 Edit Content")
        
        # Parse template
        template_data = None
        if template_file:
            try:
                template_data = json.load(template_file)
            except:
                st.error("Invalid JSON file")
        elif template_json_str:
            try:
                template_data = json.loads(template_json_str)
            except:
                st.error("Invalid JSON")
        
        if template_data:
            width = template_data.get('width', 1080)
            height = template_data.get('height', 1080)
            st.caption(f"Canvas: {width}×{height}")
            
            # Analyze template
            template_vars, anim_count, duration = analyze_template(template_data)
            
            if anim_count > 0:
                st.info(f"🎞️ {anim_count} animated elements • {duration:.1f}s")
            
            # Fetch product data
            if 'product_data' not in st.session_state or load_data:
                with st.spinner("Loading..."):
                    st.session_state.product_data = fetch_product_data(feed_url)
            
            product_data = st.session_state.get('product_data', {})
            
            # Build editable fields
            edited_data = product_data.copy() if product_data else {}
            
            if template_vars:
                st.write("**Editable Fields:**")
                
                for var, info in template_vars.items():
                    if info['is_image']:
                        # Display image preview
                        img_url = edited_data.get(var)
                        if img_url:
                            st.image(img_url, width=100, caption=f"{{{var}}}")
                        else:
                            st.caption(f"{{{var}}}: No image")
                    else:
                        # Editable text field
                        current_val = edited_data.get(var, '')
                        new_val = st.text_input(
                            f"{{{var}}}",
                            value=str(current_val),
                            key=f"edit_{var}"
                        )
                        edited_data[var] = new_val
            else:
                st.info("No template variables found")
        else:
            st.info("Upload a template to start")
    
    with col2:
        st.subheader("🖼️ Preview")
        
        if template_data and generate:
            if output_type == "Image (PNG)":
                with st.spinner("Rendering..."):
                    # Render single frame
                    from PIL import Image as PILImage
                    img = PILImage.new('RGBA', (width, height), (255, 255, 255, 255))
                    
                    children = template_data.get('pages', [{}])[0].get('children', [])
                    for child in children:
                        arr = render_element_to_array(child, edited_data, width, height, is_text_editable=True)
                        if arr is not None:
                            pil_elem = PILImage.fromarray(arr)
                            img.paste(pil_elem, (0, 0), pil_elem)
                    
                    result = img.convert('RGB')
                    st.image(result, use_container_width=True)
                    
                    buf = io.BytesIO()
                    result.save(buf, format='PNG')
                    st.download_button("⬇️ Download PNG", buf.getvalue(),
                                     file_name="output.png", mime="image/png")
            
            else:  # Video
                progress_bar = st.progress(0)
                status = st.empty()
                
                with st.spinner("Rendering video..."):
                    status.text("Generating frames...")
                    clip = render_video_optimized(template_data, edited_data, fps, progress_bar)
                    
                    if clip:
                        status.text("Encoding video...")
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                            tmp_path = tmp.name
                        
                        # Quality settings
                        preset = 'ultrafast' if quality == "Fast" else 'medium' if quality == "Balanced" else 'slow'
                        
                        try:
                            clip.write_videofile(tmp_path, codec='libx264', audio=False, 
                                               logger=None, preset=preset, threads=4)
                        except:
                            clip.write_videofile(tmp_path, codec='libx264', audio=False, verbose=False)
                        
                        with open(tmp_path, 'rb') as f:
                            video_bytes = f.read()
                        
                        status.empty()
                        st.video(video_bytes)
                        st.download_button("⬇️ Download MP4", video_bytes,
                                         file_name="output.mp4", mime="video/mp4")
                        os.unlink(tmp_path)

if __name__ == "__main__":
    main()
