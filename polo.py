# polotno_to_pil_transparent_svg.py
import streamlit as st
import json
import base64
import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO
import math

# Optional: cairosvg for real SVG → PNG conversion (with alpha)
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False
    st.info("Install cairosvg for full SVG support: pip install cairosvg")

st.set_page_config(page_title="Polotno → Transparent PIL + SVG", layout="wide")

# Session state
for key, val in {
    'original_json': None,
    'schema': None,
    'rendered_image': None,
    'text_overrides': {},
    'transparent_bg': True
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ───────────────────────────────────────────────
# Utilities
# ───────────────────────────────────────────────

def safe_int(v, d=0): 
    try: return int(float(v))
    except: return d

def safe_float(v, d=0.0): 
    try: return float(v)
    except: return d

def load_image(src, target_w=None, target_h=None):
    """Load raster or render SVG with alpha"""
    if not src or not isinstance(src, str): return None

    try:
        # SVG handling
        if 'svg' in src.lower() or src.startswith('data:image/svg'):
            if not CAIROSVG_AVAILABLE:
                st.warning("cairosvg not installed → SVG placeholder")
                return create_svg_placeholder(target_w or 200, target_h or 200)
            
            # Normalize to bytes
            if src.startswith('data:image/svg'):
                _, encoded = src.split(',', 1)
                if 'base64' in src:
                    svg_bytes = base64.b64decode(encoded)
                else:
                    svg_bytes = encoded.encode('utf-8')
            else:
                svg_bytes = src.encode('utf-8')

            png_bytes = cairosvg.svg2png(
                bytestring=svg_bytes,
                output_width=target_w,
                output_height=target_h,
                scale=2.0  # higher quality
            )
            return Image.open(BytesIO(png_bytes)).convert('RGBA')

        # Raster: data URI
        if src.startswith('data:image'):
            _, encoded = src.split(',', 1)
            data = base64.b64decode(encoded)
            img = Image.open(BytesIO(data)).convert('RGBA')
            if target_w and target_h:
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

        # Plain base64
        if len(src) > 100 and not src.startswith('http'):
            data = base64.b64decode(src)
            img = Image.open(BytesIO(data)).convert('RGBA')
            if target_w and target_h:
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

        # HTTP URL
        if src.startswith(('http://', 'https://')):
            r = requests.get(src, timeout=12)
            r.raise_for_status()
            ct = r.headers.get('content-type', '').lower()
            if 'svg' in ct:
                return load_image(r.text, target_w, target_h)  # recurse for SVG content
            img = Image.open(BytesIO(r.content)).convert('RGBA')
            if target_w and target_h:
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            return img

    except Exception as e:
        st.warning(f"Load failed: {str(e)}")
    return None

def create_svg_placeholder(w, h):
    """Fallback placeholder for missing cairosvg"""
    img = Image.new('RGBA', (w, h), (200, 200, 200, 180))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "SVG\n(install cairosvg)", fill=(80,80,80,255))
    return img

def get_font(size):
    for name in ['arial.ttf', 'DejaVuSans.ttf', 'FreeSans.ttf', 'NotoSans-Regular.ttf']:
        try: return ImageFont.truetype(name, size)
        except: continue
    return ImageFont.load_default()

def transform_polotno(pjson):
    pages = pjson.get('pages', [])
    if not pages: raise ValueError("No pages")

    page = pages[0]
    w = max(safe_int(page.get('width'), 1200), 200)
    h = max(safe_int(page.get('height'), 628), 200)

    layers = []
    for i, el in enumerate(page.get('children', [])):
        if not isinstance(el, dict): continue
        t = el.get('type')
        if t not in ['text', 'image', 'svg', 'shape', 'figure', 'line']: continue

        layer = {
            'id': str(el.get('id', f'l_{i}')),
            'type': t,
            'x': safe_float(el.get('x'), 0),
            'y': safe_float(el.get('y'), 0),
            'width': safe_float(el.get('width'), 200),
            'height': safe_float(el.get('height'), 200),
            'rotation': safe_float(el.get('rotation'), 0),
            'opacity': safe_float(el.get('opacity'), 1.0),
        }

        if t == 'text':
            layer.update({
                'text': str(el.get('text', '')),
                'font_size': safe_int(el.get('fontSize'), 32),
                'color': str(el.get('fill', '#000')),
                'align': str(el.get('align', 'left')),
            })
        elif t in ('image', 'svg'):
            src = el.get('src') or ''
            if src: layer['src'] = src
        elif t in ('shape', 'figure'):
            layer.update({
                'subtype': str(el.get('subType') or el.get('subtype', 'rect')),
                'fill': str(el.get('fill', '#888')),
                'stroke': str(el.get('stroke')),
                'strokeWidth': safe_float(el.get('strokeWidth'), 2),
                'radius': safe_float(el.get('cornerRadius'), 0),
            })
        elif t == 'line':
            layer.update({
                'color': str(el.get('color', '#000')),
                'strokeWidth': safe_float(el.get('strokeWidth'), 2),
            })

        layers.append(layer)

    return {'canvas': {'width': w, 'height': h}, 'layers': layers}

