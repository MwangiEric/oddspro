import streamlit as st
import os
import tempfile
import numpy as np
import cv2
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# --- 1. CONFIGURATION & THEME ---
st.set_page_config(page_title="Anything Factory V2", layout="wide")

THEME = {
    "bg_default": (30, 30, 30),
    "text_fallback": "#FFFFFF",
}

CACHE_DIR = Path(tempfile.gettempdir()) / "factory_v2_cache"
CACHE_DIR.mkdir(exist_ok=True)

# --- 2. FONT & METRICS UTILITIES ---
def get_safe_font(size):
    """Finds a system font or warns and uses default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux/Streamlit
        "C:/Windows/Fonts/arial.ttf",                     # Windows
        "/System/Library/Fonts/Helvetica.ttc"             # macOS
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size), "System"
    return ImageFont.load_default(), "PIL Default (Bitmap)"

def get_text_metrics(text, font_size, box_w, box_h):
    """Calculates scaling and metrics without rendering."""
    font, font_type = get_safe_font(font_size)
    # Dummy image for measurement
    img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(img)
    
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    scale = 1.0
    if tw > box_w or th > box_h:
        scale = min(box_w / (tw + 1), box_h / (th + 1))
    
    return {"scale": scale, "tw": tw, "th": th, "font_type": font_type}

# --- 3. RECURSIVE HARVESTER (FIXES GROUPS & Z-ORDER) ---
def harvest_ppt(ppt_file):
    prs = Presentation(ppt_file)
    slide = prs.slides[0]
    emu_to_px = 96 / 914400
    
    config = {
        "canvas": {"w": int(prs.slide_width * emu_to_px), "h": int(prs.slide_height * emu_to_px)},
        "elements": []
    }

    def process_shapes(shapes, off_x=0, off_y=0):
        for shape in shapes:
            # Flatten Groups: Recursive call with offsets
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                process_shapes(shape.shapes, off_x + shape.left, off_y + shape.top)
                continue
            
            # Basic properties
            el = {
                "id": f"{shape.name}_{shape.shape_id}",
                "x": int((shape.left + off_x) * emu_to_px),
                "y": int((shape.top + off_y) * emu_to_px),
                "w": int(shape.width * emu_to_px),
                "h": int(shape.height * emu_to_px),
                "z_order": shape.z_order,
                "rotation": getattr(shape, 'rotation', 0),
                "type": "shape"
            }

            if shape.has_text_frame and shape.text.strip():
                run = shape.text_frame.paragraphs[0].runs[0] if shape.text_frame.paragraphs[0].runs else None
                color = "#FFFFFF"
                if run and hasattr(run.font.color, 'rgb') and run.font.color.rgb:
                    color = f"#{run.font.color.rgb}"
                
                el.update({
                    "type": "text",
                    "text_default": shape.text,
                    "size": int(run.font.size.pt) if run and run.font.size else 40,
                    "color": color
                })
            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                el.update({"type": "image", "blob": shape.image.blob})
            
            config["elements"].append(el)

    process_shapes(slide.shapes)
    # Fix: Global Z-Order Sorting
    config["elements"].sort(key=lambda x: x['z_order'])
    return config

# --- 4. THE ALPHA-COMPOSITING ENGINE ---
def render_text_layer(el, text_val):
    metrics = get_text_metrics(text_val, el['size'], el['w'], el['h'])
    actual_size = int(el['size'] * metrics['scale'])
    font, _ = get_safe_font(actual_size)
    
    # Create canvas for the specific element
    img = Image.new("RGBA", (el['w'], el['h']), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    bbox = draw.textbbox((0, 0), text_val, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    # Center text in box
    draw.text(((el['w']-tw)//2, (el['h']-th)//2), text_val, fill=el['color'], font=font)
    
    # Apply Rotation
    if el['rotation'] != 0:
        img = img.rotate(-el['rotation'], expand=True, resample=Image.BICUBIC)
    
    return np.array(img)

# --- 5. CODEC SURVIVOR & RENDER LOOP ---
def generate_factory_video(layout, user_data, bg_upload):
    w, h = layout['canvas']['w'], layout['canvas']['h']
    fps, duration = 12, 5
    out_path = tempfile.mktemp(suffix=".mp4")
    
    # Fix: Codec Fallback Loop
    writer = None
    for codec in ['mp4v', 'avc1', 'XVID']:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
        if writer.isOpened():
            st.toast(f"Connected to Codec: {codec}")
            break
    
    if not writer or not writer.isOpened():
        st.error("Failed to initialize any video codec.")
        return None

    # Fix: Background Image Support
    if bg_upload:
        bg_pil = Image.open(bg_upload).convert("RGB").resize((w, h))
        base_frame = np.array(bg_pil)
    else:
        base_frame = np.full((h, w, 3), THEME["bg_default"], dtype=np.uint8)

    # Pre-render text layers to avoid CPU spikes in loop
    layers = []
    for el in layout['elements']:
        if el['type'] == 'text':
            txt = user_data.get(el['id'], el['text_default'])
            layers.append({
                'arr': render_text_layer(el, txt),
                'x': el['x'], 'y': el['y']
            })

    # Fix: Alpha Compositing Math Loop
    for _ in range(fps * duration):
        frame = base_frame.copy()
        for layer in layers:
            arr = layer['arr']
            lx, ly = layer['x'], layer['y']
            lh, lw = arr.shape[:2]
            
            # ROI boundaries
            if ly+lh > h or lx+lw > w: continue
            
            # Math: Normalize alpha and blend
            alpha = arr[:, :, 3:4] / 255.0
            rgb = arr[:, :, :3]
            frame[ly:ly+lh, lx:lx+lw] = (rgb * alpha + frame[ly:ly+lh, lx:lx+lw] * (1 - alpha)).astype(np.uint8)
            
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    writer.release()
    return out_path

# --- 6. STREAMLIT UI ---
st.title("🏭 Anything Factory V2")

with st.sidebar:
    st.header("1. Assets")
    ppt = st.file_uploader("Template (PPTX)", type="pptx")
    bg = st.file_uploader("Background (Optional)", type=["jpg", "png"])
    if ppt and st.button("Harvest Template"):
        st.session_state.layout = harvest_ppt(ppt)
        st.session_state.user_data = {e['id']: e.get('text_default','') for e in st.session_state.layout['elements'] if e['type']=='text'}

if 'layout' in st.session_state and st.session_state.layout:
    col_edit, col_prev = st.columns([1, 1])
    
    with col_edit:
        st.subheader("Edit Data")
        for el in st.session_state.layout['elements']:
            if el['type'] == 'text':
                # Issue Fix: Metrics Preview
                m = get_text_metrics(st.session_state.user_data[el['id']], el['size'], el['w'], el['h'])
                label = f"{el['id']} (Scale: {m['scale']:.1%})"
                st.session_state.user_data[el['id']] = st.text_area(label, value=st.session_state.user_data[el['id']])
                if m['scale'] < 1.0: st.caption(f"⚠️ Text auto-shrunk from {el['size']}pt")

    with col_prev:
        st.subheader("Production")
        if st.button("🎬 Render Full Video"):
            with st.spinner("NumPy Engine Compositing Frames..."):
                video_path = generate_factory_video(st.session_state.layout, st.session_state.user_data, bg)
                if video_path:
                    st.video(video_path)
                    with open(video_path, "rb") as f:
                        st.download_button("Download MP4", f, "factory_video.mp4")
