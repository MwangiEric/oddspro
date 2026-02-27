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

# ============== CACHE & UTILS ==============

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

def hex_to_rgba(color_str):
    """Convert color formats to RGBA."""
    if not color_str:
        return (255, 255, 255, 255)
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
    return (255, 255, 255, 255)

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

def is_image_variable(var_name):
    """Check if variable is an image variable."""
    return var_name.startswith('image') and var_name[5:].isdigit()

# ============== RENDERING ==============

def render_svg_element(draw, element):
    """Render SVG rectangle."""
    x = element.get('x', 0)
    y = element.get('y', 0)
    width = element.get('width', 100)
    height = element.get('height', 100)
    
    colors_replace = element.get('colorsReplace', {})
    fill_color = (0, 161, 255, 255)  # Default blue
    
    if colors_replace:
        for old_color, new_color in colors_replace.items():
            fill_color = hex_to_rgba(new_color)
    
    draw.rectangle([x, y, x + width, y + height], fill=fill_color[:3])

def render_element_to_pil(element, data, canvas_width, canvas_height):
    """Render single element to PIL Image (RGBA)."""
    x = int(element.get('x', 0))
    y = int(element.get('y', 0))
    w = int(element.get('width', 100))
    h = int(element.get('height', 100))
    
    # Create full canvas size image for this element
    img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
    
    elem_type = element.get('type')
    
    if elem_type == 'svg':
        draw = ImageDraw.Draw(img)
        render_svg_element(draw, element)
    
    elif elem_type == 'image':
        name = element.get('name', '')
        src = element.get('src', '')
        
        img_to_render = None
        
        # Check if it's a template variable
        if name and '{{' in name:
            var_name = name.replace('{{', '').replace('}}', '')
            img_url = data.get(var_name)
            if img_url:
                img_to_render = load_image_from_url(img_url)
        else:
            # Direct URL
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
        
        # Replace variables
        for var in extract_variables(template_text):
            value = data.get(var, '')
            template_text = template_text.replace(f'{{{var}}}', str(value))
        
        if not template_text.strip():
            return None
        
        font_size = element.get('fontSize', 20)
        font_family = element.get('fontFamily', 'Roboto')
        fill = hex_to_rgba(element.get('fill', 'rgba(0,0,0,1)'))
        align = element.get('align', 'left')
        
        font = get_font(int(font_size), font_family)
        
        # Calculate text position
        try:
            bbox = draw.textbbox((0, 0), template_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width, text_height = draw.textsize(template_text, font=font)
        
        if align == 'center':
            text_x = x + (w - text_width) / 2
        elif align == 'right':
            text_x = x + w - text_width
        else:
            text_x = x
        
        text_y = y + (h - text_height) / 2
        
        draw.text((text_x, text_y), template_text, fill=fill[:3], font=font)
    
    return img

def composite_layers(layers, bg_color, width, height):
    """Composite multiple PIL layers using alpha blending."""
    # Start with background
    result = Image.new('RGBA', (width, height), bg_color)
    
    for layer in layers:
        if layer is not None:
            # Alpha composite
            result = Image.alpha_composite(result, layer)
    
    return result

def render_static_image(template_data, data):
    """Render static PNG."""
    width = int(template_data.get('width', 1080))
    height = int(template_data.get('height', 1080))
    
    pages = template_data.get('pages', [])
    if not pages:
        return None
    
    page = pages[0]
    bg_color = hex_to_rgba(page.get('background', 'rgba(255,255,255,1)'))
    
    children = page.get('children', [])
    
    # Render all layers
    layers = []
    for child in children:
        layer = render_element_to_pil(child, data, width, height)
        if layer:
            layers.append(layer)
    
    # Composite
    result = composite_layers(layers, bg_color, width, height)
    return result.convert('RGB')

def parse_animations(element):
    """Parse enabled animations."""
    animations = element.get('animations', [])
    enabled = []
    for anim in animations:
        if anim.get('enabled', False):
            enabled.append({
                'type': anim.get('type'),  # enter, exit, loop
                'name': anim.get('name'),   # fade, zoom, blink
                'delay': anim.get('delay', 0) / 1000,
                'duration': anim.get('duration', 500) / 1000,
            })
    return enabled

def apply_animation_to_layer(layer, element, anim, progress, width, height):
    """Apply animation effect to a layer."""
    if layer is None:
        return None
    
    anim_name = anim['name']
    anim_type = anim['type']
    
    x = int(element.get('x', 0))
    y = int(element.get('y', 0))
    w = int(element.get('width', 100))
    h = int(element.get('height', 100))
    
    # Crop to element bounds for processing
    elem_region = layer.crop((x, y, x + w, y + h))
    
    if anim_name == 'fade':
        if anim_type == 'enter':
            alpha = int(progress * 255)
        elif anim_type == 'exit':
            alpha = int((1 - progress) * 255)
        else:  # loop
            alpha = int((0.5 + 0.5 * np.sin(progress * 2 * np.pi)) * 255)
        
        # Apply alpha
        r, g, b, a = elem_region.split()
        a = a.point(lambda i: int(i * alpha / 255))
        elem_region = Image.merge('RGBA', (r, g, b, a))
    
    elif anim_name == 'zoom':
        if anim_type == 'enter':
            scale = 0.5 + 0.5 * progress
        elif anim_type == 'exit':
            scale = 1.0 - 0.5 * progress
        else:  # loop
            scale = 1.0 + 0.1 * np.sin(progress * 2 * np.pi)
        
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        
        # Resize
        zoomed = elem_region.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create new region with original size, paste centered
        new_region = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        offset_x = (new_w - w) // 2
        offset_y = (new_h - h) // 2
        
        paste_x = max(0, -offset_x)
        paste_y = max(0, -offset_y)
        crop_x = max(0, offset_x)
        crop_y = max(0, offset_y)
        
        crop_w = min(w, new_w - crop_x)
        crop_h = min(h, new_h - crop_y)
        
        if crop_w > 0 and crop_h > 0:
            cropped = zoomed.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
            new_region.paste(cropped, (paste_x, paste_y))
        
        elem_region = new_region
    
    elif anim_name == 'blink':
        alpha = int((0.5 + 0.5 * np.sin(progress * 2 * np.pi)) * 255)
        r, g, b, a = elem_region.split()
        a = a.point(lambda i: int(i * alpha / 255))
        elem_region = Image.merge('RGBA', (r, g, b, a))
    
    # Paste back to full canvas
    result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    result.paste(elem_region, (x, y))
    
    return result

def render_video(template_data, data, fps=30, progress_callback=None):
    """Render video with animations."""
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
    
    # Separate static and animated
    static_children = []
    animated_children = []  # (child, animations, pre_rendered_layer)
    
    for child in children:
        anims = parse_animations(child)
        if anims:
            # Pre-render the layer
            layer = render_element_to_pil(child, data, width, height)
            animated_children.append((child, anims, layer))
        else:
            static_children.append(child)
    
    # Pre-render static composite
    static_layers = []
    for child in static_children:
        layer = render_element_to_pil(child, data, width, height)
        if layer:
            static_layers.append(layer)
    
    # Generate frames
    frames = []
    
    for frame_idx in range(total_frames):
        time = frame_idx / fps
        
        # Start with background + static
        frame = composite_layers(static_layers, bg_color, width, height)
        
        # Add animated elements
        for child, anims, layer in animated_children:
            if layer is None:
                continue
            
            # Find which animation applies
            current_layer = None
            
            for anim in anims:
                delay = anim['delay']
                duration = anim['duration']
                anim_type = anim['type']
                
                if anim_type in ['enter', 'exit']:
                    if delay <= time <= delay + duration:
                        progress = (time - delay) / duration
                        current_layer = apply_animation_to_layer(layer, child, anim, progress, width, height)
                        break
                    elif time > delay + duration and anim_type == 'enter':
                        current_layer = layer  # Fully visible after enter
                        break
                    elif time < delay and anim_type == 'exit':
                        current_layer = layer  # Fully visible before exit
                        break
                else:  # loop
                    if time >= delay:
                        loop_time = (time - delay) % duration
                        progress = loop_time / duration
                        current_layer = apply_animation_to_layer(layer, child, anim, progress, width, height)
                    else:
                        current_layer = layer
                    break
            
            if current_layer is None:
                current_layer = layer
            
            # Composite onto frame
            frame = Image.alpha_composite(frame, current_layer)
        
        # Convert to RGB for video
        frames.append(np.array(frame.convert('RGB')))
        
        if progress_callback and frame_idx % 5 == 0:
            progress_callback(frame_idx / total_frames)
    
    if progress_callback:
        progress_callback(1.0)
    
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
    """Analyze template for variables."""
    variables = {}
    has_animations = False
    
    pages = template_data.get('pages', [])
    duration = pages[0].get('duration', 5000) / 1000 if pages else 5
    
    for page in pages:
        for child in page.get('children', []):
            name = child.get('name', '')
            
            if name and '{{' in name:
                var = name.replace('{{', '').replace('}}', '')
                variables[var] = {
                    'is_image': is_image_variable(var),
                    'type': child.get('type')
                }
            
            if child.get('animations'):
                if any(a.get('enabled') for a in child.get('animations', [])):
                    has_animations = True
    
    return variables, has_animations, duration

# ============== UI ==============

def main():
    st.title("🎬 Polotno Template Renderer")
    
    # Initialize session state
    if 'data' not in st.session_state:
        st.session_state.data = {}
    
    with st.sidebar:
        st.header("📁 Upload")
        
        template_file = st.file_uploader("Template JSON", type=['json'])
        template_json = st.text_area("Or paste JSON", height=100)
        
        # Parse template
        template_data = None
        if template_file:
            try:
                template_data = json.load(template_file)
            except:
                st.error("Invalid JSON")
        elif template_json:
            try:
                template_data = json.loads(template_json)
            except:
                st.error("Invalid JSON")
        
        if template_data:
            st.success(f"Template loaded: {template_data.get('width', 0)}×{template_data.get('height', 0)}")
        
        st.divider()
        
        # Data input method
        input_method = st.radio("Data Source", ["Manual Entry", "JSON Feed"])
        
        if input_method == "JSON Feed":
            feed_url = st.text_input(
                "Feed URL",
                value="https://myrhub.vercel.app/kenyatronics/view/xiaomi-redmi-note-15-pro-5g-8gb-ram-256gb-rom-683-inch-amoled-display-200mp-camera?format=json"
            )
            if st.button("Load from Feed", use_container_width=True):
                with st.spinner("Loading..."):
                    try:
                        response = requests.get(feed_url, timeout=10)
                        data = response.json()
                        if data.get('items'):
                            content = json.loads(data['items'][0]['content_html'])
                            # Build data dict
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
                            st.success("Loaded!")
                    except Exception as e:
                        st.error(f"Failed: {e}")
        
        st.divider()
        
        st.header("⚙️ Output")
        output_type = st.radio("Type", ["PNG Image", "MP4 Video"])
        
        if output_type == "MP4 Video":
            fps = st.slider("FPS", 15, 60, 30)
        
        generate_btn = st.button("🚀 Generate", type="primary", use_container_width=True)
    
    # Main area
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📝 Variables")
        
        if template_data:
            variables, has_animations, duration = analyze_template(template_data)
            
            if has_animations:
                st.info(f"⏱️ Duration: {duration:.1f}s")
            
            # Show editable fields
            for var, info in variables.items():
                current = st.session_state.data.get(var, '')
                
                if info['is_image']:
                    st.text(f"{{{var}}}")
                    if current:
                        st.image(current, width=150)
                        st.session_state.data[var] = current
                    else:
                        url = st.text_input(f"URL for {var}", key=f"img_{var}")
                        if url:
                            st.session_state.data[var] = url
                else:
                    new_val = st.text_input(
                        f"{{{var}}}",
                        value=str(current),
                        key=f"txt_{var}"
                    )
                    st.session_state.data[var] = new_val
            
            if not variables:
                st.info("No template variables found")
        else:
            st.info("Upload a template to see variables")
    
    with col2:
        st.subheader("🖼️ Preview")
        
        if template_data and generate_btn:
            data = st.session_state.data
            
            if output_type == "PNG Image":
                with st.spinner("Rendering..."):
                    result = render_static_image(template_data, data)
                    
                    if result:
                        st.image(result, use_container_width=True)
                        
                        buf = io.BytesIO()
                        result.save(buf, format='PNG')
                        st.download_button(
                            "⬇️ Download PNG",
                            buf.getvalue(),
                            file_name="poster.png",
                            mime="image/png"
                        )
            
            else:  # Video
                progress_bar = st.progress(0.0)
                status = st.empty()
                
                with st.spinner("Rendering video..."):
                    def update_progress(p):
                        progress_bar.progress(min(1.0, p))
                    
                    clip = render_video(template_data, data, fps, update_progress)
                    
                    if clip:
                        status.text("Encoding...")
                        
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                            tmp_path = tmp.name
                        
                        try:
                            clip.write_videofile(tmp_path, codec='libx264', audio=False, 
                                               logger=None, preset='fast', threads=4)
                        except:
                            clip.write_videofile(tmp_path, codec='libx264', audio=False, verbose=False)
                        
                        with open(tmp_path, 'rb') as f:
                            video_bytes = f.read()
                        
                        progress_bar.empty()
                        status.empty()
                        
                        st.video(video_bytes)
                        st.download_button(
                            "⬇️ Download MP4",
                            video_bytes,
                            file_name="video.mp4",
                            mime="video/mp4"
                        )
                        
                        os.unlink(tmp_path)

if __name__ == "__main__":
    main()
