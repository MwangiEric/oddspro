import streamlit as st
import json
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import re
from urllib.parse import unquote, quote
from functools import lru_cache
import os
import numpy as np
import tempfile
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import math

st.set_page_config(page_title="Polotno Studio Pro", layout="wide", page_icon="🎬")

# ============== CONFIGURATION ==============

WOO_STORES = {
    "Avechi": "https://avechi.co.ke",
    "Elix Computers": "https://elixcomputers.co.ke", 
    "Smartphones Kenya": "https://smartphoneskenya.co.ke",
    "Custom": ""
}

WSRV_BASE = "https://wsrv.nl/?url={url}&trim=10&output=png&bg=transparent"

# ============== DATA CLASSES ==============

@dataclass
class Animation:
    type: str  # enter, exit, loop
    name: str  # fade, zoom, slide, rotate, bounce, blur
    delay: float  # seconds
    duration: float  # seconds
    easing: str = "linear"
    
    @classmethod
    def from_polotno(cls, anim: dict):
        return cls(
            type=anim.get('type', 'enter'),
            name=anim.get('name', 'fade'),
            delay=anim.get('delay', 0) / 1000,
            duration=anim.get('duration', 500) / 1000,
            easing=anim.get('easing', 'linear')
        )

@dataclass  
class Product:
    name: str
    price: str
    currency: str
    raw_price: float
    sku: str
    link: str
    images: List[str]
    attributes: Dict[str, str]
    store: str
    
    def to_template_data(self) -> Dict:
        """Convert to template variable dictionary."""
        data = {
            'name': self.name,
            'price': self.price,
            'sku': self.sku,
            'link': self.link,
            'currency': self.currency,
        }
        
        # Add numbered specs
        spec_map = {
            'RAM': 'ram',
            'ROM': 'rom', 
            'STORAGE': 'storage',
            'COLOR': 'color',
            'DISPLAY': 'display',
            'BATTERY': 'battery',
            'CAMERA': 'camera',
            'PROCESSOR': 'processor'
        }
        
        spec_idx = 1
        for attr_key, var_name in spec_map.items():
            if attr_key in self.attributes:
                data[var_name] = self.attributes[attr_key]
                data[f'spec{spec_idx}'] = self.attributes[attr_key]
                spec_idx += 1
        
        # Add wsrv-optimized images
        for i, img_url in enumerate(self.images[:6], 1):
            data[f'image{i}'] = WSRV_BASE.format(url=quote(img_url, safe=''))
            data[f'raw_image{i}'] = img_url
        
        return data

# ============== WOOCOMMERCE API ==============

class WooCommerceAPI:
    def __init__(self, base_url: str, store_name: str = "Custom"):
        self.base_url = base_url.rstrip('/')
        self.api_path = f"{self.base_url}/wp-json/wc/store/v1/products"
        self.store_name = store_name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search(self, keyword: str, limit: int = 3) -> List[Product]:
        """Search products and return list."""
        params = {'search': keyword, 'per_page': limit}
        
        try:
            response = requests.get(
                self.api_path, 
                params=params, 
                headers=self.headers, 
                timeout=15
            )
            response.raise_for_status()
            results = response.json()
            
            products = []
            for item in results:
                raw_price = item['prices']['price']
                currency = item['prices']['currency_code']
                
                # Extract attributes
                attrs = {}
                for attr in item.get('attributes', []):
                    name = attr.get('name', '').upper()
                    values = ", ".join([t['name'] for t in attr.get('terms', [])])
                    attrs[name] = values
                
                product = Product(
                    name=item.get('name', ''),
                    price=f"{currency} {int(raw_price)/100:,.0f}",
                    currency=currency,
                    raw_price=int(raw_price)/100,
                    sku=item.get('sku', ''),
                    link=item.get('permalink', ''),
                    images=[img['src'] for img in item.get('images', [])],
                    attributes=attrs,
                    store=self.store_name
                )
                products.append(product)
            
            return products
            
        except Exception as e:
            st.error(f"API Error ({self.store_name}): {str(e)[:100]}")
            return []

# ============== IMAGE PROCESSING ==============

