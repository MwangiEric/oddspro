import streamlit as st
import json
import requests
from PIL import Image, ImageDraw, ImageFont
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

# ============== FONT HANDLING ==============

def get_font(size: int, font_family: str = "Arial"):
    """
    Load font with fallback chain:
    1. Requested font from system
    2. Poppins.ttf from local folder
    3. DejaVu Sans
    4. Arial
    5. Default
    """
    # Clean font name
    font_family = font_family.replace('"', '').replace("'", "").strip()
    
    # Try exact font first
    try:
        return ImageFont.truetype(font_family, int(size))
    except:
        pass
    
    # Try local Poppins
    local_fonts = [
        "Poppins.ttf",
        "Poppins-Regular.ttf",
        "poppins.ttf",
        "./Poppins.ttf",
        "./poppins.ttf"
    ]
    for font_file in local_fonts:
        if os.path.exists(font_file):
            try:
                return ImageFont.truetype(font_file, int(size))
            except:
                pass
    
    # Try system fonts with mapped names
    font_map = {
        'poppins': ['Poppins-Regular.ttf', 'Poppins.ttf'],
        'roboto': ['Roboto-Regular.ttf', 'DejaVuSans.ttf'],
        'arial': ['Arial.ttf', 'DejaVuSans.ttf'],
        'dejavu': ['DejaVuSans.ttf'],
        'six caps': ['DejaVuSansCondensed-Bold.ttf'],
        'alata': ['DejaVuSans-Bold.ttf'],
        'bebas neue': ['DejaVuSansCondensed-Bold.ttf'],
        'montserrat': ['DejaVuSans.ttf'],
        'inter': ['DejaVuSans.ttf'],
        'open sans': ['DejaVuSans.ttf'],
    }
    
    # Check mapped names
    font_lower = font_family.lower()
    if font_lower in font_map:
        for fallback in font_map[font_lower]:
            try:
                paths = [
                    f"/usr/share/fonts/truetype/dejavu/{fallback}",
                    f"/usr/share/fonts/truetype/{fallback}",
                    f"/System/Library/Fonts/{fallback}",
                    f"/Windows/Fonts/{fallback}",
                    fallback
                ]
                for path in paths:
                    if os.path.exists(path):
                        return ImageFont.truetype(path, int(size))
            except:
                continue
    
    # Try common system paths
    system_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    
    for path in system_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, int(size))
            except:
                continue
    
    # Fallback to default
    return ImageFont.load_default()

# ============== DATA CLASSES ==============

@dataclass
class Animation:
    type: str
    name: str
    delay: float
    duration: float
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
        data = {
            'name': self.name,
            'price': self.price,
            'sku': self.sku,
            'link': self.link,
            'currency': self.currency,
        }
        
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

def load_image_optimized(url: str, width: int = None, height: int = None) -> Optional[Image.Image]:
    if not url:
        return None
    
    try:
        if not url.startswith('https://wsrv.nl'):
            url = WSRV_BASE.format(url=quote(url, safe=''))
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        
        img = Image.open(io.BytesIO(response.content))
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        if width and height:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        st.warning(f"Failed to load image: {str(e)[:50]}")
        return None

def hex_to_rgba(color_str: str) -> Tuple[int, int, int, int]:
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
        
        color_str = color_str.lstrip('#')
        if len(color_str) == 6:
            return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(color_str) == 8:
            return tuple(int(color_str[i:i+2], 16) for i in (0, 2, 4, 6))
            
    except:
        pass
    
    return (0, 0, 0, 255)

def extract_variables(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r'\{\{(\w+)\}\}', str(text))

def is_image_variable(var_name: str) -> bool:
    return var_name.startswith('image') and var_name[5:].isdigit()

# ============== RENDERER ==============

