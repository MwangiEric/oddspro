import streamlit as st
import os
import tempfile
import numpy as np
import cv2
import requests
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from PIL import Image, ImageDraw, ImageFont
import threading
import hashlib
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="PPTX Video Factory", layout="wide")

# Cache directory for fonts and processed layouts
CACHE_DIR = Path(tempfile.gettempdir()) / "pptx_factory"
CACHE_DIR.mkdir(exist_ok=True)

# --- 1. FONT MANAGEMENT ---
def ensure_font():
    """Download and cache Inter font for consistent metrics."""
    font_path = CACHE_DIR / "Inter-Regular.ttf"
    
    if not font_path.exists():
        with st.spinner("Downloading font..."):
            # Direct link to Inter Regular from Google Fonts
            url = "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hjp-Ek-_EeA.woff2"
            # Fallback to GitHub raw if needed
            url = "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"
            
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    font_path.write_bytes(r.content)
                else:
                    # Use system fallback
                    return get_system_font()
            except:
                return get_system_font()
    
    return str(font_path)

def get_system_font():
    """Fallback to system fonts."""
    import platform
    candidates = []
    
    if platform.system() == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    elif platform.system() == "Darwin":
        candidates = ["/System/Library/Fonts/Helvetica.ttc"]
    elif platform.system() == "Windows":
        candidates = ["C:/Windows/Fonts/arial.ttf"]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    
    return None  # Will use PIL default

# --- 2. PPTX HARVESTER WITH FULL PROPERTY EXTRACTION ---
def harvest_ppt(ppt_file):
    """
    Extract all possible properties from PPTX.
    Returns None if extraction fails.
    """
    try:
        prs = Presentation(ppt_file)
        if not prs.slides:
            st.error("PPTX has no slides")
            return None
        
        slide = prs.slides[0]
        emu_to_px = 96 / 914400
        
        config = {
            "canvas": {
                "w": int(prs.slide_width * emu_to_px),
                "h": int(prs.slide_height * emu_to_px)
            },
            "elements": []
        }
        
        for shape in slide.shapes:
            # Skip empty placeholders
            if shape.is_placeholder:
                if not shape.has_text_frame or not shape.text.strip():
                    continue
            
            # Handle groups recursively (flatten)
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                for subshape in shape.shapes:
                    element = extract_shape_properties(subshape, emu_to_px)
                    if element:
                        config["elements"].append(element)
                continue
            
            element = extract_shape_properties(shape, emu_to_px)
            if element:
                config["elements"].append(element)
        
        return config
        
    except Exception as e:
        st.error(f"Failed to parse PPTX: {str(e)}")
        return None

def extract_shape_properties(shape, emu_to_px):
    """Extract comprehensive properties from a single shape."""
    # Skip invisible shapes
    if getattr(shape, 'visible', True) == False:
        return None
    
    el = {
        "id": shape.name or f"shape_{id(shape)}",
        "x": int(shape.left * emu_to_px),
        "y": int(shape.top * emu_to_px),
        "w": int(shape.width * emu_to_px),
        "h": int(shape.height * emu_to_px),
        "rotation": getattr(shape, 'rotation', 0),
        "z_order": getattr(shape, 'z_order', 0),
    }
    
    # Text extraction with full formatting
    if shape.has_text_frame and shape.text.strip():
        text_frame = shape.text_frame
        paragraphs = []
        
        for para in text_frame.paragraphs:
            runs = []
            for run in para.runs:
                font_info = {
                    "text": run.text,
                    "font_name": run.font.name,
                    "font_size": int(run.font.size.pt) if run.font.size else 24,
                    "bold": bool(run.font.bold),
                    "italic": bool(run.font.italic),
                    "underline": bool(run.font.underline),
                    "color": extract_color(run.font),
                }
                runs.append(font_info)
            
            paragraphs.append({
                "runs": runs,
                "alignment": str(para.alignment),
                "space_before": para.space_before,
                "space_after": para.space_after,
            })
        
        # Concatenate all text for default value
        full_text = "".join(["".join([r["text"] for r in p["runs"]]) for p in paragraphs])
        
        el.update({
            "type": "text",
            "text_default": full_text,
            "paragraphs": paragraphs,  # Rich formatting preserved
            "word_wrap": text_frame.word_wrap,
        })
        
        # Use first run for default styling
        if paragraphs and paragraphs[0]["runs"]:
            first_run = paragraphs[0]["runs"][0]
            el["size"] = first_run["font_size"]
            el["color"] = first_run["color"]
            el["bold"] = first_run["bold"]
            el["italic"] = first_run["italic"]
    
    # Image extraction
    elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        try:
            image = shape.image
            el.update({
                "type": "image",
                "image_ext": image.ext,
                "image_blob": image.blob,
                "image_size": (image.width, image.height),
            })
        except Exception as e:
            el["type"] = "asset"
            el["error"] = str(e)
    else:
        el["type"] = "shape"
        # Extract fill color if available
        if hasattr(shape, 'fill') and shape.fill.type is not None:
            el["fill_color"] = extract_fill_color(shape.fill)
    
    return el