@lru_cache(maxsize=50)
def get_font(size: int, font_family: str):
    """Cached font loader."""
    try:
        # Try system fonts
        font_map = {
            'Six Caps': '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf',
            'Alata': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'Roboto': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'Bebas Neue': '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
            'Montserrat': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        }
        
        if font_family in font_map and os.path.exists(font_map[font_family]):
            return ImageFont.truetype(font_map[font_family], size)
        
        # Try generic
        return ImageFont.truetype(font_family, size)
    except:
        return ImageFont.load_default()

def load_image_optimized(url: str, width: int = None, height: int = None) -> Optional[Image.Image]:
    """Load image with wsrv optimization."""
    if not url:
        return None
    
    try:
        # Use wsrv for optimization
        if not url.startswith('https://wsrv.nl'):
            url = WSRV_BASE.format(url=quote(url, safe=''))
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        
        img = Image.open(io.BytesIO(response.content))
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Resize if dimensions provided
        if width and height:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        return None

def hex_to_rgba(color_str: str) -> Tuple[int, int, int, int]:
    """Convert color string to RGBA tuple."""
    if not color_str:
        return (0, 0, 0, 255)
    
    try:
        if color_str.startswith('rgba'):
            match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', color_str)
            if match:
                return (
                    int(match.group(1)),
                    int(match.group(2)), 
                    int(match.group(3)),
                    int(float(match.group(4)) * 255)
                )
        
        if color_str.startswith('rgb'):
            match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_str)
            if match:
                return tuple(int(match.group(i)) for i in range(1, 4)) + (255,)
        
        # Hex
        color_str = color_str.lstrip('#')
        if len(color_str) == 6:
            return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(color_str) == 8:
            return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4, 6))
            
    except:
        pass
    
    return (0, 0, 0, 255)

# ============== ANIMATION ENGINE ==============