class PolotnoRenderer:
    def __init__(self, template_data: dict, product_data: dict):
        self.template = template_data
        self.data = product_data
        self.width = int(template_data.get('width', 1080))
        self.height = int(template_data.get('height', 1080))
        
    def substitute_text(self, template: str) -> str:
        if not template:
            return ""
        
        result = template
        for var in extract_variables(template):
            replacement = str(self.data.get(var, ''))
            result = result.replace(f'{{{var}}}', replacement)
        return result
    
    def parse_text_style(self, element: dict) -> dict:
        """Extract all text styling from element."""
        style = {
            'fontSize': element.get('fontSize', 30),
            'fontFamily': element.get('fontFamily', 'Arial'),
            'fontStyle': element.get('fontStyle', 'normal'),
            'fontWeight': element.get('fontWeight', 'normal'),
            'fill': element.get('fill', 'rgba(0,0,0,1)'),
            'align': element.get('align', 'left'),
            'verticalAlign': element.get('verticalAlign', 'top'),
            'lineHeight': element.get('lineHeight', 1.2),
            'letterSpacing': element.get('letterSpacing', 0),
            'textDecoration': element.get('textDecoration', ''),
            'textTransform': element.get('textTransform', 'none'),
            'stroke': element.get('stroke', 'black'),
            'strokeWidth': element.get('strokeWidth', 0),
            'shadowEnabled': element.get('shadowEnabled', False),
            'shadowColor': element.get('shadowColor', 'black'),
            'shadowBlur': element.get('shadowBlur', 5),
            'shadowOffsetX': element.get('shadowOffsetX', 0),
            'shadowOffsetY': element.get('shadowOffsetY', 0),
            'opacity': element.get('opacity', 1),
        }
        return style
    
    def apply_text_transform(self, text: str, transform: str) -> str:
        """Apply text transformation."""
        if transform == 'uppercase':
            return text.upper()
        elif transform == 'lowercase':
            return text.lower()
        elif transform == 'capitalize':
            return text.title()
        return text
    
    def render_element(self, element: dict, to_numpy: bool = False):
        """Render single element."""
        elem_type = element.get('type')
        x = int(element.get('x', 0))
        y = int(element.get('y', 0))
        w = int(element.get('width', 100))
        h = int(element.get('height', 100))
        
        # Create full canvas
        if to_numpy:
            canvas = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        else:
            canvas = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        
        if elem_type == 'svg':
            self._render_svg(canvas, element, x, y, w, h, to_numpy)
        elif elem_type == 'image':
            self._render_image(canvas, element, x, y, w, h, to_numpy)
        elif elem_type == 'text':
            self._render_text(canvas, element, x, y, w, h, to_numpy)
        
        return canvas
    
    def _render_svg(self, canvas, element: dict, x: int, y: int, w: int, h: int, to_numpy: bool):
        """Render SVG rectangle."""
        colors_replace = element.get('colorsReplace', {})
        fill = (0, 161, 255, 255)
        
        if colors_replace:
            for old, new in colors_replace.items():
                fill = hex_to_rgba(new)
        
        opacity = element.get('opacity', 1)
        if opacity < 1:
            fill = (*fill[:3], int(fill[3] * opacity))
        
        if to_numpy:
            # Draw on numpy array
            from PIL import Image as PILImage
            tmp = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(tmp)
            draw.rectangle([x, y, x+w, y+h], fill=fill[:3])
            arr = np.array(tmp)
            canvas[:] = arr
        else:
            draw = ImageDraw.Draw(canvas)
            draw.rectangle([x, y, x+w, y+h], fill=fill[:3])
    
    def _render_image(self, canvas, element: dict, x: int, y: int, w: int, h: int, to_numpy: bool):
        """Render image element."""
        name = element.get('name', '')
        
        if '{{' in name:
            var = name.replace('{{', '').replace('}}', '')
            url = self.data.get(var)
        else:
            url = element.get('src', '')
        
        if not url:
            return
        
        img = load_image_optimized(url, w, h)
        if not img:
            return
        
        corner_radius = element.get('cornerRadius', 0)
        if corner_radius > 0:
            mask = Image.new('L', (w, h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, w, h], radius=corner_radius, fill=255)
            img.putalpha(mask)
        
        if to_numpy:
            # Convert to numpy and place
            img_array = np.array(img)
            canvas[y:y+h, x:x+w] = img_array
        else:
            if img.mode == 'RGBA':
                canvas.paste(img, (x, y), img)
            else:
                canvas.paste(img, (x, y))
    
    def _render_text(self, canvas, element: dict, x: int, y: int, w: int, h: int, to_numpy: bool):
        """Render text with full style support."""
        name = element.get('name', '')
        text = element.get('text', '')
        
        # Get template
        template = name if '{{' in name else text if '{{' in text else (name or text)
        final_text = self.substitute_text(template)
        
        if not final_text.strip():
            return
        
        # Get styles
        style = self.parse_text_style(element)
        
        # Apply text transform
        final_text = self.apply_text_transform(final_text, style['textTransform'])
        
        # Load font
        font = get_font(int(style['fontSize']), style['fontFamily'])
        
        # Get color
        fill = hex_to_rgba(style['fill'])
        opacity = style['opacity']
        if opacity < 1:
            fill = (*fill[:3], int(fill[3] * opacity))
        
        # Create temp image for text rendering
        from PIL import Image as PILImage
        text_layer = PILImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        # Handle multiline text
        lines = final_text.split('\n')
        line_height = int(style['fontSize'] * style['lineHeight'])
        
        # Calculate total height
        total_height = len(lines) * line_height
        
        # Vertical alignment
        if style['verticalAlign'] == 'middle':
            start_y = y + (h - total_height) / 2
        elif style['verticalAlign'] == 'bottom':
            start_y = y + h - total_height
        else:
            start_y = y
        
        current_y = start_y
        
        for line in lines:
            # Get line width
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
            except:
                line_width, _ = draw.textsize(line, font=font)
            
            # Horizontal alignment
            if style['align'] == 'center':
                line_x = x + (w - line_width) / 2
            elif style['align'] == 'right':
                line_x = x + w - line_width
            else:
                line_x = x
            
            # Letter spacing
            if style['letterSpacing'] != 0:
                # Draw each character separately
                char_x = line_x
                for char in line:
                    try:
                        char_bbox = draw.textbbox((0, 0), char, font=font)
                        char_width = char_bbox[2] - char_bbox[0]
                    except:
                        char_width, _ = draw.textsize(char, font=font)
                    
                    # Shadow
                    if style['shadowEnabled']:
                        sx = style['shadowOffsetX']
                        sy = style['shadowOffsetY']
                        sc = style['shadowColor']
                        draw.text((char_x + sx, current_y + sy), char, fill=sc, font=font)
                    
                    # Main text
                    draw.text((char_x, current_y), char, fill=fill[:3], font=font)
                    char_x += char_width + style['letterSpacing']
            else:
                # Shadow
                if style['shadowEnabled']:
                    sx = style['shadowOffsetX']
                    sy = style['shadowOffsetY']
                    sc = style['shadowColor']
                    draw.text((line_x + sx, current_y + sy), line, fill=sc, font=font)
                
                # Main text with stroke/outline if specified
                if style['strokeWidth'] > 0:
                    # Draw outline
                    stroke_color = hex_to_rgba(style['stroke'])
                    for dx in range(-style['strokeWidth'], style['strokeWidth'] + 1):
                        for dy in range(-style['strokeWidth'], style['strokeWidth'] + 1):
                            if dx != 0 or dy != 0:
                                draw.text((line_x + dx, current_y + dy), line, 
                                         fill=stroke_color[:3], font=font)
                
                # Main text
                draw.text((line_x, current_y), line, fill=fill[:3], font=font)
            
            current_y += line_height
        
        # Convert to numpy or keep as PIL
        if to_numpy:
            arr = np.array(text_layer)
            # Alpha blend
            alpha = arr[:, :, 3:4] / 255.0
            canvas[:] = (arr * alpha + canvas * (1 - alpha)).astype(np.uint8)
        else:
            canvas.paste(text_layer, (0, 0), text_layer)
    
    def render_static(self, base_image: Image.Image = None) -> Image.Image:
        """Render static poster."""
        pages = self.template.get('pages', [])
        if not pages:
            return Image.new('RGB', (self.width, self.height), (255, 255, 255))
        
        page = pages[0]
        bg_color = hex_to_rgba(page.get('background', 'rgba(255,255,255,1)'))
        
        # Start with base image or background color
        if base_image:
            result = base_image.convert('RGBA')
            if result.size != (self.width, self.height):
                result = result.resize((self.width, self.height), Image.Resampling.LANCZOS)
        else:
            result = Image.new('RGBA', (self.width, self.height), bg_color)
        
        children = page.get('children', [])
        
        # Sort by type
        def sort_key(c):
            return {'svg': 0, 'image': 1, 'text': 2}.get(c.get('type'), 3)
        
        for child in sorted(children, key=sort_key):
            elem_img = self.render_element(child, to_numpy=False)
            if elem_img:
                result = Image.alpha_composite(result, elem_img)
        
        return result.convert('RGB')
    
    def render_video(self, fps: int = 30, progress_callback=None):
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
            
            if anims:
                # Pre-render for animation
                elem_array = self.render_element(child, to_numpy=True)
                animated_elements.append((child, anims, elem_array))
            else:
                # Static element
                elem_array = self.render_element(child, to_numpy=True)
                static_elements.append(elem_array)
        
        # Composite static base
        base_array = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        bg_color = hex_to_rgba(page.get('background', 'rgba(255,255,255,1)'))
        base_array[:, :] = bg_color
        
        for elem in static_elements:
            # Alpha blend
            alpha = elem[:, :, 3:4] / 255.0
            base_array = (elem * alpha + base_array * (1 - alpha)).astype(np.uint8)
        
        # Generate frames
        frames = []
        
        for frame_idx in range(total_frames):
            time = frame_idx / fps
            frame = base_array.copy()
            
            # Apply animated elements
            for elem_data, anims, elem_array in animated_elements:
                current_array = elem_array.copy()
                
                # Check animations
                visible = True
                for anim in anims:
                    if anim.type in ['enter', 'exit']:
                        if anim.delay <= time <= anim.delay + anim.duration:
                            progress = (time - anim.delay) / anim.duration
                            current_array = self._apply_animation(current_array, anim, progress)
                            visible = True
                            break
                        elif time > anim.delay + anim.duration and anim.type == 'enter':
                            visible = True
                            break
                        elif time < anim.delay and anim.type == 'exit':
                            visible = True
                            break
                        elif time > anim.delay + anim.duration and anim.type == 'exit':
                            visible = False
                    else:  # loop
                        if time >= anim.delay:
                            loop_time = (time - anim.delay) % anim.duration
                            progress = loop_time / anim.duration
                            current_array = self._apply_animation(current_array, anim, progress)
                            visible = True
                            break
                
                if visible:
                    # Alpha blend onto frame
                    alpha = current_array[:, :, 3:4] / 255.0
                    frame = (current_array * alpha + frame * (1 - alpha)).astype(np.uint8)
            
            frames.append(frame[:, :, :3])  # RGB only
            
            if progress_callback and frame_idx % 5 == 0:
                progress_callback(frame_idx / total_frames)
        
        if progress_callback:
            progress_callback(1.0)
        
        # Create video clip
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
        from scipy import ndimage
        
        # Ensure we have alpha channel
        if img_array.shape[2] == 3:
            alpha = np.full((img_array.shape[0], img_array.shape[1], 1), 255, dtype=np.uint8)
            img_array = np.concatenate([img_array, alpha], axis=2)
        
        name = anim.name
        
        if name == 'fade':
            if anim.type == 'exit':
                progress = 1 - progress
            alpha_factor = progress
            img_array[:, :, 3] = (img_array[:, :, 3] * alpha_factor).astype(np.uint8)
        
        elif name == 'zoom':
            if anim.type == 'enter':
                scale = 0.5 + 0.5 * progress
            elif anim.type == 'exit':
                scale = 1.5 - 0.5 * progress
            else:
                scale = 1.0 + 0.1 * math.sin(progress * 2 * math.pi)
            
            h, w = img_array.shape[:2]
            new_h, new_w = int(h * scale), int(w * scale)
            
            if new_h > 1 and new_w > 1:
                # Scale each channel
                scaled = np.zeros((new_h, new_w, 4), dtype=np.uint8)
                for c in range(4):
                    scaled[:, :, c] = ndimage.zoom(img_array[:, :, c], scale, order=1)
                
                # Center crop
                y1 = max(0, (new_h - h) // 2)
                x1 = max(0, (new_w - w) // 2)
                img_array = scaled[y1:y1+h, x1:x1+w]
        
        elif name == 'slide':
            h, w = img_array.shape[:2]
            if anim.type == 'enter':
                offset = int(w * (1 - progress))
            else:
                offset = int(-w * (1 - progress))
            
            img_array = np.roll(img_array, offset, axis=1)
        
        elif name == 'rotate':
            angle = progress * 360 if anim.type != 'exit' else -progress * 360
            rotated = np.zeros_like(img_array)
            for c in range(4):
                rotated[:, :, c] = ndimage.rotate(img_array[:, :, c], angle, 
                                                  reshape=False, order=1, mode='constant', cval=0)
            img_array = rotated
        
        elif name == 'blur':
            if anim.type == 'enter':
                sigma = (1 - progress) * 5
            else:
                sigma = progress * 5
            
            if sigma > 0.1:
                for c in range(3):  # Only blur RGB, not alpha
                    img_array[:, :, c] = ndimage.gaussian_filter(
                        img_array[:, :, c], sigma=sigma
                    ).astype(np.uint8)
        
        elif name in ['bounce', 'blink']:
            alpha_factor = 0.5 + 0.5 * math.sin(progress * 2 * math.pi)
            img_array[:, :, 3] = (img_array[:, :, 3] * alpha_factor).astype(np.uint8)
        
        return img_array

def parse_template_variables(template_data: dict) -> Dict:
    """Extract all template variables."""
    variables = {}
    
    pages = template_data.get('pages', [])
    for page in pages:
        for child in page.get('children', []):
            name = child.get('name', '')
            text = child.get('text', '')
            
            for field in [name, text]:
                if field and '{{' in field:
                    vars_found = extract_variables(field)
                    for var in vars_found:
                        variables[var] = {
                            'is_image': is_image_variable(var),
                            'type': child.get('type')
                        }
    
    return variables

# ============== STREAMLIT UI ==============

def main():
    st.title("🎬 Polotno Studio Pro")
    st.markdown("**Multi-Store WooCommerce + Animated Video Generator**")
    
    if 'product_data' not in st.session_state:
        st.session_state.product_data = {}
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    
    with st.sidebar:
        st.header("🛒 Product Source")
        
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
        
        base_image_file = st.file_uploader(
            "Base Image (Optional)",
            type=['png', 'jpg', 'jpeg']
        )
        
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
    
    col_edit, col_preview = st.columns([1, 1.5])
    
    with col_edit:
        st.subheader("📝 Template Variables")
        
        if template_data:
            renderer = PolotnoRenderer(template_data, {})
            pages = template_data.get('pages', [])
            
            all_vars = {}
            for page in pages:
                for child in page.get('children', []):
                    for field in [child.get('name', ''), child.get('text', '')]:
                        for var in renderer.extract_variables(field):
                            all_vars[var] = {
                                'is_image': is_image_variable(var),
                                'type': child.get('type')
                            }
            
            if all_vars:
                st.write(f"**{len(all_vars)} variables detected**")
                
                text_vars = [v for v in all_vars if not v.startswith('image')]
                image_vars = [v for v in all_vars if v.startswith('image')]
                
                for var in sorted(text_vars):
                    current = st.session_state.product_data.get(var, '')
                    new_val = st.text_input(
                        f"{{{var}}}",
                        value=str(current),
                        key=f"var_{var}"
                    )
                    st.session_state.product_data[var] = new_val
                
                for var in sorted(image_vars):
                    st.markdown(f"**{{{var}}}**")
                    current = st.session_state.product_data.get(var, '')
                    
                    if current:
                        st.image(current, width=150)
                    
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
            base_img = None
            if base_image_file:
                base_img = Image.open(base_image_file)
            
            renderer = PolotnoRenderer(template_data, st.session_state.product_data)
            
            if output_type == "Static PNG":
                with st.spinner("Rendering..."):
                    result = renderer.render_static(base_img)
                    st.image(result, use_container_width=True)
                    
                    buf = io.BytesIO()
                    result.save(buf, format='PNG')
                    st.download_button(
                        "⬇️ Download PNG",
                        buf.getvalue(),
                        file_name="poster.png",
                        mime="image/png"
                    )
            
            else:
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
