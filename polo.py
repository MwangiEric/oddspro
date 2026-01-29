
# Create the complete single-file Streamlit app
streamlit_code = '''import streamlit as st
import json
import base64
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import copy

st.set_page_config(page_title="Polotno → PIL Transformer", layout="wide")

# Initialize session state
if 'schema' not in st.session_state:
    st.session_state.schema = None
if 'original_json' not in st.session_state:
    st.session_state.original_json = None
if 'rendered_image' not in st.session_state:
    st.session_state.rendered_image = None
if 'selected_element' not in st.session_state:
    st.session_state.selected_element = None

def load_image_from_source(src):
    """Load image from URL or base64"""
    if not src:
        return None
    
    try:
        # Check if base64 data URI
        if src.startswith('data:image'):
            base64_data = src.split(',')[1]
            img_data = base64.b64decode(base64_data)
            return Image.open(BytesIO(img_data)).convert('RGBA')
        
        # Check if raw base64 without data URI
        elif len(src) > 100 and not src.startswith('http'):
            try:
                img_data = base64.b64decode(src)
                return Image.open(BytesIO(img_data)).convert('RGBA')
            except:
                pass
        
        # URL
        if src.startswith('http'):
            response = requests.get(src, timeout=10)
            return Image.open(BytesIO(response.content)).convert('RGBA')
            
    except Exception as e:
        st.error(f"Failed to load image: {str(e)}")
        return None
    
    return None

def transform_polotno_to_schema(polotno_json):
    """Convert Polotno JSON to simplified schema"""
    
    page = polotno_json['pages'][0]
    canvas_width = page.get('width', 1080)
    canvas_height = page.get('height', 1920)
    
    layers = []
    
    for child in page.get('children', []):
        element_id = child.get('id', f"elem_{len(layers)}")
        element_type = child.get('type', 'unknown')
        
        # Skip unsupported types
        if element_type not in ['text', 'image']:
            continue
        
        layer = {
            'id': element_id,
            'type': element_type,
            'x': float(child.get('x', 0)),
            'y': float(child.get('y', 0)),
            'width': float(child.get('width', 100)),
            'height': float(child.get('height', 100)),
            'rotation': float(child.get('rotation', 0)),
            'opacity': float(child.get('opacity', 1)),
        }
        
        if element_type == 'text':
            layer.update({
                'text': child.get('text', ''),
                'font_size': int(child.get('fontSize', 32)),
                'color': child.get('fill', '#000000'),
                'align': child.get('align', 'left'),
                'font_family': child.get('fontFamily', 'Arial'),
                'role': detect_role(element_id, child)
            })
            
        elif element_type == 'image':
            src = child.get('src', '')
            layer.update({
                'src': src,
                'is_base64': src.startswith('data:image') or (len(src) > 100 and not src.startswith('http')),
                'role': 'bg_image' if element_id.startswith('bg') else 'dynamic_image'
            })
        
        layers.append(layer)
    
    return {
        'template_id': 'test_template',
        'canvas': {
            'width': canvas_width,
            'height': canvas_height
        },
        'layers': layers
    }

def detect_role(element_id, child):
    """Detect semantic role from ID and content"""
    id_lower = element_id.lower()
    
    if any(x in id_lower for x in ['bg', 'background']):
        return 'bg_image'
    if any(x in id_lower for x in ['headline', 'title', 'main']):
        return 'headline'
    if any(x in id_lower for x in ['device', 'phone', 'product']):
        return 'device_name'
    if any(x in id_lower for x in ['price', 'cost', 'ksh', '$']):
        return 'price'
    if any(x in id_lower for x in ['spec', 'feature']):
        return 'spec'
    
    # Detect from content
    if child.get('type') == 'text':
        text = child.get('text', '').lower()
        if any(x in text for x in ['$', 'ksh', 'usd', 'price']):
            return 'price'
        if child.get('fontSize', 0) > 50:
            return 'headline'
    
    return 'text'

def get_font(size):
    """Get best available font"""
    try:
        # Try common fonts
        for font_name in ['DejaVuSans-Bold.ttf', 'Arial-Bold.ttf', 'Helvetica-Bold.ttf']:
            try:
                return ImageFont.truetype(font_name, size)
            except:
                continue
    except:
        pass
    return ImageFont.load_default()

def render_schema(schema, data_overrides=None):
    """Render schema to PIL Image"""
    
    canvas_width = schema['canvas']['width']
    canvas_height = schema['canvas']['height']
    
    # Create transparent canvas
    canvas = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 255))
    
    data_overrides = data_overrides or {}
    
    for layer in schema['layers']:
        element_id = layer['id']
        
        # Apply overrides if any
        x = data_overrides.get(f"{element_id}_x", layer['x'])
        y = data_overrides.get(f"{element_id}_y", layer['y'])
        width = data_overrides.get(f"{element_id}_w", layer['width'])
        height = data_overrides.get(f"{element_id}_h", layer['height'])
        
        try:
            if layer['type'] == 'image':
                # Load image
                src = layer.get('src', '')
                if not src:
                    continue
                    
                img = load_image_from_source(src)
                if img:
                    # Resize
                    img = img.resize((int(width), int(height)), Image.Resampling.LANCZOS)
                    
                    # Handle rotation
                    if layer.get('rotation', 0) != 0:
                        img = img.rotate(-layer['rotation'], expand=True, resample=Image.Resampling.BICUBIC)
                    
                    # Paste with opacity
                    if layer.get('opacity', 1) < 1:
                        alpha = img.split()[-1]
                        alpha = alpha.point(lambda p: int(p * layer['opacity']))
                        img.putalpha(alpha)
                    
                    canvas.paste(img, (int(x), int(y)), img)
                else:
                    # Placeholder for failed image
                    draw = ImageDraw.Draw(canvas)
                    draw.rectangle([x, y, x+width, y+height], outline='red', width=3)
                    draw.text((x+10, y+10), f"IMG\\n{element_id}", fill='red')
                    
            elif layer['type'] == 'text':
                draw = ImageDraw.Draw(canvas)
                
                text = data_overrides.get(element_id, layer.get('text', ''))
                font_size = int(layer.get('font_size', 32))
                color = layer.get('color', '#000000')
                align = layer.get('align', 'left')
                
                font = get_font(font_size)
                
                # Calculate text position
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                # Alignment
                text_x = x
                if align == 'center':
                    text_x = x + (width - text_w) / 2
                elif align == 'right':
                    text_x = x + width - text_w
                
                text_y = y + (height - text_h) / 2
                
                # Draw
                draw.text((text_x, text_y), text, font=font, fill=color)
                
        except Exception as e:
            st.error(f"Error rendering {element_id}: {str(e)}")
    
    return canvas

# UI
st.title("🎨 Polotno → PIL Transformer")
st.markdown("Paste Polotno JSON or upload file to transform and render")

# Input section
col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Input")
    
    # File upload
    uploaded_file = st.file_uploader("Upload Polotno JSON", type=['json'])
    
    # Text paste
    json_text = st.text_area("Or paste JSON here", height=300, 
                             placeholder='{"pages": [{"width": 1080, "height": 1920, "children": [...]}]}')
    
    # Load button
    if st.button("🔄 Load & Transform", type="primary"):
        try:
            if uploaded_file:
                content = uploaded_file.read().decode('utf-8')
            else:
                content = json_text
            
            polotno_json = json.loads(content)
            st.session_state.original_json = polotno_json
            st.session_state.schema = transform_polotno_to_schema(polotno_json)
            st.success(f"✅ Loaded {len(st.session_state.schema['layers'])} layers")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    st.subheader("📋 Schema Preview")
    
    if st.session_state.schema:
        # Show canvas info
        canvas = st.session_state.schema['canvas']
        st.info(f"Canvas: {canvas['width']}x{canvas['height']}")
        
        # Show layers
        for i, layer in enumerate(st.session_state.schema['layers']):
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.text(f"{layer['id']} ({layer['type']})")
            with cols[1]:
                st.text(f"{layer['x']:.0f},{layer['y']:.0f}")
            with cols[2]:
                st.text(f"{layer['width']:.0f}x{layer['height']:.0f}")
            with cols[3]:
                if st.button("✏️", key=f"edit_{i}"):
                    st.session_state.selected_element = i
    else:
        st.info("Load JSON to see schema")

# Editor section
if st.session_state.schema:
    st.divider()
    st.subheader("🎛️ Element Editor & Renderer")
    
    col_edit, col_preview = st.columns([1, 2])
    
    with col_edit:
        st.markdown("### Edit Elements")
        
        # Global overrides
        st.markdown("**Global Data Overrides**")
        override_text = st.text_area("Text overrides (JSON)", 
                                    value='{}',
                                    help='{"headline": "New Text", "price": "$599"}')
        
        # Element-specific editor
        if st.session_state.selected_element is not None:
            idx = st.session_state.selected_element
            layer = st.session_state.schema['layers'][idx]
            
            st.markdown(f"**Editing: {layer['id']}**")
            
            # Position controls
            new_x = st.number_input("X", value=float(layer['x']), step=10.0)
            new_y = st.number_input("Y", value=float(layer['y']), step=10.0)
            new_w = st.number_input("Width", value=float(layer['width']), step=10.0)
            new_h = st.number_input("Height", value=float(layer['height']), step=10.0)
            
            # Text override
            if layer['type'] == 'text':
                new_text = st.text_input("Text", value=layer.get('text', ''))
            else:
                new_text = None
            
            # Apply button
            if st.button("💾 Apply Changes"):
                layer['x'] = new_x
                layer['y'] = new_y
                layer['width'] = new_w
                layer['height'] = new_h
                if new_text is not None:
                    layer['text'] = new_text
                st.session_state.selected_element = None
                st.rerun()
    
    with col_preview:
        st.markdown("### Preview")
        
        # Parse overrides
        try:
            text_overrides = json.loads(override_text) if override_text else {}
        except:
            text_overrides = {}
            st.error("Invalid JSON in overrides")
        
        # Render button
        if st.button("🎨 Render Image", type="primary"):
            with st.spinner("Rendering..."):
                img = render_schema(st.session_state.schema, text_overrides)
                st.session_state.rendered_image = img
        
        # Display result
        if st.session_state.rendered_image:
            st.image(st.session_state.rendered_image, use_container_width=True)
            
            # Download
            buf = BytesIO()
            st.session_state.rendered_image.convert('RGB').save(buf, format='PNG')
            st.download_button(
                "⬇️ Download PNG",
                buf.getvalue(),
                "rendered.png",
                "image/png"
            )
        else:
            st.info("Click 'Render Image' to generate preview")

# Debug section
if st.session_state.original_json:
    with st.expander("🔍 Debug: Original JSON"):
        st.json(st.session_state.original_json)
    
    with st.expander("🔍 Debug: Transformed Schema"):
        st.json(st.session_state.schema)
'''

# Save to file
output_path = '/mnt/kimi/output/polotno_transformer_app.py'
with open(output_path, 'w') as f:
    f.write(streamlit_code)

print(f"✅ Single-file Streamlit app saved to: {output_path}")
print(f"\n📦 File size: {len(streamlit_code)} characters")
print("\n🚀 To deploy to Streamlit Cloud:")
print("   1. Upload this file to GitHub")
print("   2. Connect repo to streamlit.io")
print("   3. Set main file path: polotno_transformer_app.py")
print("\n💻 To run locally:")
print(f"   streamlit run {output_path}")