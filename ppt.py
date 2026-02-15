import streamlit as st
import os
import tempfile
import numpy as np
import cv2
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import math
import re
import zipfile
import shutil
from io import BytesIO

st.set_page_config(page_title="PPTX Video Factory", layout="wide")

LAYOUTS = {
    "Original PPTX Size": None,
    "Landscape (16:9) 1920x1080": {"w": 1920, "h": 1080},
    "Portrait (9:16) 1080x1920": {"w": 1080, "h": 1920},
    "Square (1:1) 1080x1080": {"w": 1080, "h": 1080},
}

ANIMATION_STYLES = {
    "None": None,
    "Fade In": "fade_in",
    "Fade Out": "fade_out",
    "Slide Left": "slide_left",
    "Slide Right": "slide_right",
    "Slide Up": "slide_up",
    "Slide Down": "slide_down",
    "Scale Up": "scale_up",
    "Scale Down": "scale_down",
    "Bounce": "bounce",
    "Rotate": "rotate",
}

EASING_FUNCTIONS = {
    "Linear": lambda t: t,
    "Ease In": lambda t: t * t,
    "Ease Out": lambda t: 1 - (1 - t) * (1 - t),
    "Ease In Out": lambda t: 2*t*t if t < 0.5 else 1 - math.pow(-2*t + 2, 2) / 2,
    "Bounce": lambda t: 4*t*(1-t) if t < 0.5 else 1 - 4*(t-0.5)*(t-0.5),
}