def render_schema(schema, overrides=None, transparent_bg=True):
    overrides = overrides or {}
    c = schema['canvas']
    w, h = safe_int(c['width'], 1200), safe_int(c['height'], 628)

    canvas = Image.new('RGBA', (w, h), (0,0,0,0) if transparent_bg else (255,255,255,255))
    draw = ImageDraw.Draw(canvas)

    for layer in schema.get('layers', []):
        try:
            t = layer['type']
            x, y = int(layer['x']), int(layer['y'])
            lw, lh = int(layer['width']), int(layer['height'])
            op = int(layer['opacity'] * 255)

            if t in ('image', 'svg'):
                img = load_image(layer.get('src'), lw, lh)
                if img:
                    rot = layer.get('rotation', 0)
                    if rot: img = img.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)

                    if op < 255:
                        a = img.getchannel('A')
                        a = a.point(lambda p: int(p * op / 255))
                        img.putalpha(a)

                    canvas.paste(img, (x, y), img)

            elif t == 'text':
                txt = overrides.get(layer['id'], layer.get('text', ''))
                if not txt: continue

                font = get_font(layer['font_size'])
                col = layer['color']

                bbox = draw.textbbox((0,0), txt, font=font)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]

                tx = x
                if layer['align'] == 'center': tx += (lw - tw) // 2
                elif layer['align'] == 'right': tx += lw - tw

                ty = y + (lh - th) // 2

                if op == 255:
                    draw.text((tx, ty), txt, font=font, fill=col)
                else:
                    ti = Image.new('RGBA', (tw+40, th+40), (0,0,0,0))
                    td = ImageDraw.Draw(ti)
                    td.text((20,20), txt, font=font, fill=col)
                    ta = ti.getchannel('A')
                    ta = ta.point(lambda p: int(p * op / 255))
                    ti.putalpha(ta)
                    canvas.paste(ti, (tx-20, ty-20), ti)

            # Shape/figure/line can be added here similarly (draw_shape function from previous)

        except Exception as e:
            st.warning(f"Layer {layer.get('id','?')} failed: {str(e)}")

    return canvas

# ───────────────────────────────────────────────
# UI
# ───────────────────────────────────────────────

st.title("Polotno JSON → Transparent PNG Renderer (with SVG)")
st.markdown("Supports full alpha transparency + SVG rendering (install cairosvg for best results)")

col1, col2 = st.columns([1,1])

with col1:
    st.subheader("Input")
    up = st.file_uploader("Upload JSON", type="json")
    raw = st.text_area("Paste JSON", height=400)

    if st.button("Load & Transform", type="primary"):
        content = up.read().decode('utf-8') if up else raw.strip()
        if content:
            try:
                data = json.loads(content)
                st.session_state.original_json = data
                st.session_state.schema = transform_polotno(data)
                st.success(f"Loaded {len(st.session_state.schema['layers'])} layers")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

with col2:
    st.subheader("Render")
    st.checkbox("Transparent background", value=True, key="trans_bg")

    if st.session_state.schema and st.button("Render", type="primary"):
        with st.spinner("Rendering..."):
            img = render_schema(
                st.session_state.schema,
                transparent_bg=st.session_state.trans_bg
            )
            st.session_state.rendered_image = img

    if st.session_state.rendered_image:
        st.image(st.session_state.rendered_image, use_column_width=True)

        buf = BytesIO()
        st.session_state.rendered_image.save(buf, format="PNG")
        st.download_button(
            "Download Transparent PNG",
            buf.getvalue(),
            "polotno_render.png",
            "image/png"
        )

with st.expander("Debug JSON"):
    if st.session_state.original_json: st.json(st.session_state.original_json)
    if st.session_state.schema: st.json(st.session_state.schema)