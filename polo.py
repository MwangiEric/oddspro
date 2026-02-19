import streamlit as st
import json
import requests
import base64
import re
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Helper functions ----------
def parse_color(color_str):
    """Convert rgba(...), rgb(...), or #RRGGBB to a tuple (R,G,B,A)."""
    if not isinstance(color_str, str):
        return color_str  # assume already a tuple? but we expect string.
    if color_str.startswith('rgba'):
        parts = re.findall(r'[\d.]+', color_str)
        if len(parts) == 4:
            return tuple(int(float(p)) if i<3 else float(p) for i,p in enumerate(parts))
    elif color_str.startswith('rgb'):
        parts = re.findall(r'\d+', color_str)
        if len(parts) == 3:
            return tuple(int(p) for p in parts) + (255,)
    elif color_str.startswith('#'):
        h = color_str.lstrip('#')
        if len(h) == 6:
            return tuple(int(h[i:i+2], 16) for i in (0,2,4)) + (255,)
        elif len(h) == 3:
            return tuple(int(c*2, 16) for c in h) + (255,)
    # Default fallback
    return (0,0,0,255)

def load_image_from_src(src):
    """Load image from URL or data URI. Returns PIL Image."""
    if src.startswith('data:image'):
        header, encoded = src.split(',', 1)
        image_data = base64.b64decode(encoded)
        return Image.open(BytesIO(image_data)).convert('RGBA')
    else:
        response = requests.get(src, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')

def apply_crop(img, crop_x, crop_y, crop_w, crop_h):
    """Crop using normalized coordinates (0-1)."""
    if crop_w == 1 and crop_h == 1 and crop_x == 0 and crop_y == 0:
        return img
    w, h = img.size
    left = crop_x * w
    top = crop_y * h
    right = left + crop_w * w
    bottom = top + crop_h * h
    return img.crop((left, top, right, bottom))

def resize_image(img, target_w, target_h, keep_ratio, stretch):
    """Resize image according to Polotno rules."""
    if keep_ratio and not stretch:
        img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        new_img = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
        paste_x = (target_w - img.width) // 2
        paste_y = (target_h - img.height) // 2
        new_img.paste(img, (paste_x, paste_y), img)
        return new_img
    else:
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

def apply_flip(img, flip_x, flip_y):
    """Apply horizontal/vertical flips."""
    if flip_x:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_y:
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return img

def apply_opacity(img, opacity):
    """Multiply alpha channel by opacity (0-1)."""
    if opacity >= 1:
        return img
    alpha = img.split()[3].point(lambda p: p * opacity)
    img.putalpha(alpha)
    return img

def rotate_element(img, angle, bg_color=(0,0,0,0)):
    """Rotate image around its center, expanding canvas to fit."""
    if angle == 0:
        return img
    return img.rotate(angle, expand=True, fillcolor=bg_color)

def draw_border(img, border_size, border_color):
    """Draw a border around the image (on the same layer)."""
    if border_size <= 0:
        return img
    draw = ImageDraw.Draw(img)
    draw.rectangle(
        [(0, 0), (img.width-1, img.height-1)],
        outline=parse_color(border_color),
        width=border_size
    )
    return img

# ---------- Main rendering function ----------
def render_page(page_data, root_width, root_height):
    """Render a single Polotno page into a PIL Image."""
    # Page dimensions: if "auto", use root; else convert to int
    raw_w = page_data.get('width', 'auto')
    raw_h = page_data.get('height', 'auto')
    width = root_width if raw_w == 'auto' else int(round(float(raw_w)))
    height = root_height if raw_h == 'auto' else int(round(float(raw_h)))

    # Create base canvas
    bg = page_data.get('background', 'white')
    canvas = None

    # Try background as image URL first
    if isinstance(bg, str) and (bg.startswith('http') or bg.startswith('data:image')):
        try:
            bg_img = load_image_from_src(bg)
            bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
            canvas = Image.new('RGBA', (width, height), (0,0,0,0))
            canvas.paste(bg_img, (0,0), bg_img)
        except Exception as e:
            logger.warning(f"Failed to load background image: {e}. Falling back to color.")
            canvas = None

    if canvas is None:
        bg_color = parse_color(bg) if isinstance(bg, str) else (255,255,255,255)
        canvas = Image.new('RGBA', (width, height), bg_color)

    children = page_data.get('children', [])
    for child in children:
        if not child.get('visible', True):
            continue

        elem_type = child.get('type')
        # Convert coordinates to int (rounding)
        try:
            x = int(round(float(child.get('x', 0))))
            y = int(round(float(child.get('y', 0))))
            elem_w = int(round(float(child.get('width', 100))))
            elem_h = int(round(float(child.get('height', 100))))
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid dimensions for element {child.get('id','unknown')}: {e}")
            continue

        rotation = child.get('rotation', 0)
        opacity = child.get('opacity', 1.0)

        # Create a blank layer for this element
        elem_img = Image.new('RGBA', (elem_w, elem_h), (0,0,0,0))
        draw = ImageDraw.Draw(elem_img)

        try:
            if elem_type == 'image':
                src = child.get('src', '')
                if not src:
                    continue
                img = load_image_from_src(src)
                # Crop
                crop_x = child.get('cropX', 0)
                crop_y = child.get('cropY', 0)
                crop_w = child.get('cropWidth', 1)
                crop_h = child.get('cropHeight', 1)
                img = apply_crop(img, crop_x, crop_y, crop_w, crop_h)
                # Resize
                keep_ratio = child.get('keepRatio', True)
                stretch = child.get('stretchEnabled', True)
                img = resize_image(img, elem_w, elem_h, keep_ratio, stretch)
                # Flip
                flip_x = child.get('flipX', False)
                flip_y = child.get('flipY', False)
                img = apply_flip(img, flip_x, flip_y)
                # Paste onto elem_img
                elem_img.paste(img, (0,0), img)

                # Border (quick win)
                border_size = child.get('borderSize', 0)
                if border_size > 0:
                    border_color = child.get('borderColor', 'black')
                    elem_img = draw_border(elem_img, border_size, border_color)

            elif elem_type == 'text':
                text = child.get('text', '')
                if not text:
                    continue
                font_size = int(round(float(child.get('fontSize', 24))))
                try:
                    # Try common font names
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                align = child.get('align', 'left')
                v_align = child.get('verticalAlign', 'top')
                line_height = child.get('lineHeight', 1.2)
                stroke_width = child.get('strokeWidth', 0)
                stroke_color = child.get('stroke', 'black')
                fill_color = child.get('fill', 'black')

                lines = text.split('\n')
                # Calculate line dimensions
                line_heights = []
                line_widths = []
                total_height = 0
                for line in lines:
                    bbox = font.getbbox(line)
                    lw = bbox[2] - bbox[0]
                    lh = int(font_size * line_height)  # approximate line height
                    line_heights.append(lh)
                    line_widths.append(lw)
                    total_height += lh

                # Vertical alignment
                if v_align == 'top':
                    y_offset = 0
                elif v_align == 'middle':
                    y_offset = (elem_h - total_height) // 2
                else:  # bottom
                    y_offset = elem_h - total_height

                for i, line in enumerate(lines):
                    if align == 'left':
                        x_offset = 0
                    elif align == 'center':
                        x_offset = (elem_w - line_widths[i]) // 2
                    else:  # right
                        x_offset = elem_w - line_widths[i]

                    if stroke_width > 0:
                        draw.text((x_offset, y_offset), line, font=font,
                                  fill=parse_color(stroke_color),
                                  stroke_width=stroke_width,
                                  stroke_fill=parse_color(stroke_color))
                    draw.text((x_offset, y_offset), line, font=font,
                              fill=parse_color(fill_color))
                    y_offset += line_heights[i]

            elif elem_type == 'figure':
                sub_type = child.get('subType', 'rect')
                fill = child.get('fill', 'black')
                stroke = child.get('stroke', 'black')
                stroke_width = child.get('strokeWidth', 0)
                if sub_type in ('rect', 'ellipse'):
                    coords = (0, 0, elem_w, elem_h)
                    if sub_type == 'rect':
                        draw.rectangle(coords, fill=parse_color(fill),
                                       outline=parse_color(stroke) if stroke_width>0 else None,
                                       width=stroke_width)
                    else:
                        draw.ellipse(coords, fill=parse_color(fill),
                                     outline=parse_color(stroke) if stroke_width>0 else None,
                                     width=stroke_width)
                else:
                    continue
            else:
                # Unsupported type – skip
                continue

            # Apply opacity
            if opacity < 1.0:
                elem_img = apply_opacity(elem_img, opacity)

            # Apply rotation
            if rotation != 0:
                elem_img = rotate_element(elem_img, rotation)

            # Paste onto canvas
            canvas.paste(elem_img, (x, y), elem_img)

        except Exception as e:
            logger.warning(f"Error rendering element {child.get('id', 'unknown')}: {e}")
            continue

    return canvas

# ---------- Streamlit App ----------
st.set_page_config(layout="centered")
st.title("Polotno JSON Renderer")
st.write("Upload a Polotno JSON file to render the first page as an image.")

uploaded_file = st.file_uploader("Choose a JSON file", type="json")

if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
    except Exception as e:
        st.error(f"Invalid JSON file: {e}")
        st.stop()

    # Get root canvas dimensions (fallback if page dimensions are "auto")
    try:
        root_width = int(round(float(data.get('width', 1080))))
        root_height = int(round(float(data.get('height', 1080))))
    except (ValueError, TypeError) as e:
        st.error(f"Invalid root width/height: {e}")
        st.stop()

    pages = data.get('pages', [])
    if not pages:
        st.error("No pages found in the JSON.")
        st.stop()

    first_page = pages[0]
    with st.spinner("Rendering page..."):
        try:
            img = render_page(first_page, root_width, root_height)
        except Exception as e:
            st.error(f"Rendering failed: {e}")
            st.stop()

    st.image(img, caption="Rendered Page 1", use_container_width=True)

    # Option to download
    buf = BytesIO()
    img.convert('RGB').save(buf, format='PNG')
    st.download_button("Download as PNG", buf.getvalue(), file_name="page1.png", mime="image/png")