class AnimationEngine:
    """Handle all animation calculations."""
    
    @staticmethod
    def ease_value(t: float, easing: str) -> float:
        """Apply easing function."""
        if easing == "ease-in":
            return t * t
        elif easing == "ease-out":
            return 1 - (1 - t) * (1 - t)
        elif easing == "ease-in-out":
            return 0.5 - 0.5 * math.cos(t * math.pi)
        elif easing == "bounce":
            if t < 0.5:
                return 2 * t * t
            else:
                return 1 - math.pow(-2 * t + 2, 2) / 2
        return t  # linear
    
    @staticmethod
    def apply_fade(img_array: np.ndarray, progress: float, fade_in: bool = True) -> np.ndarray:
        """Apply fade effect."""
        alpha = progress if fade_in else (1 - progress)
        return (img_array * alpha).astype(np.uint8)
    
    @staticmethod
    def apply_zoom(img_array: np.ndarray, progress: float, zoom_in: bool = True) -> np.ndarray:
        """Apply zoom effect."""
        from scipy import ndimage
        
        if zoom_in:
            scale = 0.5 + 0.5 * progress
        else:
            scale = 1.5 - 0.5 * progress
        
        h, w = img_array.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        
        if new_h < 2 or new_w < 2:
            return img_array
        
        # Zoom
        zoomed = ndimage.zoom(img_array, (scale, scale, 1), order=1)
        
        # Center crop/pad
        zh, zw = zoomed.shape[:2]
        y1 = max(0, (zh - h) // 2)
        x1 = max(0, (zw - w) // 2)
        y2 = min(zh, y1 + h)
        x2 = min(zw, x1 + w)
        
        result = np.zeros_like(img_array)
        dy1 = max(0, (h - zh) // 2)
        dx1 = max(0, (w - zw) // 2)
        
        result[dy1:dy1+(y2-y1), dx1:dx1+(x2-x1)] = zoomed[y1:y2, x1:x2]
        return result
    
    @staticmethod
    def apply_slide(img_array: np.ndarray, progress: float, direction: str = "left") -> np.ndarray:
        """Apply slide effect."""
        h, w = img_array.shape[:2]
        
        if direction == "left":
            offset = int(w * (1 - progress))
        elif direction == "right":
            offset = int(-w * (1 - progress))
        elif direction == "up":
            offset = int(h * (1 - progress))
            result = np.roll(img_array, offset, axis=0)
            return result
        else:  # down
            offset = int(-h * (1 - progress))
            result = np.roll(img_array, offset, axis=0)
            return result
        
        result = np.roll(img_array, offset, axis=1)
        return result
    
    @staticmethod
    def apply_rotate(img_array: np.ndarray, progress: float, clockwise: bool = True) -> np.ndarray:
        """Apply rotation effect."""
        from scipy import ndimage
        
        angle = progress * 360 if clockwise else -progress * 360
        rotated = ndimage.rotate(img_array, angle, reshape=False, order=1)
        return rotated
    
    @staticmethod
    def apply_blur(img_array: np.ndarray, progress: float, blur_in: bool = True) -> np.ndarray:
        """Apply blur effect."""
        from scipy import ndimage
        
        if blur_in:
            sigma = (1 - progress) * 10
        else:
            sigma = progress * 10
        
        if sigma < 0.1:
            return img_array
        
        blurred = ndimage.gaussian_filter(img_array, sigma=(sigma, sigma, 0))
        return blurred.astype(np.uint8)

# ============== RENDERER ==============

class PolotnoRenderer:
    """Main rendering engine."""
    
    def __init__(self, template_data: dict, product_data: dict):
        self.template = template_data
        self.data = product_data
        self.width = int(template_data.get('width', 1080))
        self.height = int(template_data.get('height', 1080))
        self.anim_engine = AnimationEngine()
        
    def extract_variables(self, text: str) -> List[str]:
        """Extract {{variable}} patterns."""
        if not text:
            return []
        return re.findall(r'\{\{(\w+)\}\}', str(text))
    
    def substitute_text(self, template: str) -> str:
        """Replace variables with data."""
        if not template:
            return ""
        
        result = template
        for var in self.extract_variables(template):
            replacement = str(self.data.get(var, ''))
            result = result.replace(f'{{{var}}}', replacement)
        return result
    
    def render_element_static(self, element: dict) -> Optional[Image.Image]:
        """Render single element to PIL Image."""
        elem_type = element.get('type')
        x = int(element.get('x', 0))
        y = int(element.get('y', 0))
        w = int(element.get('width', 100))
        h = int(element.get('height', 100))
        
        # Create full canvas for this element
        canvas = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        
        if elem_type == 'svg':
            draw = ImageDraw.Draw(canvas)
            self._render_svg(draw, element, x, y, w, h)
            
        elif elem_type == 'image':
            self._render_image(canvas, element, x, y, w, h)
            
        elif elem_type == 'text':
            draw = ImageDraw.Draw(canvas)
            self._render_text(draw, element, x, y, w, h)
        
        return canvas
    
    def _render_svg(self, draw: ImageDraw, elem: dict, x: int, y: int, w: int, h: int):
        """Render SVG shape."""
        colors_replace = elem.get('colorsReplace', {})
        fill = (0, 161, 255, 255)
        
        if colors_replace:
            for old, new in colors_replace.items():
                fill = hex_to_rgba(new)
        
        opacity = elem.get('opacity', 1)
        if opacity < 1:
            fill = (*fill[:3], int(fill[3] * opacity))
        
        draw.rectangle([x, y, x+w, y+h], fill=fill[:3])
    
    def _render_image(self, canvas: Image.Image, elem: dict, x: int, y: int, w: int, h: int):
        """Render image element."""
        name = elem.get('name', '')
        
        # Check if variable
        if '{{' in name:
            var = name.replace('{{', '').replace('}}', '')
            url = self.data.get(var)
        else:
            url = elem.get('src', '')
        
        if not url:
            return
        
        img = load_image_optimized(url, w, h)
        if img:
            corner_radius = elem.get('cornerRadius', 0)
            if corner_radius > 0:
                mask = Image.new('L', (w, h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, w, h], radius=corner_radius, fill=255)
                img.putalpha(mask)
            
            canvas.paste(img, (x, y), img)
    
    def _render_text(self, draw: ImageDraw, elem: dict, x: int, y: int, w: int, h: int):
        """Render text element."""
        name = elem.get('name', '')
        text = elem.get('text', '')
        
        # Determine template
        template = name if '{{' in name else text if '{{' in text else (name or text)
        final_text = self.substitute_text(template)
        
        if not final_text.strip():
            return
        
        font_size = elem.get('fontSize', 20)
        font_family = elem.get('fontFamily', 'Roboto')
        fill = hex_to_rgba(elem.get('fill', 'rgba(0,0,0,1)'))
        align = elem.get('align', 'left')
        
        font = get_font(int(font_size), font_family)
        
        # Calculate position
        try:
            bbox = draw.textbbox((0, 0), final_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except:
            tw, th = draw.textsize(final_text, font=font)
        
        if align == 'center':
            tx = x + (w - tw) / 2
        elif align == 'right':
            tx = x + w - tw
        else:
            tx = x
        
        ty = y + (h - th) / 2
        
        # Shadow
        if elem.get('shadowEnabled'):
            sx = elem.get('shadowOffsetX', 0)
            sy = elem.get('shadowOffsetY', 0)
            sc = elem.get('shadowColor', 'black')
            draw.text((tx+sx, ty+sy), final_text, fill=sc, font=font)
        
        draw.text((tx, ty), final_text, fill=fill[:3], font=font)
    
    def render_static(self, base_image: Image.Image = None) -> Image.Image:
        """Render static poster."""
        # Get background
        pages = self.template.get('pages', [])
        if not pages:
            return Image.new('RGB', (self.width, self.height), (255, 255, 255))
        
        page = pages[0]
        bg_color = hex_to_rgba(page.get('background', 'rgba(255,255,255,1)'))
        
        if base_image:
            result = base_image.convert('RGBA')
            # Resize if needed
            if result.size != (self.width, self.height):
                result = result.resize((self.width, self.height), Image.Resampling.LANCZOS)
        else:
            result = Image.new('RGBA', (self.width, self.height), bg_color)
        
        children = page.get('children', [])
        
        # Sort: SVGs, images, text
        def sort_key(c):
            return {'svg': 0, 'image': 1, 'text': 2}.get(c.get('type'), 3)
        
        for child in sorted(children, key=sort_key):
            elem_img = self.render_element_static(child)
            if elem_img:
                result = Image.alpha_composite(result, elem_img)
        
        return result.convert('RGB')
    
    def render_video(self, fps: int = 30, progress_callback=None) -> Optional:
        """Render animated video."""
        try:
            from moviepy import VideoClip
        except:
            from moviepy.editor import VideoClip
        
        pages = self.template.get('pages', [])
        if not pages:
            return None
        
        page = pages[0]
        duration = page.get('duration', 5000) / 1000
        total_frames = int(duration * fps)
        
        # Pre-render all elements
        static_elements = []
        animated_elements = []
        
        for child in page.get('children', []):
            anims = [Animation.from_polotno(a) for a in child.get('animations', []) if a.get('enabled')]
            elem_img = self.render_element_static(child)
            
            if anims and elem_img:
                animated_elements.append((child, anims, elem_img))
            elif elem_img:
                static_elements.append(elem_img)
        
        # Composite static base
        bg_color = hex_to_rgba(page.get('background', 'rgba(255,255,255,1)'))
        base = Image.new('RGBA', (self.width, self.height), bg_color)
        
        for elem in static_elements:
            base = Image.alpha_composite(base, elem)
        
        base_array = np.array(base)
        
        # Generate frames
        frames = []
        
        for frame_idx in range(total_frames):
            time = frame_idx / fps
            frame = base_array.copy()
            
            # Apply animated elements
            for elem_data, anims, elem_img in animated_elements:
                elem_array = np.array(elem_img)
                
                # Find active animation
                for anim in anims:
                    if anim.type in ['enter', 'exit']:
                        if anim.delay <= time <= anim.delay + anim.duration:
                            progress = (time - anim.delay) / anim.duration
                            progress = self.anim_engine.ease_value(progress, anim.easing)
                            elem_array = self._apply_animation(elem_array, anim, progress)
                            break
                        elif time > anim.delay + anim.duration and anim.type == 'enter':
                            break  # Keep full
                        elif time < anim.delay and anim.type == 'exit':
                            break  # Keep full
                    else:  # loop
                        if time >= anim.delay:
                            loop_time = (time - anim.delay) % anim.duration
                            progress = loop_time / anim.duration
                            progress = self.anim_engine.ease_value(progress, anim.easing)
                            elem_array = self._apply_animation(elem_array, anim, progress)
                            break
                
                # Alpha composite
                alpha = elem_array[:, :, 3:4] / 255.0
                frame = (elem_array * alpha + frame * (1 - alpha)).astype(np.uint8)
            
            frames.append(frame[:, :, :3])  # RGB only
            
            if progress_callback and frame_idx % 5 == 0:
                progress_callback(frame_idx / total_frames)
        
        if progress_callback:
            progress_callback(1.0)
        
        # Create video
        def make_frame(t):
            idx = min(int(t * fps), len(frames) - 1)
            return frames[idx]
        
        try:
            clip = VideoClip(make_frame, duration=duration)
            clip = clip.with_fps(fps)
        except:
            clip = VideoClip(make_frame, duration=duration)
            clip.fps = fps
        
        return clip
    
    def _apply_animation(self, img_array: np.ndarray, anim: Animation, progress: float) -> np.ndarray:
        """Apply animation effect."""
        name = anim.name
        
        if name == 'fade':
            if anim.type == 'exit':
                progress = 1 - progress
            return self.anim_engine.apply_fade(img_array, progress)
        
        elif name == 'zoom':
            return self.anim_engine.apply_zoom(img_array, progress, anim.type != 'exit')
        
        elif name == 'slide':
            direction = 'left' if anim.type == 'enter' else 'right'
            return self.anim_engine.apply_slide(img_array, progress, direction)
        
        elif name == 'rotate':
            return self.anim_engine.apply_rotate(img_array, progress)
        
        elif name == 'blur':
            return self.anim_engine.apply_blur(img_array, progress, anim.type != 'exit')
        
        elif name == 'bounce':
            # Custom bounce using sine
            bounce = abs(math.sin(progress * math.pi))
            alpha = bounce
            return self.anim_engine.apply_fade(img_array, alpha)
        
        elif name == 'blink':
            alpha = 0.5 + 0.5 * math.sin(progress * 2 * math.pi)
            return self.anim_engine.apply_fade(img_array, alpha)
        
        return img_array

# ============== STREAMLIT UI ==============

def main():
    st.title("🎬 Polotno Studio Pro")
    st.markdown("**Multi-Store WooCommerce + Animated Video Generator**")
    
    # Session state
    if 'product_data' not in st.session_state:
        st.session_state.product_data = {}
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    
    with st.sidebar:
        st.header("🛒 Product Source")
        
        # Store selection
        store_choice = st.selectbox(
            "Select Store",
            list(WOO_STORES.keys()),
            index=2
        )
        
        if store_choice == "Custom":
            store_url = st.text_input("Store URL", value="https://")
        else:
            store_url = WOO_STORES[store_choice]
            st.caption(f"URL: {store_url}")
        
        # Search
        search_query = st.text_input(
            "🔍 Search Product",
            placeholder="e.g., Samsung S25 Ultra, iPhone 16..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Search", use_container_width=True):
                with st.spinner(f"Searching {store_choice}..."):
                    api = WooCommerceAPI(store_url, store_choice)
                    results = api.search(search_query, limit=5)
                    st.session_state.search_results = results
        
        with col2:
            if st.button("Clear", use_container_width=True):
                st.session_state.search_results = []
                st.session_state.product_data = {}
        
        # Results
        if st.session_state.search_results:
            st.subheader("Select Product:")
            for i, prod in enumerate(st.session_state.search_results):
                with st.container(border=True):
                    st.write(f"**{prod.name}**")
                    st.write(f"💰 {prod.price}")
                    if prod.images:
                        st.image(prod.images[0], width=100)
                    
                    if st.button(f"Select #{i+1}", key=f"select_{i}", use_container_width=True):
                        st.session_state.product_data = prod.to_template_data()
                        st.session_state.selected_product = prod
                        st.rerun()
        
        st.divider()
        st.header("📁 Template")
        
        # Base image
        base_image_file = st.file_uploader(
            "Base Image (Optional)",
            type=['png', 'jpg', 'jpeg'],
            help="Upload background image or leave empty to use JSON background"
        )
        
        # JSON input
        json_method = st.radio("JSON Input", ["Upload", "Paste"])
        
        template_data = None
        if json_method == "Upload":
            json_file = st.file_uploader("Upload JSON", type=['json'])
            if json_file:
                template_data = json.load(json_file)
        else:
            json_text = st.text_area("Paste JSON", height=150)
            if json_text:
                try:
                    template_data = json.loads(json_text)
                except:
                    st.error("Invalid JSON")
        
        st.divider()
        st.header("⚙️ Output")
        
        output_type = st.radio("Format", ["Static PNG", "Animated MP4"])
        
        if output_type == "Animated MP4":
            fps = st.slider("FPS", 15, 60, 30)
            quality = st.select_slider("Quality", ["Draft", "Good", "Best"], "Good")
        
        generate = st.button("🚀 Generate", type="primary", use_container_width=True)
    
    # Main area
    col_edit, col_preview = st.columns([1, 1.5])
    
    with col_edit:
        st.subheader("📝 Template Variables")
        
        if template_data:
            # Detect variables
            renderer = PolotnoRenderer(template_data, {})
            pages = template_data.get('pages', [])
            
            # Collect all variables
            all_vars = set()
            for page in pages:
                for child in page.get('children', []):
                    for field in [child.get('name', ''), child.get('text', '')]:
                        all_vars.update(renderer.extract_variables(field))
            
            # Show editable fields
            if all_vars:
                st.write(f"**{len(all_vars)} variables detected**")
                
                # Group by type
                text_vars = [v for v in all_vars if not v.startswith('image')]
                image_vars = [v for v in all_vars if v.startswith('image')]
                
                # Text variables
                for var in sorted(text_vars):
                    current = st.session_state.product_data.get(var, '')
                    new_val = st.text_input(
                        f"{{{var}}}",
                        value=str(current),
                        key=f"var_{var}"
                    )
                    st.session_state.product_data[var] = new_val
                
                # Image variables
                for var in sorted(image_vars):
                    st.markdown(f"**{{{var}}}**")
                    current = st.session_state.product_data.get(var, '')
                    
                    # Show preview
                    if current:
                        st.image(current, width=150)
                    
                    # Allow URL edit
                    raw_key = f"raw_{var}"
                    raw_url = st.session_state.product_data.get(raw_key, '')
                    
                    new_url = st.text_input(
                        "Image URL",
                        value=raw_url,
                        key=f"url_{var}",
                        label_visibility="collapsed"
                    )
                    
                    if new_url:
                        st.session_state.product_data[raw_key] = new_url
                        st.session_state.product_data[var] = WSRV_BASE.format(url=quote(new_url, safe=''))
            else:
                st.info("No template variables found")
        else:
            st.info("Upload or paste a template JSON")
    
    with col_preview:
        st.subheader("🖼️ Preview")
        
        if generate and template_data:
            # Load base image
            base_img = None
            if base_image_file:
                base_img = Image.open(base_image_file)
            
            renderer = PolotnoRenderer(template_data, st.session_state.product_data)
            
            if output_type == "Static PNG":
                with st.spinner("Rendering..."):
                    result = renderer.render_static(base_img)
                    st.image(result, use_container_width=True)
                    
                    # Download
                    buf = io.BytesIO()
                    result.save(buf, format='PNG')
                    st.download_button(
                        "⬇️ Download PNG",
                        buf.getvalue(),
                        file_name="poster.png",
                        mime="image/png"
                    )
            
            else:  # Video
                progress = st.progress(0.0)
                status = st.empty()
                
                with st.spinner("Rendering video..."):
                    status.text("Generating frames...")
                    
                    def update(p):
                        progress.progress(min(1.0, p))
                    
                    clip = renderer.render_video(fps, update)
                    
                    if clip:
                        status.text("Encoding...")
                        
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                            tmp_path = tmp.name
                        
                        preset = {'Draft': 'ultrafast', 'Good': 'medium', 'Best': 'slow'}[quality]
                        
                        try:
                            clip.write_videofile(
                                tmp_path, 
                                codec='libx264', 
                                audio=False,
                                preset=preset,
                                threads=4,
                                logger=None
                            )
                        except:
                            clip.write_videofile(tmp_path, codec='libx264', audio=False, verbose=False)
                        
                        with open(tmp_path, 'rb') as f:
                            video_bytes = f.read()
                        
                        progress.empty()
                        status.empty()
                        
                        st.video(video_bytes)
                        st.download_button(
                            "⬇️ Download MP4",
                            video_bytes,
                            file_name="animated_poster.mp4",
                            mime="video/mp4"
                        )
                        
                        os.unlink(tmp_path)

if __name__ == "__main__":
    main()