def extract_color(font):
    """Safely extract hex color from font."""
    if not font or not font.color:
        return "#FFFFFF"
    
    if hasattr(font.color, 'rgb') and font.color.rgb:
        return f"#{font.color.rgb}"
    
    # Theme colors - return default
    return "#FFFFFF"

def extract_fill_color(fill):
    """Extract fill color if solid."""
    try:
        if fill.type == 1:  # SOLID
            if hasattr(fill.fore_color, 'rgb') and fill.fore_color.rgb:
                return f"#{fill.fore_color.rgb}"
    except:
        pass
    return None

# --- 3. TEXT MEASUREMENT & OVERFLOW DETECTION ---
def measure_text_metrics(text, font_path, font_size, max_width=None, bold=False, italic=False):
    """
    Measure text with precise metrics including overflow detection.
    Returns dict with dimensions, scale factor, and overflow status.
    """
    img = Image.new("RGBA", (4000, 4000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    # Handle multiline
    lines = text.split('\n') if '\n' in text else [text]
    
    if max_width:
        # Word wrap to max_width
        wrapped_lines = []
        for line in lines:
            words = line.split()
            current_line = []
            for word in words:
                test = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))
        lines = wrapped_lines or [text]
    
    # Measure each line
    line_metrics = []
    max_width_found = 0
    total_height = 0
    line_spacing = font_size * 1.2
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_width_found = max(max_width_found, w)
        total_height += line_spacing
        line_metrics.append({
            'text': line,
            'width': w,
            'height': h,
            'bbox': bbox
        })
    
    return {
        'lines': line_metrics,
        'width': max_width_found,
        'height': total_height,
        'line_count': len(lines),
        'font_size': font_size,
        'scale_factor': 1.0
    }

def calculate_auto_scale(text_metrics, box_w, box_h, min_scale=0.5, max_scale=1.0):
    """
    Calculate scale factor to fit text in box.
    Returns scale factor (0.5-1.0) and overflow status.
    """
    text_w = text_metrics['width']
    text_h = text_metrics['height']
    
    if text_w == 0 or text_h == 0:
        return 1.0, False
    
    scale_x = box_w / text_w
    scale_y = box_h / text_h
    scale = min(scale_x, scale_y, max_scale)
    scale = max(scale, min_scale)  # Don't go below min_scale
    
    # Check if scaling is needed
    overflow = scale < 1.0
    
    return scale, overflow

