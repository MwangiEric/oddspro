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

st.set_page_config(page_title="PPTX Video Factory", layout="wide")

# --- SOCIAL MEDIA LAYOUTS ---
LAYOUTS = {
    "Landscape (16:9)": {"w": 1920, "h": 1080, "aspect": 16/9},
    "Portrait (9:16)": {"w": 1080, "h": 1920, "aspect": 9/16},
    "Square (1:1)": {"w": 1080, "h": 1080, "aspect": 1},
    "Instagram Feed (4:5)": {"w": 1080, "h": 1350, "aspect": 4/5},
    "Twitter/X (1200x675)": {"w": 1200, "h": 675, "aspect": 16/9},
    "Facebook Cover (820x312)": {"w": 1640, "h": 624, "aspect": 820/312},  # 2x for quality
    "YouTube Thumbnail (1280x720)": {"w": 1280, "h": 720, "aspect": 16/9},
    "TikTok/Snap (1080x1920)": {"w": 1080, "h": 1920, "aspect": 9/16},
}

# --- FONT MANAGEMENT ---
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

# --- PPTX EXTRACTION WITH SCALING ---
def harvest_ppt(ppt_file, target_w, target_h):
    """Extract and scale to target dimensions."""
    try:
        prs = Presentation(ppt_file)
        if not prs.slides:
            return None
        
        slide = prs.slides[0]
        emu_to_px = 96 / 914400
        
        # Original dimensions
        orig_w = int(prs.slide_width * emu_to_px)
        orig_h = int(prs.slide_height * emu_to_px)
        
        # Calculate scale to fit target while maintaining aspect
        scale_x = target_w / orig_w
        scale_y = target_h / orig_h
        scale = min(scale_x, scale_y)  # Fit within target
        
        # Centering offsets
        offset_x = (target_w - int(orig_w * scale)) // 2
        offset_y = (target_h - int(orig_h * scale)) // 2
        
        config = {
            "canvas": {"w": target_w, "h": target_h},
            "original": {"w": orig_w, "h": orig_h},
            "scale": scale,
            "elements": []
        }
        
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                continue
            
            # Scale position and size
            x = int(shape.left * emu_to_px * scale) + offset_x
            y = int(shape.top * emu_to_px * scale) + offset_y
            w = int(shape.width * emu_to_px * scale)
            h = int(shape.height * emu_to_px * scale)
            
            # Scale font size
            font_scale = scale if scale < 1 else 1  # Don't upscale fonts
            
            el = {
                "id": shape.name,
                "x": x, "y": y, "w": w, "h": h,
                "z_order": getattr(shape, 'z_order', 0),
            }
            
            if shape.has_text_frame and shape.text.strip():
                para = shape.text_frame.paragraphs[0]
                run = para.runs[0] if para.runs else None
                
                orig_size = int(run.font.size.pt) if run and run.font.size else 24
                new_size = max(int(orig_size * font_scale), 12)  # Min 12pt
                
                el.update({
                    "type": "text",
                    "text_default": shape.text,
                    "size": new_size,
                    "color": f"#{run.font.color.rgb}" if run and run.font.color.rgb else "#000000",
                    "bold": bool(run.font.bold) if run else False,
                })
            else:
                el["type"] = "shape"
            
            config["elements"].append(el)
        
        config["elements"].sort(key=lambda x: x.get('z_order', 0))
        return config
        
    except Exception as e:
        st.error(f"Extraction failed: {e}")
        return None

# --- TEXT RENDERING ---
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
    
    # Word wrap
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
    
    # Center
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

def render_frame(layout, user_data, font_path, bg_color, bg_image=None):
    w, h = layout['canvas']['w'], layout['canvas']['h']
    
    if bg_image:
        frame = np.array(bg_image.resize((w, h), Image.Resampling.LANCZOS))
    else:
        frame = np.full((h, w, 3), bg_color, dtype=np.uint8)
    
    for el in layout['elements']:
        if el['type'] != 'text':
            continue
        
        text = user_data.get(el['id'], el['text_default'])
        hex_color = el['color'].lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        text_array = render_text(text, el['w'], el['h'], el['size'], rgb + (255,), font_path)
        
        x, y = el['x'], el['y']
        eh, ew = text_array.shape[:2]
        
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