def find_font():
    candidates = [
        "poppins.ttf", "Poppins.ttf", "Poppins-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for f in candidates:
        if os.path.exists(f):
            try:
                ImageFont.truetype(f, 40)
                return f
            except:
                continue
    return None

def get_images_from_folder(folder_path):
    """Get all images from a folder."""
    folder = Path(folder_path)
    if not folder.exists():
        return {}
    
    extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif']
    images = {}
    
    for ext in extensions:
        for f in folder.glob(f"*{ext}"):
            images[f.name] = str(f)
    
    return images

def extract_media_from_pptx(pptx_path, extract_dir):
    """Extract media folder from PPTX to directory."""
    media_dir = Path(extract_dir) / "ppt" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with zipfile.ZipFile(pptx_path, 'r') as zf:
            for name in zf.namelist():
                if name.startswith('ppt/media/'):
                    zf.extract(name, extract_dir)
        return str(media_dir)
    except Exception as e:
        st.error(f"Error extracting media: {e}")
        return None

def find_best_match(query_name, query_id, available_images):
    """Find best matching image using both name and ID."""
    if not available_images or not query_name:
        return None
    
    query_name_clean = query_name.lower().replace(' ', '').replace('_', '').replace('-', '')
    query_id_clean = query_id.lower().replace(' ', '').replace('_', '').replace('-', '') if query_id else ""
    
    best_match = None
    best_score = 0
    
    for img_name, img_path in available_images.items():
        img_clean = img_name.lower().replace(' ', '').replace('_', '').replace('-', '')
        score = 0
        
        # Exact match with name
        if query_name_clean == img_clean:
            score = 100
        # Name contains image name or vice versa
        elif query_name_clean in img_clean or img_clean in query_name_clean:
            score = 80
        
        # Check ID match if name didn't match well
        if score < 80 and query_id_clean:
            if query_id_clean == img_clean:
                score = 90
            elif query_id_clean in img_clean or img_clean in query_id_clean:
                score = 70
        
        # Partial word matching
        if score < 70:
            name_words = set(re.findall(r'[a-z]+', query_name_clean))
            img_words = set(re.findall(r'[a-z]+', img_clean))
            common = name_words & img_words
            if common:
                score = len(common) * 10
        
        # Number matching
        if score < 50:
            name_nums = set(re.findall(r'\d+', query_name_clean))
            id_nums = set(re.findall(r'\d+', query_id_clean))
            img_nums = set(re.findall(r'\d+', img_clean))
            if name_nums & img_nums or id_nums & img_nums:
                score = 40
        
        if score > best_score:
            best_score = score
            best_match = img_path
    
    return best_match if best_score >= 30 else None

def get_shape_identifier(shape):
    """Get best identifier for matching - name and alt text."""
    name = shape.name
    
    # Try to get alt text (original filename when inserted)
    alt_text = None
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        try:
            alt_text = shape._pic.nvPicPr.cNvPr.get('descr')
            # Clean up alt text - remove path, keep filename
            if alt_text:
                alt_text = Path(alt_text).stem
        except:
            pass
    
    return {
        'name': name,
        'alt_text': alt_text,
        'id': getattr(shape, 'shape_id', None)
    }

def extract_background(slide):
    try:
        fill = slide.background.fill
        if fill.type is not None:
            if hasattr(fill.fore_color, 'rgb') and fill.fore_color.rgb:
                rgb = fill.fore_color.rgb
                return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except:
        pass
    return (255, 255, 255)

def harvest_ppt(pptx_path, target_dims=None, asset_sources=None, manual_mappings=None):
    """
    Extract PPT with multiple asset sources.
    asset_sources: dict with 'folder', 'extracted_media', 'uploaded' keys
    """
    try:
        prs = Presentation(pptx_path)
        if not prs.slides:
            return None
        
        slide = prs.slides[0]
        emu_to_px = 96 / 914400
        
        orig_w = int(prs.slide_width * emu_to_px)
        orig_h = int(prs.slide_height * emu_to_px)
        
        if target_dims:
            target_w, target_h = target_dims['w'], target_dims['h']
            scale = max(target_w / orig_w, target_h / orig_h)
            scaled_w = int(orig_w * scale)
            scaled_h = int(orig_h * scale)
            offset_x = (target_w - scaled_w) // 2
            offset_y = (target_h - scaled_h) // 2
            canvas_w, canvas_h = target_w, target_h
        else:
            canvas_w, canvas_h = orig_w, orig_h
            scale = 1.0
            offset_x, offset_y = 0, 0
        
        bg_color = extract_background(slide)
        
        # Combine all asset sources
        all_images = {}
        source_info = {}
        
        if asset_sources:
            # Priority: uploaded > extracted_media > folder
            for source_name in ['folder', 'extracted_media', 'uploaded']:
                if source_name in asset_sources and asset_sources[source_name]:
                    imgs = get_images_from_folder(asset_sources[source_name]) if isinstance(asset_sources[source_name], (str, Path)) else asset_sources[source_name]
                    for img_name, img_path in imgs.items():
                        if img_name not in all_images:
                            all_images[img_name] = img_path
                            source_info[img_name] = source_name
        
        config = {
            "canvas": {"w": canvas_w, "h": canvas_h},
            "original": {"w": orig_w, "h": orig_h},
            "scale": scale,
            "offset": {"x": offset_x, "y": offset_y},
            "pptx_background": bg_color,
            "asset_sources": asset_sources,
            "available_images": list(all_images.keys()),
            "elements": []
        }
        
        def process_shape(shape, parent_x=0, parent_y=0):
            identifiers = get_shape_identifier(shape)
            original_id = identifiers['name']  # Use name as ID (user-editable in PowerPoint)
            display_name = original_id
            
            x = int((shape.left * emu_to_px * scale) + offset_x + parent_x)
            y = int((shape.top * emu_to_px * scale) + offset_y + parent_y)
            w = int(shape.width * emu_to_px * scale)
            h = int(shape.height * emu_to_px * scale)
            
            el = {
                "id": original_id,
                "name": display_name,
                "alt_text": identifiers.get('alt_text'),
                "x": x, "y": y, "w": w, "h": h,
                "rotation": getattr(shape, 'rotation', 0) or 0,
                "z_order": getattr(shape, 'z_order', 0) or 0,
            }
            
            if shape.has_text_frame and shape.text.strip():
                para = shape.text_frame.paragraphs[0]
                run = para.runs[0] if para.runs else None
                
                el.update({
                    "type": "text",
                    "text_default": shape.text,
                    "size": max(int((run.font.size.pt if run and run.font.size else 24) * scale), 8),
                    "color": f"#{run.font.color.rgb}" if run and run.font.color.rgb else "#000000",
                    "bold": bool(run.font.bold) if run else False,
                })
                return el
            
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                el["type"] = "image"
                
                # Try manual mapping first
                if manual_mappings and original_id in manual_mappings:
                    el["image_path"] = manual_mappings[original_id]
                    el["match_source"] = "manual"
                else:
                    # Try matching by name first, then alt_text
                    matched = find_best_match(display_name, identifiers.get('alt_text'), all_images)
                    
                    # If no match by name, try alt_text as primary
                    if not matched and identifiers.get('alt_text'):
                        matched = find_best_match(identifiers['alt_text'], display_name, all_images)
                    
                    if matched:
                        el["image_path"] = matched
                        el["match_source"] = source_info.get(Path(matched).name, "unknown")
                
                return el
            
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                children = []
                for child in shape.shapes:
                    child_el = process_shape(child, parent_x=x - offset_x, parent_y=y - offset_y)
                    if child_el:
                        children.append(child_el)
                return children
            
            el["type"] = "shape"
            
            # Check if this shape should be treated as image (manual or auto-match)
            if manual_mappings and original_id in manual_mappings:
                el["type"] = "image"
                el["image_path"] = manual_mappings[original_id]
                el["match_source"] = "manual"
                return el
            
            # Auto-convert shapes with matching image names
            matched = find_best_match(display_name, None, all_images)
            if not matched and identifiers.get('alt_text'):
                matched = find_best_match(identifiers['alt_text'], None, all_images)
            
            if matched:
                el["type"] = "image"
                el["image_path"] = matched
                el["match_source"] = source_info.get(Path(matched).name, "auto")
                return el
            
            # Shape styling
            try:
                if hasattr(shape, 'fill') and shape.fill.type == 1:
                    if hasattr(shape.fill.fore_color, 'rgb') and shape.fill.fore_color.rgb:
                        rgb = shape.fill.fore_color.rgb
                        el["fill_color"] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            except:
                pass
            
            try:
                if shape.has_line and shape.line.color.rgb:
                    rgb = shape.line.color.rgb
                    el["line_color"] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
                    el["line_width"] = int(shape.line.width.pt * scale) if shape.line.width else 1
            except:
                pass
            
            return el
        
        for shape in slide.shapes:
            result = process_shape(shape)
            if isinstance(result, list):
                config["elements"].extend(result)
            elif result:
                config["elements"].append(result)
        
        config["elements"].sort(key=lambda x: x.get('z_order', 0))
        
        return config
        
    except Exception as e:
        st.error(f"Extraction failed: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def render_text(text, box_w, box_h, font_size, color, font_path):
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
    
    words = text.split()
    lines = []
    current = []
    
    for word in words:
        test = ' '.join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= box_w:
            current.append(word)
        else:
            if current:
                lines.append(' '.join(current))
            current = [word]
    if current:
        lines.append(' '.join(current))
    
    if not lines:
        lines = [text]
    
    line_h = font_size * 1.2
    total_h = len(lines) * line_h
    y = (box_h - total_h) // 2
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (box_w - line_w) // 2
        draw.text((x, y - bbox[1]), line, fill=color, font=font)
        y += line_h
    
    return np.array(img)

def apply_animation(element, progress, anim_config):
    """Apply animation transformation based on progress (0-1)."""
    if not anim_config or anim_config.get('style') == 'None':
        return element
    
    style = anim_config.get('style')
    easing = EASING_FUNCTIONS.get(anim_config.get('easing', 'Ease Out'), EASING_FUNCTIONS['Ease Out'])
    t = easing(progress)
    
    x, y = element['x'], element['y']
    w, h = element['w'], element['h']
    
    if style == 'fade_in':
        alpha = t
        return {**element, 'alpha': alpha, 'x': x, 'y': y}
    
    elif style == 'fade_out':
        alpha = 1 - t
        return {**element, 'alpha': alpha, 'x': x, 'y': y}
    
    elif style == 'slide_left':
        offset = int(w * (1 - t))
        return {**element, 'x': x - offset, 'y': y}
    
    elif style == 'slide_right':
        offset = int(w * (1 - t))
        return {**element, 'x': x + offset, 'y': y}
    
    elif style == 'slide_up':
        offset = int(h * (1 - t))
        return {**element, 'x': x, 'y': y - offset}
    
    elif style == 'slide_down':
        offset = int(h * (1 - t))
        return {**element, 'x': x, 'y': y + offset}
    
    elif style == 'scale_up':
        scale = 0.5 + 0.5 * t
        new_w = int(w * scale)
        new_h = int(h * scale)
        new_x = x + (w - new_w) // 2
        new_y = y + (h - new_h) // 2
        return {**element, 'x': new_x, 'y': new_y, 'w': new_w, 'h': new_h}
    
    elif style == 'scale_down':
        scale = 1.5 - 0.5 * t
        new_w = int(w * scale)
        new_h = int(h * scale)
        new_x = x + (w - new_w) // 2
        new_y = y + (h - new_h) // 2
        return {**element, 'x': new_x, 'y': new_y, 'w': new_w, 'h': new_h}
    
    elif style == 'bounce':
        bounce = math.sin(t * math.pi) * 0.3 * (1 - t)
        return {**element, 'y': y - int(h * bounce)}
    
    elif style == 'rotate':
        angle = 360 * (1 - t)
        return {**element, 'rotation': angle}
    
    return element

def render_frame(layout, user_data, font_path, bg_settings, anim_settings=None, frame_time=0, total_duration=5):
    w, h = layout['canvas']['w'], layout['canvas']['h']
    
    bg_type = bg_settings.get('type', 'pptx')
    bg_value = bg_settings.get('value')
    
    if bg_type == 'image' and isinstance(bg_value, Image.Image):
        frame = np.array(bg_value.resize((w, h), Image.Resampling.LANCZOS))
    elif bg_type == 'color' and isinstance(bg_value, tuple):
        frame = np.full((h, w, 3), bg_value, dtype=np.uint8)
    elif bg_type == 'pptx':
        frame = np.full((h, w, 3), layout['pptx_background'], dtype=np.uint8)
    else:
        frame = np.full((h, w, 3), (245, 245, 245), dtype=np.uint8)
    
    pil_img = Image.fromarray(frame)
    draw = ImageDraw.Draw(pil_img)
    
    text_layers = []
    
    for el in layout['elements']:
        original_el = el.copy()
        
        # Apply animation if configured
        if anim_settings and el['id'] in anim_settings:
            anim_config = anim_settings[el['id']]
            delay = anim_config.get('delay', 0)
            duration = anim_config.get('duration', 1.0)
            
            if frame_time >= delay:
                anim_progress = min((frame_time - delay) / duration, 1.0) if duration > 0 else 1.0
                el = apply_animation(el, anim_progress, anim_config)
        
        x, y, ew, eh = el['x'], el['y'], el['w'], el['h']
        alpha = el.get('alpha', 1.0)
        
        if x < -ew or y < -eh or x >= w or y >= h or alpha <= 0:
            continue
        
        if el['type'] == 'shape':
            fill = el.get('fill_color', (200, 200, 200))
            line = el.get('line_color', (100, 100, 100))
            line_w = el.get('line_width', 1)
            
            if not isinstance(fill, tuple):
                fill = (200, 200, 200)
            if not isinstance(line, tuple):
                line = (100, 100, 100)
            
            if alpha < 1.0:
                fill = tuple(int(c * alpha + 255 * (1 - alpha)) for c in fill)
            
            draw.rectangle([x, y, x+ew, y+eh], fill=fill, outline=line, width=max(line_w, 1))
        
        elif el['type'] == 'image':
            img_path = el.get('image_path')
            
            if img_path and Path(img_path).exists():
                try:
                    asset_img = Image.open(img_path).convert('RGBA')
                    asset_img = asset_img.resize((ew, eh), Image.Resampling.LANCZOS)
                    
                    if alpha < 1.0:
                        arr = np.array(asset_img)
                        arr[:, :, 3] = (arr[:, :, 3] * alpha).astype(np.uint8)
                        asset_img = Image.fromarray(arr)
                    
                    pil_img.paste(asset_img, (x, y), asset_img)
                except Exception as e:
                    print(f"Image error: {e}")
                    draw.rectangle([x, y, x+ew, y+eh], fill=(255, 0, 0))
                    draw.text((x+5, y+5), "ERR", fill=(255, 255, 255))
            else:
                draw.rectangle([x, y, x+ew, y+eh], fill=(150, 150, 150), outline=(100, 100, 100))
                draw.text((x+5, y+5), f"No img\n{el['id'][:10]}", fill=(50, 50, 50))
        
        elif el['type'] == 'text':
            text = user_data.get(el['id'], el.get('text_default', ''))
            if text.strip():
                hex_color = el['color'].lstrip('#')
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                text_layers.append({
                    'x': x, 'y': y, 'w': ew, 'h': eh,
                    'text': text, 'size': el['size'], 'color': rgb,
                    'alpha': alpha
                })
    
    frame = np.array(pil_img)
    
    for t in text_layers:
        text_array = render_text(t['text'], t['w'], t['h'], t['size'], t['color'] + (int(255 * t.get('alpha', 1.0)),), font_path)
        
        x, y, ew, eh = t['x'], t['y'], t['w'], t['h']
        
        if x < 0 or y < 0 or x + ew > w or y + eh > h:
            continue
        
        alpha = text_array[:, :, 3:4].astype(np.float32) / 255.0
        rgb_layer = text_array[:, :, :3].astype(np.float32)
        roi = frame[y:y+eh, x:x+ew].astype(np.float32)
        
        blended = (rgb_layer * alpha + roi * (1 - alpha)).astype(np.uint8)
        frame[y:y+eh, x:x+ew] = blended
    
    return frame

def encode_video(frames, fps, output_path):
    h, w = frames[0].shape[:2]
    for codec in ['mp4v', 'avc1']:
        try:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            if writer.isOpened():
                for frame in frames:
                    writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                writer.release()
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    return True
        except:
            continue
    return False

def main():
    st.title("🏭 PPTX Video Factory")
    st.caption("Auto-discover assets from template folders + manual upload fallback")
    
    defaults = {
        'layout': None,
        'user_data': {},
        'font_path': find_font(),
        'bg_settings': {'type': 'pptx', 'value': None},
        'asset_sources': {},  # 'folder', 'extracted_media', 'uploaded'
        'manual_mappings': {},
        'pptx_path': None,
        'pptx_name': None,
        'templates_dir': "templates",
        'templates': {},
        'current_template': None,
        'anim_settings': {},
        'selected_element': None,
        'uploaded_images': {},  # Store uploaded images: {filename: temp_path}
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    
    with st.sidebar:
        st.header("1. Format")
        layout_name = st.selectbox("Size", list(LAYOUTS.keys()))
        target = LAYOUTS[layout_name]
        
        st.divider()
        st.header("2. Templates Directory")
        templates_dir = st.text_input("Templates folder", value=st.session_state.templates_dir)
        st.session_state.templates_dir = templates_dir
        
        st.divider()
        st.header("3. Upload PPTX")
        uploaded = st.file_uploader("PPTX file", type=['pptx'])
        
        if uploaded and st.button("Extract & Auto-Discover"):
            # Get PPTX name without extension
            pptx_name = Path(uploaded.name).stem
            st.session_state.pptx_name = pptx_name
            
            # Create temp dir for extraction
            extract_dir = Path(tempfile.gettempdir()) / f"pptx_{hashlib.md5(uploaded.getvalue()).hexdigest()[:8]}"
            extract_dir.mkdir(exist_ok=True)
            
            tmp_path = extract_dir / "presentation.pptx"
            with open(tmp_path, 'wb') as f:
                f.write(uploaded.getvalue())
            
            st.session_state.pptx_path = str(tmp_path)
            
            # AUTO-DISCOVERY: Look for templates/pptx_name/ppt/media/
            auto_discovered = None
            if templates_dir:
                expected_media_path = Path(templates_dir) / pptx_name / "ppt" / "media"
                if expected_media_path.exists():
                    auto_discovered = str(expected_media_path)
                    st.success(f"✓ Auto-discovered: {expected_media_path}")
                else:
                    st.info(f"ℹ️ No auto-discovery folder at {expected_media_path}")
            
            # Also extract media from PPTX itself as fallback
            extracted_media = extract_media_from_pptx(str(tmp_path), extract_dir)
            
            # Set up asset sources
            st.session_state.asset_sources = {
                'folder': auto_discovered,
                'extracted_media': extracted_media,
                'uploaded': st.session_state.uploaded_images
            }
            
            # Extract layout
            layout = harvest_ppt(
                str(tmp_path), 
                target, 
                st.session_state.asset_sources,
                st.session_state.manual_mappings
            )
            
            if layout:
                st.session_state.layout = layout
                st.session_state.user_data = {
                    el['id']: el.get('text_default', '')
                    for el in layout['elements']
                    if el.get('type') == 'text'
                }
                st.session_state.bg_settings = {'type': 'pptx', 'value': None}
                
                matched = sum(1 for e in layout['elements'] if e.get('image_path'))
                st.success(f"Loaded {len(layout['elements'])} elements, {matched} images matched")
                st.rerun()
        
        # UPLOAD FALLBACK
        if st.session_state.layout:
            st.divider()
            st.header("📤 Upload Images (Fallback)")
            st.caption("Upload images if auto-discovery didn't find them")
            
            uploaded_imgs = st.file_uploader(
                "Upload images", 
                type=['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'],
                accept_multiple_files=True
            )
            
            if uploaded_imgs:
                for img_file in uploaded_imgs:
                    if img_file.name not in st.session_state.uploaded_images:
                        # Save to temp
                        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=Path(img_file.name).suffix)
                        temp_path.write(img_file.getvalue())
                        temp_path.close()
                        st.session_state.uploaded_images[img_file.name] = temp_path.name
                
                # Update asset sources
                st.session_state.asset_sources['uploaded'] = st.session_state.uploaded_images
                
                # Re-extract with new images
                if st.button("Re-match with uploaded images"):
                    layout = harvest_ppt(
                        st.session_state.pptx_path,
                        target,
                        st.session_state.asset_sources,
                        st.session_state.manual_mappings
                    )
                    st.session_state.layout = layout
                    st.success(f"Rematched with {len(st.session_state.uploaded_images)} uploaded images")
                    st.rerun()
        
        if st.session_state.layout:
            layout = st.session_state.layout
            
            st.divider()
            st.header("📊 Stats")
            st.metric("Canvas", f"{layout['canvas']['w']}x{layout['canvas']['h']}")
            
            shapes = sum(1 for e in layout['elements'] if e['type'] == 'shape')
            texts = sum(1 for e in layout['elements'] if e['type'] == 'text')
            images = sum(1 for e in layout['elements'] if e['type'] == 'image')
            mapped = sum(1 for e in layout['elements'] if e.get('image_path'))
            
            st.metric("Shapes", shapes)
            st.metric("Text", texts)
            st.metric(f"Images {mapped}/{images}", images)
            
            # Show asset sources
            with st.expander("Asset Sources"):
                for source, path in st.session_state.asset_sources.items():
                    if path:
                        if isinstance(path, dict):
                            st.text(f"{source}: {len(path)} files")
                        else:
                            st.text(f"{source}: {path}")
            
            # TEMPLATE MANAGEMENT
            st.divider()
            st.header("🎨 Save Template")
            
            template_names = list(st.session_state.templates.keys())
            selected_template = st.selectbox(
                "Load Template",
                ["(Current)"] + template_names,
                key="template_selector"
            )
            
            if selected_template != "(Current)" and selected_template in st.session_state.templates:
                if st.button("Load"):
                    template_data = st.session_state.templates[selected_template]
                    st.session_state.manual_mappings = template_data.get('mappings', {})
                    st.session_state.bg_settings = template_data.get('bg', {'type': 'pptx', 'value': None})
                    st.session_state.anim_settings = template_data.get('animations', {})
                    layout = harvest_ppt(
                        st.session_state.pptx_path,
                        target,
                        st.session_state.asset_sources,
                        st.session_state.manual_mappings
                    )
                    st.session_state.layout = layout
                    st.session_state.current_template = selected_template
                    st.success(f"Loaded: {selected_template}")
                    st.rerun()
            
            new_template_name = st.text_input("Save As", value=st.session_state.current_template or st.session_state.pptx_name or "")
            if st.button("Save Current") and new_template_name:
                st.session_state.templates[new_template_name] = {
                    'mappings': st.session_state.manual_mappings.copy(),
                    'bg': st.session_state.bg_settings.copy(),
                    'animations': st.session_state.anim_settings.copy(),
                    'pptx_name': st.session_state.pptx_name,
                    'asset_sources': st.session_state.asset_sources
                }
                st.session_state.current_template = new_template_name
                st.success(f"Saved: {new_template_name}")
                st.rerun()
            
            # ELEMENT MAPPING
            st.divider()
            st.header("🎯 Element Images")
            st.caption("Manual override if auto-match failed")
            
            all_images = {}
            if st.session_state.asset_sources.get('folder'):
                all_images.update(get_images_from_folder(st.session_state.asset_sources['folder']))
            if st.session_state.asset_sources.get('extracted_media'):
                all_images.update(get_images_from_folder(st.session_state.asset_sources['extracted_media']))
            all_images.update(st.session_state.uploaded_images)
            
            image_options = ["(Auto-match)"] + sorted(all_images.keys())
            
            image_shape_candidates = [e for e in layout['elements'] if e['type'] in ['image', 'shape']]
            
            for el in image_shape_candidates:
                original_id = el['id']
                current_mapping = st.session_state.manual_mappings.get(original_id, "")
                
                with st.expander(f"{original_id[:25]}", expanded=False):
                    # Show alt text if available
                    if el.get('alt_text'):
                        st.caption(f"Alt text: {el['alt_text']}")
                    
                    # Show current match
                    if el.get('image_path'):
                        src = el.get('match_source', 'unknown')
                        st.success(f"✓ {src}: {Path(el['image_path']).name}")
                    else:
                        st.error("✗ No image matched")
                    
                    # Manual override
                    current_img_name = Path(current_mapping).name if current_mapping else "(Auto-match)"
                    
                    selected_img = st.selectbox(
                        "Override",
                        image_options,
                        index=image_options.index(current_img_name) if current_img_name in image_options else 0,
                        key=f"manual_img_{original_id}"
                    )
                    
                    if selected_img == "(Auto-match)":
                        if original_id in st.session_state.manual_mappings:
                            del st.session_state.manual_mappings[original_id]
                            layout = harvest_ppt(
                                st.session_state.pptx_path,
                                target,
                                st.session_state.asset_sources,
                                st.session_state.manual_mappings
                            )
                            st.session_state.layout = layout
                            st.rerun()
                    else:
                        full_path = all_images[selected_img]
                        if st.session_state.manual_mappings.get(original_id) != full_path:
                            st.session_state.manual_mappings[original_id] = full_path
                            layout = harvest_ppt(
                                st.session_state.pptx_path,
                                target,
                                st.session_state.asset_sources,
                                st.session_state.manual_mappings
                            )
                            st.session_state.layout = layout
                            st.rerun()
            
            # BACKGROUND
            st.divider()
            st.header("🖼️ Background")
            
            bg_opt = st.radio("BG", ["PPTX color", "Solid", "Image"], key="bg_type")
            
            if bg_opt == "PPTX color":
                st.session_state.bg_settings = {'type': 'pptx', 'value': None}
                st.info(f"{layout['pptx_background']}")
            
            elif bg_opt == "Solid":
                hex_c = st.color_picker("Color", "#F5F5F5")
                rgb = tuple(int(hex_c[i:i+2], 16) for i in (1, 3, 5))
                st.session_state.bg_settings = {'type': 'color', 'value': rgb}
            
            elif bg_opt == "Image":
                if all_images:
                    bg_img_name = st.selectbox("Select", list(all_images.keys()), key="bg_image_select")
                    if bg_img_name:
                        bg_path = all_images[bg_img_name]
                        try:
                            bg_img = Image.open(bg_path).convert('RGB')
                            st.session_state.bg_settings = {'type': 'image', 'value': bg_img}
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            # EXPORT
            st.divider()
            st.header("5. Export")
            fps = st.slider("FPS", 6, 60, 30)
            duration = st.slider("Sec", 1, 30, 5)
            st.session_state.export_fps = fps
            st.session_state.export_duration = duration
    
    if not st.session_state.layout:
        st.info("""
        **Workflow:**
        1. Set Templates directory (e.g., `./templates`)
        2. Upload PPTX (e.g., `insurance tips.pptx`)
        3. Tool auto-looks in `templates/insurance tips/ppt/media/`
        4. Upload fallback images if needed
        5. Configure animations
        6. Export
        """)
        return
    
    layout = st.session_state.layout
    
    # Main area
    col_preview, col_controls = st.columns([2, 1])
    
    with col_controls:
        st.subheader("✨ Animations")
        
        element_options = []
        for e in layout['elements']:
            display = f"{e['id']}"
            if e.get('alt_text'):
                display += f" ({e['alt_text'][:15]})"
            display += f" [{e['type']}]"
            element_options.append((display, e['id']))
        
        selected_display = st.selectbox(
            "Select Element",
            ["(None)"] + [opt[0] for opt in element_options],
            key="anim_element_select"
        )
        
        if selected_display != "(None)":
            element_id = next(opt[1] for opt in element_options if opt[0] == selected_display)
            st.session_state.selected_element = element_id
            
            current_anim = st.session_state.anim_settings.get(element_id, {})
            
            st.divider()
            st.text(f"Configuring: {element_id[:25]}")
            
            anim_style = st.selectbox(
                "Style",
                list(ANIMATION_STYLES.keys()),
                index=list(ANIMATION_STYLES.keys()).index(current_anim.get('style', 'None')),
                key=f"anim_style_{element_id}"
            )
            
            if anim_style != "None":
                anim_duration = st.slider("Duration", 0.1, 5.0, current_anim.get('duration', 1.0), 0.1, key=f"anim_dur_{element_id}")
                anim_delay = st.slider("Delay", 0.0, 10.0, current_anim.get('delay', 0.0), 0.1, key=f"anim_delay_{element_id}")
                anim_easing = st.selectbox(
                    "Easing",
                    list(EASING_FUNCTIONS.keys()),
                    index=list(EASING_FUNCTIONS.keys()).index(current_anim.get('easing', 'Ease Out')),
                    key=f"anim_ease_{element_id}"
                )
                
                if st.button("Apply", key=f"apply_anim_{element_id}"):
                    st.session_state.anim_settings[element_id] = {
                        'style': anim_style,
                        'duration': anim_duration,
                        'delay': anim_delay,
                        'easing': anim_easing
                    }
                    st.success(f"Applied {anim_style}")
                    st.rerun()
            
            if st.button("Clear", key=f"clear_anim_{element_id}"):
                if element_id in st.session_state.anim_settings:
                    del st.session_state.anim_settings[element_id]
                st.rerun()
        
        if st.session_state.anim_settings:
            st.divider()
            st.caption("Active Animations")
            for el_id, anim in st.session_state.anim_settings.items():
                st.text(f"• {el_id[:15]}: {anim['style']}")
        
        st.divider()
        st.subheader("📝 Edit Text")
        for el in layout['elements']:
            if el.get('type') == 'text':
                cur = st.session_state.user_data.get(el['id'], el.get('text_default', ''))
                new = st.text_area(f"{el['id'][:15]}", cur, key=f"t_{el['id']}", height=40)
                st.session_state.user_data[el['id']] = new
        
        if st.button("🔄 Refresh", use_container_width=True, type="primary"):
            st.rerun()
    
    with col_preview:
        bg_info = st.session_state.bg_settings['type']
        sources = [k for k, v in st.session_state.asset_sources.items() if v]
        st.caption(f"Sources: {', '.join(sources)} | BG: {bg_info} | Anims: {len(st.session_state.anim_settings)}")
        
        preview_time = st.session_state.export_duration / 2 if hasattr(st.session_state, 'export_duration') else 2.5
        frame = render_frame(
            layout, 
            st.session_state.user_data, 
            st.session_state.font_path, 
            st.session_state.bg_settings,
            st.session_state.anim_settings,
            preview_time,
            st.session_state.export_duration if hasattr(st.session_state, 'export_duration') else 5
        )
        st.image(frame, use_container_width=True)
        
        if st.session_state.anim_settings:
            st.caption("Timeline Preview")
            preview_frame = st.slider("Time", 0.0, st.session_state.export_duration, preview_time, 0.1, key="preview_time")
            frame_preview = render_frame(
                layout, 
                st.session_state.user_data, 
                st.session_state.font_path, 
                st.session_state.bg_settings,
                st.session_state.anim_settings,
                preview_frame,
                st.session_state.export_duration
            )
            st.image(frame_preview, use_container_width=True)
    
    with st.expander(f"Elements ({len(layout['elements'])})"):
        for el in layout['elements']:
            anim_status = ""
            if el['id'] in st.session_state.anim_settings:
                anim = st.session_state.anim_settings[el['id']]
                anim_status = f" [{anim['style']}]"
            
            if el['type'] == 'image':
                path = el.get('image_path', 'NOT MAPPED')
                status = "✓" if path else "✗"
                src = f"({el.get('match_source', '?')})" if path else ""
                alt = f" [alt:{el.get('alt_text', 'none')}]" if el.get('alt_text') else ""
                st.text(f"{status} 🖼️ {el['id']}{alt} {src}{anim_status}")
            elif el['type'] == 'text':
                st.text(f"📝 {el['id']}{anim_status}")
            else:
                st.text(f"⬜ {el['id']}{anim_status}")
    
    st.subheader("Export")
    a, b = st.columns(2)
    
    with a:
        if st.button("🎬 MP4", use_container_width=True, type="primary"):
            with st.spinner(f"Rendering {st.session_state.export_duration}s..."):
                fps = st.session_state.export_fps
                duration = st.session_state.export_duration
                total_frames = int(fps * duration)
                
                frames = []
                for i in range(total_frames):
                    frame_time = i / fps
                    frame = render_frame(
                        layout, 
                        st.session_state.user_data, 
                        st.session_state.font_path, 
                        st.session_state.bg_settings,
                        st.session_state.anim_settings,
                        frame_time,
                        duration
                    )
                    frames.append(frame)
                
                out = tempfile.mktemp(suffix=".mp4")
                if encode_video(frames, fps, out):
                    with open(out, "rb") as f:
                        st.video(f.read())
                        st.download_button("DL MP4", f, "vid.mp4", mime="video/mp4")
                    os.unlink(out)
    
    with b:
        if st.button("🖼️ PNG", use_container_width=True):
            frame = render_frame(
                layout, 
                st.session_state.user_data, 
                st.session_state.font_path, 
                st.session_state.bg_settings,
                st.session_state.anim_settings,
                0,
                st.session_state.export_duration
            )
            img = Image.fromarray(frame)
            
            buf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(buf.name)
            with open(buf.name, "rb") as f:
                st.download_button("DL PNG", f, "frame.png", mime="image/png")
            os.unlink(buf.name)

if __name__ == "__main__":
    main()