# --- 4. RENDERING ENGINE WITH AUTO-SCALING ---
def render_text_to_array(text, w, h, font_path, font_size=40, color="#FFFFFF", 
                         bold=False, italic=False, auto_scale=True, alignment="center"):
    """
    Render text to numpy array with overflow handling and auto-scaling.
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        base_font = ImageFont.truetype(font_path, font_size)
    except:
        base_font = ImageFont.load_default()
    
    # Measure with word wrap at box width
    metrics = measure_text_metrics(text, font_path, font_size, max_width=w)
    
    # Auto-scale if needed
    actual_size = font_size
    if auto_scale:
        scale, overflow = calculate_auto_scale(metrics, w, h)
        if scale < 1.0:
            actual_size = int(font_size * scale)
            # Re-measure with new size
            metrics = measure_text_metrics(text, font_path, actual_size, max_width=w)
            try:
                base_font = ImageFont.truetype(font_path, actual_size)
            except:
                pass
    
    # Vertical centering
    total_h = metrics['height']
    start_y = (h - total_h) // 2
    
    line_height = actual_size * 1.2
    
    for i, line_data in enumerate(metrics['lines']):
        line = line_data['text']
        line_w = line_data['width']
        
        # Horizontal alignment
        if alignment == "center":
            x = (w - line_w) // 2
        elif alignment == "right":
            x = w - line_w
        else:  # left
            x = 0
        
        y = start_y + (i * line_height)
        
        # Adjust for textbbox offset (top-left anchor correction)
        bbox = line_data['bbox']
        y_adjusted = y - bbox[1]
        
        draw.text((x, y_adjusted), line, fill=color, font=base_font)
    
    return np.array(img), metrics

# --- 5. VIDEO GENERATION (STREAMING FOR LOW MEMORY) ---
def generate_video_streaming(layout, user_data, fps=12, duration=5, progress_callback=None):
    """
    Generate video frame-by-frame to minimize RAM usage.
    Supports progress callbacks for UI updates.
    """
    w, h = layout['canvas']['w'], layout['canvas']['h']
    total_frames = int(fps * duration)
    
    # Setup video writer
    out_path = tempfile.mktemp(suffix=".mp4")
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # or 'mp4v' if avc1 fails
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    
    if not writer.isOpened():
        # Fallback codec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    
    font_path = ensure_font()
    
    # Pre-render all text layers with auto-scaling
    text_layers = []
    overflow_warnings = []
    
    for el in layout['elements']:
        if el['type'] != 'text':
            continue
            
        text_content = user_data.get(el['id'], el['text_default'])
        
        # Render with auto-scaling
        text_array, metrics = render_text_to_array(
            text_content,
            el['w'], el['h'],
            font_path,
            font_size=el.get('size', 40),
            color=el.get('color', '#FFFFFF'),
            bold=el.get('bold', False),
            italic=el.get('italic', False),
            auto_scale=True,
            alignment="center"
        )
        
        # Check if scaling was applied
        if metrics['font_size'] < el.get('size', 40):
            overflow_warnings.append({
                'id': el['id'],
                'original_size': el.get('size', 40),
                'scaled_size': metrics['font_size'],
                'text': text_content[:50] + '...' if len(text_content) > 50 else text_content
            })
        
        text_layers.append({
            'array': text_array,
            'x': el['x'],
            'y': el['y'],
            'z': el.get('z_order', 0)
        })
    
    # Sort by z-order
    text_layers.sort(key=lambda x: x['z'])
    
    # Generate frames
    for frame_idx in range(total_frames):
        # Dark background (configurable)
        frame = np.full((h, w, 3), (30, 30, 30), dtype=np.uint8)
        
        # Composite text layers
        for layer in text_layers:
            arr = layer['array']
            x, y = layer['x'], layer['y']
            eh, ew = arr.shape[:2]
            
            # Bounds checking
            if x < 0 or y < 0 or x + ew > w or y + eh > h:
                continue
            
            # Alpha blend
            alpha = arr[:, :, 3:4].astype(np.float32) / 255.0
            rgb = arr[:, :, :3].astype(np.float32)
            
            roi = frame[y:y+eh, x:x+ew].astype(np.float32)
            blended = (rgb * alpha + roi * (1 - alpha)).astype(np.uint8)
            frame[y:y+eh, x:x+ew] = blended
        
        # Convert RGB to BGR for OpenCV
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
        if progress_callback and frame_idx % 5 == 0:
            progress_callback(frame_idx / total_frames)
    
    writer.release()
    
    return out_path, overflow_warnings

# --- 6. STREAMLIT UI ---
def main():
    st.title("🏭 PPTX Video Factory")
    st.caption("Auto-scaling text • Overflow detection • Low-memory streaming")
    
    # Session state
    if 'layout' not in st.session_state:
        st.session_state.layout = None
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'font_path' not in st.session_state:
        st.session_state.font_path = ensure_font()
    
    # Sidebar: Upload and settings
    with st.sidebar:
        st.header("Template")
        uploaded_file = st.file_uploader("Upload PPTX", type=['pptx'])
        
        if uploaded_file and st.button("Extract Layout"):
            with st.spinner("Parsing PPTX..."):
                # Save to temp file
                tmp_path = CACHE_DIR / f"upload_{hashlib.md5(uploaded_file.getvalue()).hexdigest()}.pptx"
                tmp_path.write_bytes(uploaded_file.getvalue())
                
                layout = harvest_ppt(str(tmp_path))
                if layout:
                    st.session_state.layout = layout
                    # Initialize user data with defaults
                    st.session_state.user_data = {
                        el['id']: el.get('text_default', '') 
                        for el in layout['elements'] 
                        if el['type'] == 'text'
                    }
                    st.success(f"Extracted {len(layout['elements'])} elements")
                    st.rerun()
        
        if st.session_state.layout:
            st.divider()
            st.header("Export Settings")
            fps = st.slider("FPS", 6, 30, 12)
            duration = st.slider("Duration (seconds)", 1, 10, 5)
            
            st.divider()
            if st.button("Clear Layout"):
                st.session_state.layout = None
                st.session_state.user_data = {}
                st.rerun()
    
    # Main content
    if not st.session_state.layout:
        st.info("👈 Upload a PowerPoint file to get started")
        
        with st.expander("What this app does"):
            st.markdown("""
            1. **Extracts** all text and image elements from your PPTX
            2. **Measures** text using actual font metrics (not PPTX estimates)
            3. **Auto-scales** text that doesn't fit the original box
            4. **Streams** video frame-by-frame to stay within memory limits
            5. **Warns** you about text overflow so you can adjust
            
            **Best practices:**
            - Use PPTX as layout templates, not final designs
            - Keep text concise for better scaling
            - Use the overflow warnings to iterate on text length
            """)
        return
    
    layout = st.session_state.layout
    
    # Layout info
    col1, col2, col3 = st.columns(3)
    col1.metric("Canvas", f"{layout['canvas']['w']}×{layout['canvas']['h']}")
    text_elements = [e for e in layout['elements'] if e['type'] == 'text']
    col2.metric("Text Boxes", len(text_elements))
    col3.metric("Other Elements", len(layout['elements']) - len(text_elements))
    
    # Two-column layout: Editor and Preview
    left_col, right_col = st.columns([1, 1])
    
    with left_col:
        st.subheader("Edit Content")
        
        # Group elements by type
        text_els = [e for e in layout['elements'] if e['type'] == 'text']
        other_els = [e for e in layout['elements'] if e['type'] != 'text']
        
        with st.container(border=True):
            st.write("**Text Elements**")
            for el in text_els:
                # Show original formatting info
                orig_size = el.get('size', 40)
                orig_color = el.get('color', '#FFFFFF')
                
                col_label, col_input = st.columns([1, 3])
                with col_label:
                    st.caption(f"📄 {el['id'][:20]}")
                    st.caption(f"Box: {el['w']}×{el['h']}px")
                    st.caption(f"Font: {orig_size}pt")
                
                with col_input:
                    current_val = st.session_state.user_data.get(el['id'], el.get('text_default', ''))
                    new_val = st.text_area(
                        f"Content_{el['id']}",
                        value=current_val,
                        height=60,
                        label_visibility="collapsed"
                    )
                    st.session_state.user_data[el['id']] = new_val
        
        if other_els:
            with st.expander(f"Other Elements ({len(other_els)})"):
                for el in other_els:
                    st.caption(f"{el['type']}: {el['id']} at ({el['x']}, {el['y']})")
    
    with right_col:
        st.subheader("Generate Video")
        
        # Preview current text metrics
        with st.expander("Text Metrics Preview", expanded=True):
            font_path = st.session_state.font_path
            for el in text_els:
                user_text = st.session_state.user_data.get(el['id'], '')
                if not user_text:
                    continue
                
                metrics = measure_text_metrics(
                    user_text, font_path, 
                    el.get('size', 40), 
                    max_width=el['w']
                )
                scale, overflow = calculate_auto_scale(metrics, el['w'], el['h'])
                
                cols = st.columns([3, 1])
                with cols[0]:
                    st.text(f"{el['id'][:15]}: {metrics['line_count']} lines")
                with cols[1]:
                    if overflow:
                        st.error(f"↓{scale:.0%}")
                    else:
                        st.success("✓ Fit")
        
        # Generate button
        if st.button("🎬 Render MP4", type="primary", use_container_width=True):
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            def update_progress(pct):
                progress_bar.progress(min(pct, 0.99))
                status_text.text(f"Rendering frame {int(pct * 100)}%...")
            
            try:
                with st.spinner("Generating video..."):
                    video_path, warnings = generate_video_streaming(
                        layout,
                        st.session_state.user_data,
                        fps=fps,
                        duration=duration,
                        progress_callback=update_progress
                    )
                
                progress_bar.empty()
                status_text.empty()
                
                # Show overflow warnings
                if warnings:
                    with st.expander("⚠️ Text Auto-Scaled", expanded=True):
                        st.warning("Some text was too long and auto-scaled to fit:")
                        for w in warnings:
                            st.markdown(f"""
                            **{w['id']}**: {w['original_size']}pt → **{w['scaled_size']}pt**  
                            *"{w['text']}"*
                            """)
                
                # Display video
                st.video(video_path)
                
                # Download button
                with open(video_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download MP4",
                        f,
                        file_name=f"output_{hashlib.md5(str(st.session_state.user_data).encode()).hexdigest()[:8]}.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                
                # Cleanup temp file after display
                try:
                    os.unlink(video_path)
                except:
                    pass
                    
            except Exception as e:
                progress_bar.empty()
                st.error(f"Generation failed: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()