# --- UI ---
def main():
    st.title("🏭 PPTX Video Factory")
    st.caption("Social media layouts: 16:9, 9:16, 1:1, 4:5, and more")
    
    if 'layout' not in st.session_state:
        st.session_state.layout = None
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'font_path' not in st.session_state:
        st.session_state.font_path = find_font()
    if 'selected_layout' not in st.session_state:
        st.session_state.selected_layout = "Landscape (16:9)"
    
    with st.sidebar:
        st.header("1. Choose Format")
        layout_name = st.selectbox(
            "Social Media Format",
            list(LAYOUTS.keys()),
            index=list(LAYOUTS.keys()).index(st.session_state.selected_layout)
        )
        st.session_state.selected_layout = layout_name
        
        target = LAYOUTS[layout_name]
        st.info(f"Output: **{target['w']}×{target['h']}** ({target['aspect']:.2f}:1)")
        
        st.divider()
        st.header("2. Upload PPTX")
        uploaded = st.file_uploader("Template file", type=['pptx'])
        
        if uploaded and st.button("Extract & Scale"):
            tmp_path = Path(tempfile.gettempdir()) / f"pptx_{hashlib.md5(uploaded.getvalue()).hexdigest()[:8]}.pptx"
            tmp_path.write_bytes(uploaded.getvalue())
            
            layout = harvest_ppt(str(tmp_path), target['w'], target['h'])
            if layout:
                st.session_state.layout = layout
                st.session_state.user_data = {
                    el['id']: el['text_default']
                    for el in layout['elements']
                    if el['type'] == 'text'
                }
                st.success(f"Scaled from {layout['original']['w']}×{layout['original']['h']} to {target['w']}×{target['h']}")
                st.rerun()
        
        if st.session_state.layout:
            st.divider()
            st.header("3. Background")
            
            bg_type = st.radio("Type", ["Color", "Image"])
            
            if bg_type == "Color":
                bg_hex = st.color_picker("Color", "#F5F5F5")
                st.session_state.bg_color = tuple(int(bg_hex[i:i+2], 16) for i in (1, 3, 5))
                st.session_state.bg_image = None
            else:
                bg_file = st.file_uploader("Image", type=['png', 'jpg'])
                if bg_file:
                    st.session_state.bg_image = Image.open(bg_file).convert('RGB')
            
            st.divider()
            st.header("4. Export")
            fps = st.slider("FPS", 6, 30, 12)
            duration = st.slider("Seconds", 1, 10, 5)
    
    if not st.session_state.layout:
        st.info("👈 Select a format and upload PPTX")
        
        with st.expander("Available Formats"):
            for name, dims in LAYOUTS.items():
                st.text(f"{name}: {dims['w']}×{dims['h']}")
        return
    
    layout = st.session_state.layout
    
    # Info bar
    cols = st.columns(4)
    cols[0].metric("Output Size", f"{layout['canvas']['w']}×{layout['canvas']['h']}")
    cols[1].metric("Scale Factor", f"{layout['scale']:.2f}x")
    cols[2].metric("Text Boxes", len([e for e in layout['elements'] if e['type'] == 'text']))
    cols[3].metric("Font", Path(st.session_state.font_path).name if st.session_state.font_path else "Default")
    
    # Preview and edit
    st.subheader("Preview")
    
    col_preview, col_edit = st.columns([2, 1])
    
    with col_edit:
        st.caption("Edit Content")
        for el in layout['elements']:
            if el['type'] == 'text':
                current = st.session_state.user_data.get(el['id'], el['text_default'])
                new_text = st.text_area(
                    f"{el['id']} ({el['w']}×{el['h']}px, {el['size']}pt)",
                    current,
                    key=f"txt_{el['id']}",
                    height=50
                )
                st.session_state.user_data[el['id']] = new_text
    
    with col_preview:
        bg = st.session_state.get('bg_image') or st.session_state.get('bg_color', (245, 245, 245))
        frame = render_frame(layout, st.session_state.user_data, st.session_state.font_path, bg)
        st.image(frame, use_container_width=True)
    
    # Export
    st.subheader("Export")
    
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button("🎬 MP4 Video", use_container_width=True, type="primary"):
            with st.spinner(f"Rendering {layout['canvas']['w']}×{layout['canvas']['h']}..."):
                bg = st.session_state.get('bg_image') or st.session_state.get('bg_color', (245, 245, 245))
                frames = []
                
                for _ in range(fps * duration):
                    frames.append(render_frame(layout, st.session_state.user_data, st.session_state.font_path, bg))
                
                out_path = tempfile.mktemp(suffix=".mp4")
                if encode_video(frames, fps, out_path):
                    with open(out_path, "rb") as f:
                        st.video(f.read())
                        st.download_button(
                            "Download MP4",
                            f,
                            f"video_{layout['canvas']['w']}x{layout['canvas']['h']}.mp4",
                            mime="video/mp4"
                        )
                    os.unlink(out_path)
                else:
                    st.error("Video encoding failed")
    
    with c2:
        if st.button("🖼️ PNG Frame", use_container_width=True):
            bg = st.session_state.get('bg_image') or st.session_state.get('bg_color', (245, 245, 245))
            frame = render_frame(layout, st.session_state.user_data, st.session_state.font_path, bg)
            img = Image.fromarray(frame)
            
            buf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(buf.name)
            with open(buf.name, "rb") as f:
                st.download_button(
                    "Download PNG",
                    f,
                    f"frame_{layout['canvas']['w']}x{layout['canvas']['h']}.png",
                    mime="image/png"
                )
            os.unlink(buf.name)

if __name__ == "__main__":
    main()
