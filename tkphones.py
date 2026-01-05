import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from io import BytesIO
import numpy as np
import tempfile
import random
import re
import time
from moviepy.editor import VideoClip, CompositeVideoClip, ImageClip, TextClip
from moviepy.editor import vfx, afx
import os

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
BRAND_COLORS = {
    "primary": "#2D1B1B",    # Dark Maroon
    "secondary": "#C5A059",  # Gold
    "accent": "#3EB489",     # Mint Green
    "dark": "#0F0A0A",       # Darker Maroon
    "light": "#FFFFFF"       # White
}

CONTACT_INFO = {
    "phone": "+254 700 123 456",
    "whatsapp": "+254 700 123 456",
    "web": "www.triplek.co.ke",
    "location": "CBD, Nairobi, Kenya"
}

API_CONFIG = {
    "base": "https://tkphsp2.vercel.app",
    "timeout": 10
}

# ==========================================
# 2. ADVANCED PARTICLE SYSTEM
# ==========================================
class MotionParticles:
    def __init__(self, width, height, count=30):
        self.width = width
        self.height = height
        self.particles = []
        
        for _ in range(count):
            self.particles.append({
                "x": random.randint(0, width),
                "y": random.randint(0, height),
                "size": random.randint(2, 8),
                "speed": random.uniform(0.2, 1.0),
                "color": random.choice([
                    (197, 160, 89),   # Gold
                    (62, 180, 137),   # Mint
                    (255, 255, 255)   # White
                ]),
                "direction": random.uniform(0, 360)
            })
    
    def update(self, time):
        for p in self.particles:
            # Move particles with some physics
            p["y"] -= p["speed"] * 20
            p["x"] += np.sin(time + p["x"] * 0.01) * 2
            
            # Wrap around screen
            if p["y"] < -10:
                p["y"] = self.height + 10
                p["x"] = random.randint(0, self.width)
    
    def draw(self, draw):
        for p in self.particles:
            x, y = int(p["x"]), int(p["y"])
            size = p["size"]
            draw.ellipse([x, y, x + size, y + size], fill=p["color"])

# ==========================================
# 3. SMART DATA EXTRACTION
# ==========================================
def extract_smart_specs(info_data):
    """Extract and format specifications intelligently"""
    specs = []
    
    # Display
    display_info = info_data.get("display", {})
    display_size = display_info.get("size", "6.7")
    display_type = display_info.get("type", "OLED")
    if '"' not in str(display_size):
        display_size = f'{display_size}"'
    specs.append(("Display", f"{display_size} {display_type}"))
    
    # Camera
    camera_info = info_data.get("mainCamera", {})
    camera_mp = camera_info.get("mainModules", "12MP")
    if "MP" not in str(camera_mp).upper():
        camera_mp = f"{camera_mp}MP"
    specs.append(("Camera", str(camera_mp)))
    
    # Memory & Storage
    memory_info = info_data.get("memory", [{}])[0]
    memory_text = memory_info.get("value", "8GB RAM, 256GB")
    
    # Parse RAM
    ram_match = re.search(r'(\d+\s*[GgTt][Bb])\s*[Rr][Aa][Mm]', memory_text)
    storage_match = re.search(r'(\d+\s*[GgTt][Bb])\s*(?:internal|storage|rom|memory)', memory_text, re.IGNORECASE)
    
    if ram_match:
        specs.append(("RAM", ram_match.group(1).upper()))
    else:
        specs.append(("RAM", "8GB"))
    
    if storage_match:
        specs.append(("Storage", storage_match.group(1).upper()))
    else:
        specs.append(("Storage", "256GB"))
    
    # Battery
    battery_info = info_data.get("battery", {})
    battery_capacity = battery_info.get("battType", "5000")
    if "mAh" not in str(battery_capacity):
        battery_capacity = f"{battery_capacity}mAh"
    specs.append(("Battery", str(battery_capacity)))
    
    # Processor
    platform_info = info_data.get("platform", {})
    if platform_info.get("chipset"):
        chipset = platform_info["chipset"].split()[0]
        specs.append(("Processor", f"{chipset} Chipset"))
    
    return specs

def fetch_phone_details(query):
    """Fetch complete phone data with intelligent parsing"""
    try:
        # Search for phone
        search_url = f"{API_CONFIG['base']}/gsm/search?q={query}"
        search_response = requests.get(search_url, timeout=API_CONFIG["timeout"])
        
        if search_response.status_code != 200 or not search_response.json():
            return None
        
        phone_data = search_response.json()[0]
        phone_id = phone_data["id"]
        
        # Fetch details concurrently
        info_url = f"{API_CONFIG['base']}/gsm/info/{phone_id}"
        images_url = f"{API_CONFIG['base']}/gsm/images/{phone_id}"
        
        info_response = requests.get(info_url, timeout=API_CONFIG["timeout"])
        images_response = requests.get(images_url, timeout=API_CONFIG["timeout"])
        
        if info_response.status_code != 200 or images_response.status_code != 200:
            return None
        
        info_data = info_response.json()
        images_data = images_response.json()
        
        # Get best image
        image_list = images_data.get("images", [])
        hero_image = image_list[1] if len(image_list) > 1 else image_list[0] if image_list else None
        
        # Extract specs
        specs = extract_smart_specs(info_data)
        
        return {
            "name": phone_data.get("name", query),
            "image_url": hero_image,
            "specs": specs,
            "raw_info": info_data
        }
        
    except Exception as e:
        st.error(f"Error fetching data: {str(e)[:100]}")
        return None

# ==========================================
# 4. PROFESSIONAL AD GENERATOR
# ==========================================
class ProfessionalAdGenerator:
    def __init__(self):
        # Try to load modern fonts
        try:
            self.font_title = ImageFont.truetype("arialbd.ttf", 68)
            self.font_subtitle = ImageFont.truetype("arialbd.ttf", 42)
            self.font_price = ImageFont.truetype("arialbd.ttf", 56)
            self.font_specs = ImageFont.truetype("arial.ttf", 26)
            self.font_footer = ImageFont.truetype("arial.ttf", 22)
        except:
            # Fallback to default with larger sizes
            self.font_title = ImageFont.load_default()
            self.font_subtitle = ImageFont.load_default()
            self.font_price = ImageFont.load_default()
            self.font_specs = ImageFont.load_default()
            self.font_footer = ImageFont.load_default()
    
    def create_modern_frame(self, phone_image):
        """Create modern phone frame with effects"""
        if phone_image is None:
            return None
        
        # Resize for optimal display
        phone_image.thumbnail((750, 950), Image.Resampling.LANCZOS)
        pw, ph = phone_image.size
        
        # Create frame
        frame_size = (pw + 100, ph + 100)
        frame = Image.new("RGBA", frame_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        
        # Modern frame with gradient
        for i in range(frame_size[1]):
            alpha = int(255 * (1 - abs(i - frame_size[1]//2) / (frame_size[1]//2)) * 0.7)
            draw.line([(0, i), (frame_size[0], i)], fill=(255, 255, 255, alpha))
        
        # Add phone with shadow
        shadow_offset = 15
        shadow = Image.new("RGBA", (pw + 30, ph + 30), (0, 0, 0, 100))
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))
        frame.paste(shadow, (50 - shadow_offset, 50 - shadow_offset), shadow)
        
        # Paste phone
        frame.paste(phone_image, (50, 50), phone_image if phone_image.mode == 'RGBA' else None)
        
        # Add subtle reflection
        reflection = phone_image.copy().transpose(Image.FLIP_TOP_BOTTOM)
        reflection = reflection.convert("RGBA")
        
        # Apply gradient mask
        mask = Image.new("L", reflection.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        for i in range(reflection.height):
            alpha = int(60 * (1 - i / reflection.height))
            mask_draw.line([(0, i), (reflection.width, i)], fill=alpha)
        reflection.putalpha(mask)
        
        frame.paste(reflection, (50, 50 + ph), reflection)
        
        return frame
    
    def generate_instagram_post(self, name, price, phone_image, specs):
        """Generate modern Instagram post"""
        canvas = Image.new("RGB", (1080, 1080), BRAND_COLORS["primary"])
        draw = ImageDraw.Draw(canvas)
        
        # Gradient background
        for y in range(1080):
            factor = y / 1080
            r = int(45 * (1 - factor) + 20 * factor)
            g = int(27 * (1 - factor) + 11 * factor)
            b = int(27 * (1 - factor) + 11 * factor)
            draw.line([(0, y), (1080, y)], fill=(r, g, b))
        
        # Header with logo/text
        draw.text((540, 60), "TRIPPLE K", font=self.font_subtitle, 
                 fill=BRAND_COLORS["secondary"], anchor="mm")
        draw.text((540, 100), "PREMIUM MOBILES", font=self.font_specs, 
                 fill="white", anchor="mm")
        
        # Phone name
        name_text = name.upper()[:25]
        draw.text((540, 180), name_text, font=self.font_title, 
                 fill="white", anchor="mm")
        
        # Phone image (modern frame)
        if phone_image:
            phone_frame = self.create_modern_frame(phone_image)
            if phone_frame:
                frame_x = 1080 - phone_frame.width - 40
                frame_y = 250
                canvas.paste(phone_frame, (frame_x, frame_y), phone_frame)
        
        # Specifications (right side)
        y_spec = 280
        for label, value in specs[:4]:
            # Modern spec card
            draw.rounded_rectangle([40, y_spec, 400, y_spec + 65], 
                                 radius=10, fill=(255, 255, 255, 20))
            
            # Label
            draw.text((60, y_spec + 10), label, font=self.font_specs, 
                     fill=BRAND_COLORS["secondary"])
            
            # Value
            draw.text((60, y_spec + 35), value, font=self.font_specs, 
                     fill="white")
            
            y_spec += 80
        
        # Price badge
        price_width = 300
        price_height = 100
        price_x = (1080 - price_width) // 2
        price_y = 800
        
        # Gradient price badge
        for i in range(price_height):
            factor = i / price_height
            r = int(62 * (1 - factor) + 40 * factor)
            g = int(180 * (1 - factor) + 140 * factor)
            b = int(137 * (1 - factor) + 100 * factor)
            draw.line([(price_x, price_y + i), (price_x + price_width, price_y + i)], 
                     fill=(r, g, b))
        
        draw.rounded_rectangle([price_x, price_y, price_x + price_width, price_y + price_height], 
                             radius=15, outline="white", width=2)
        
        price_text = f"KES {price}"
        text_width = draw.textlength(price_text, font=self.font_price)
        draw.text((price_x + price_width//2, price_y + price_height//2), price_text, 
                 font=self.font_price, fill="white", anchor="mm")
        
        # Footer
        footer_y = 980
        draw.line([(0, footer_y), (1080, footer_y)], fill=(255, 255, 255, 50), width=1)
        
        contact_text = f"📞 {CONTACT_INFO['phone']} | 🌐 {CONTACT_INFO['web']}"
        draw.text((540, 1020), contact_text, font=self.font_footer, 
                 fill=BRAND_COLORS["secondary"], anchor="mm")
        
        return canvas
    
    def generate_whatsapp_ad(self, name, price, phone_image, specs):
        """Generate WhatsApp optimized ad"""
        canvas = Image.new("RGB", (1080, 1080), BRAND_COLORS["dark"])
        draw = ImageDraw.Draw(canvas)
        
        # Large phone image
        if phone_image:
            phone_image.thumbnail((700, 850), Image.Resampling.LANCZOS)
            pw, ph = phone_image.size
            canvas.paste(phone_image, ((1080 - pw)//2, 100))
        
        # Title with badge
        draw.rounded_rectangle([340, 30, 740, 80], radius=20, 
                             fill=BRAND_COLORS["accent"])
        draw.text((540, 55), "NEW ARRIVAL", font=self.font_subtitle, 
                 fill="white", anchor="mm")
        
        # Device name
        draw.text((540, 900), name.upper()[:22], font=self.font_title, 
                 fill="white", anchor="mm")
        
        # Price in circle
        draw.ellipse([390, 920, 690, 1220], fill=BRAND_COLORS["primary"])
        draw.ellipse([400, 930, 680, 1210], fill=BRAND_COLORS["secondary"])
        
        price_lines = price.split(',')
        if len(price_lines[0]) > 3:
            price_display = f"KES\n{price_lines[0][:-3]},{price_lines[0][-3:]}"
        else:
            price_display = f"KES\n{price}"
        
        draw.text((540, 1070), price_display, font=self.font_price, 
                 fill=BRAND_COLORS["primary"], anchor="mm", align="center")
        
        # Call to action
        draw.text((540, 1250), f"📱 WhatsApp: {CONTACT_INFO['whatsapp']}", 
                 font=self.font_footer, fill="white", anchor="mm")
        
        # Add border
        draw.rectangle([0, 0, 1079, 1079], outline=BRAND_COLORS["secondary"], width=3)
        
        return canvas
    
    def generate_tiktok_ad(self, name, price, phone_image, specs):
        """Generate TikTok vertical ad"""
        canvas = Image.new("RGB", (1080, 1920), BRAND_COLORS["primary"])
        draw = ImageDraw.Draw(canvas)
        
        # Background pattern
        for i in range(0, 1920, 40):
            draw.line([(0, i), (1080, i)], fill=(255, 255, 255, 5), width=1)
        
        # Brand header
        draw.rectangle([0, 0, 1080, 120], fill=BRAND_COLORS["dark"])
        draw.text((540, 60), "TRIPPLE K MOBILE AGENCY", font=self.font_subtitle, 
                 fill=BRAND_COLORS["secondary"], anchor="mm")
        
        # Phone image (large)
        if phone_image:
            phone_image.thumbnail((900, 1100), Image.Resampling.LANCZOS)
            pw, ph = phone_image.size
            canvas.paste(phone_image, ((1080 - pw)//2, 150))
        
        # Device name with gradient
        name_text = name.upper()[:25]
        draw.text((540, 1300), name_text, font=self.font_title, 
                 fill="white", anchor="mm")
        
        # Key specs
        specs_text = ""
        for label, value in specs[:3]:
            specs_text += f"• {label}: {value}\n"
        
        draw.text((540, 1400), specs_text, font=self.font_specs, 
                 fill=BRAND_COLORS["secondary"], anchor="mm", align="center")
        
        # Price section
        price_bg_height = 180
        price_bg_y = 1650
        draw.rectangle([0, price_bg_y, 1080, price_bg_y + price_bg_height], 
                      fill=BRAND_COLORS["accent"])
        
        draw.text((540, price_bg_y + 50), "SPECIAL OFFER", font=self.font_subtitle, 
                 fill="white", anchor="mm")
        draw.text((540, price_bg_y + 100), f"KES {price}", font=self.font_price, 
                 fill="white", anchor="mm")
        
        # Footer
        footer_text = f"📍 {CONTACT_INFO['location']} | 📞 {CONTACT_INFO['phone']}"
        draw.text((540, 1880), footer_text, font=self.font_footer, 
                 fill="white", anchor="mm")
        
        return canvas

# ==========================================
# 5. VIDEO GENERATION ENGINE
# ==========================================
class VideoEngine:
    def __init__(self):
        self.temp_files = []
    
    def create_cinematic_video(self, image, duration=8):
        """Create professional cinematic video"""
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        
        def make_frame(t):
            # Create base frame with zoom
            zoom = 1.0 + 0.05 * (t / duration)
            h, w = img_array.shape[:2]
            
            # Calculate zoomed dimensions
            new_h, new_w = int(h * zoom), int(w * zoom)
            
            # Resize
            frame = Image.fromarray(img_array).resize((new_w, new_h), Image.Resampling.LANCZOS)
            frame = np.array(frame)
            
            # Crop center
            start_h = (new_h - h) // 2
            start_w = (new_w - w) // 2
            frame = frame[start_h:start_h + h, start_w:start_w + w]
            
            # Add particle effects
            particles = MotionParticles(w, h, 20)
            particles.update(t)
            
            # Draw particles on frame
            pil_frame = Image.fromarray(frame)
            draw = ImageDraw.Draw(pil_frame)
            particles.draw(draw)
            
            # Add vignette effect
            vignette = Image.new("RGB", (w, h), (0, 0, 0))
            vignette_draw = ImageDraw.Draw(vignette, 'RGBA')
            vignette_draw.ellipse([-200, -200, w+200, h+200], fill=(0, 0, 0, 0))
            vignette_draw.ellipse([100, 100, w-100, h-100], fill=(0, 0, 0, 100))
            
            # Blend vignette
            pil_frame = Image.blend(pil_frame, vignette, 0.3)
            
            # Add text animation
            if t > 2 and t < duration - 2:
                text_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_overlay)
                
                # Animated text
                text_alpha = min(255, int(255 * (t - 2) * 2))
                text_draw.text((w//2, h - 150), "TRIPPLE K AGENCY", 
                              fill=(197, 160, 89, text_alpha), 
                              anchor="mm", font=ImageFont.load_default())
                
                pil_frame = Image.alpha_composite(pil_frame.convert("RGBA"), text_overlay)
            
            return np.array(pil_frame.convert("RGB"))
        
        # Create video clip
        clip = VideoClip(make_frame, duration=duration)
        
        # Render to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        self.temp_files.append(temp_file.name)
        
        # High quality encoding
        clip.write_videofile(
            temp_file.name,
            fps=30,
            codec='libx264',
            audio_codec='aac' if duration > 3 else None,
            ffmpeg_params=['-pix_fmt', 'yuv420p', '-crf', '18'],
            logger=None
        )
        
        return temp_file.name
    
    def cleanup(self):
        """Clean up temporary files"""
        for file in self.temp_files:
            try:
                os.unlink(file)
            except:
                pass

# ==========================================
# 6. AI COPY GENERATOR
# ==========================================
def generate_ai_copy(name, price, specs, api_key=None):
    """Generate marketing copy using Grok API"""
    
    # Prepare specs text
    spec_text = "\n".join([f"• {label}: {value}" for label, value in specs[:4]])
    
    # Base template
    base_copy = f"""
🔥 *{name.upper()} - NOW IN STOCK!* 🔥

📱 *PREMIUM FEATURES:*
{spec_text}

💰 *EXCLUSIVE PRICE: KES {price}*
✅ Brand New | Full Warranty
✅ Genuine Import | Ready for Delivery

📍 *VISIT OUR SHOWROOM:*
📞 {CONTACT_INFO['phone']}
📱 WhatsApp: {CONTACT_INFO['whatsapp']}
🌐 {CONTACT_INFO['web']}
🗺️ {CONTACT_INFO['location']}

#TripleK #MobileTech #Nairobi #Kenya #{name.replace(' ', '')}
"""
    
    # Try Grok API if key is available
    if api_key and api_key.strip():
        try:
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Create a compelling social media marketing copy for a mobile phone store in Nairobi, Kenya.
            
            Product: {name}
            Price: KES {price}
            Key Features: {', '.join([f'{label}: {value}' for label, value in specs[:3]])}
            Store: Triple K Agency
            Location: {CONTACT_INFO['location']}
            Contact: {CONTACT_INFO['phone']}
            
            Make it engaging, use emojis, and include relevant hashtags for the Kenyan market."""
            
            payload = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            }
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                ai_content = response.json()["choices"][0]["message"]["content"]
                return ai_content + f"\n\n📞 {CONTACT_INFO['phone']} | 🌐 {CONTACT_INFO['web']}"
                
        except Exception as e:
            st.warning(f"AI generation failed, using template: {str(e)[:50]}")
    
    return base_copy

# ==========================================
# 7. MAIN APPLICATION
# ==========================================
def main():
    st.set_page_config(
        page_title="Triple K Studio Pro",
        layout="wide",
        page_icon="📱",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #2D1B1B, #C5A059, #3EB489);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        padding: 0.5rem;
    }
    .platform-card {
        background: rgba(45, 27, 27, 0.1);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #C5A059;
        margin-bottom: 1rem;
    }
    .stButton > button {
        background: linear-gradient(45deg, #2D1B1B, #C5A059);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.3s;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(197, 160, 89, 0.4);
    }
    .success-msg {
        background: rgba(62, 180, 137, 0.1);
        border-left: 4px solid #3EB489;
        padding: 1rem;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">📱 TRIPLE K STUDIO PRO</h1>', unsafe_allow_html=True)
    st.markdown("### *Professional Mobile Advertising Platform*")
    
    # Initialize session state
    if 'phone_data' not in st.session_state:
        st.session_state.phone_data = None
    if 'generated_assets' not in st.session_state:
        st.session_state.generated_assets = {}
    if 'video_engine' not in st.session_state:
        st.session_state.video_engine = VideoEngine()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Campaign Configuration")
        
        # Device search
        device_query = st.text_input(
            "📱 Device Name / Model",
            value="iPhone 15 Pro Max",
            help="e.g., Samsung S23 Ultra, Google Pixel 8"
        )
        
        # Price
        price = st.text_input(
            "💰 Price (KES)",
            value="185,000",
            help="Enter price in Kenyan Shillings"
        )
        
        # Format price
        if price:
            try:
                clean_price = re.sub(r'[^\d]', '', price)
                if clean_price:
                    price_num = int(clean_price)
                    price = f"{price_num:,}"
            except:
                pass
        
        # Grok API Key
        grok_key = st.text_input(
            "🤖 Grok API Key (Optional)",
            type="password",
            value=st.secrets.get("grok_key", "") if hasattr(st, 'secrets') else ""
        )
        
        # Video options
        with st.expander("🎬 Video Settings"):
            video_duration = st.slider("Duration (seconds)", 5, 15, 8)
            include_audio = st.checkbox("Add background music", value=True)
        
        # Generate button
        generate_all = st.button(
            "🚀 GENERATE ALL ASSETS",
            type="primary",
            use_container_width=True
        )
    
    # Main content
    if generate_all:
        with st.spinner("🔄 Processing your request..."):
            # Fetch phone data
            phone_data = fetch_phone_details(device_query)
            
            if not phone_data:
                st.error("❌ Could not fetch device information. Please try a different model.")
                st.info("Try: iPhone 15 Pro, Samsung S23 Ultra, Google Pixel 8")
                return
            
            st.session_state.phone_data = phone_data
            
            # Get phone image
            phone_img = None
            if phone_data.get('image_url'):
                try:
                    response = requests.get(phone_data['image_url'], timeout=15)
                    if response.status_code == 200:
                        phone_img = Image.open(BytesIO(response.content)).convert("RGBA")
                except:
                    # Create placeholder
                    phone_img = Image.new("RGBA", (400, 600), (255, 255, 255, 255))
            
            # Initialize generator
            generator = ProfessionalAdGenerator()
            
            # Create tabs for different outputs
            tabs = st.tabs(["📸 Instagram", "💬 WhatsApp", "🎵 TikTok", "🎥 Videos", "📝 Copy"])
            
            with tabs[0]:
                st.subheader("Instagram Post (1080x1080)")
                
                insta_ad = generator.generate_instagram_post(
                    phone_data['name'],
                    price,
                    phone_img,
                    phone_data['specs']
                )
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.image(insta_ad, use_container_width=True)
                
                with col2:
                    # Download options
                    buf = BytesIO()
                    insta_ad.save(buf, format='PNG', optimize=True)
                    
                    st.download_button(
                        "📥 Download PNG",
                        buf.getvalue(),
                        f"TripleK_Instagram_{phone_data['name'].replace(' ', '_')}.png",
                        "image/png",
                        use_container_width=True
                    )
                
                st.session_state.generated_assets['instagram'] = insta_ad
            
            with tabs[1]:
                st.subheader("WhatsApp Ad (1080x1080)")
                
                whatsapp_ad = generator.generate_whatsapp_ad(
                    phone_data['name'],
                    price,
                    phone_img,
                    phone_data['specs']
                )
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.image(whatsapp_ad, use_container_width=True)
                
                with col2:
                    buf = BytesIO()
                    whatsapp_ad.save(buf, format='PNG', optimize=True)
                    
                    st.download_button(
                        "📥 Download PNG",
                        buf.getvalue(),
                        f"TripleK_WhatsApp_{phone_data['name'].replace(' ', '_')}.png",
                        "image/png",
                        use_container_width=True
                    )
                
                st.session_state.generated_assets['whatsapp'] = whatsapp_ad
            
            with tabs[2]:
                st.subheader("TikTok Ad (1080x1920)")
                
                tiktok_ad = generator.generate_tiktok_ad(
                    phone_data['name'],
                    price,
                    phone_img,
                    phone_data['specs']
                )
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.image(tiktok_ad, use_container_width=True)
                
                with col2:
                    buf = BytesIO()
                    tiktok_ad.save(buf, format='PNG', optimize=True)
                    
                    st.download_button(
                        "📥 Download PNG",
                        buf.getvalue(),
                        f"TripleK_TikTok_{phone_data['name'].replace(' ', '_')}.png",
                        "image/png",
                        use_container_width=True
                    )
                
                st.session_state.generated_assets['tiktok'] = tiktok_ad
            
            with tabs[3]:
                st.subheader("🎬 Cinematic Videos")
                
                # Video generation options
                video_options = st.multiselect(
                    "Generate videos for:",
                    ["Instagram", "WhatsApp", "TikTok"],
                    default=["Instagram"]
                )
                
                if st.button("🎥 Generate Selected Videos", use_container_width=True):
                    for platform in video_options:
                        if platform.lower() in st.session_state.generated_assets:
                            with st.spinner(f"Creating {platform} video..."):
                                try:
                                    video_file = st.session_state.video_engine.create_cinematic_video(
                                        st.session_state.generated_assets[platform.lower()],
                                        duration=video_duration
                                    )
                                    
                                    # Display video
                                    st.subheader(f"{platform} Video")
                                    st.video(video_file)
                                    
                                    # Download button
                                    with open(video_file, 'rb') as f:
                                        video_bytes = f.read()
                                    
                                    st.download_button(
                                        f"🎥 Download {platform} Video",
                                        video_bytes,
                                        f"TripleK_{platform}_{phone_data['name'].replace(' ', '_')}.mp4",
                                        "video/mp4",
                                        use_container_width=True
                                    )
                                    
                                    st.markdown("---")
                                    
                                except Exception as e:
                                    st.error(f"Failed to create {platform} video: {str(e)}")
                        else:
                            st.warning(f"No {platform} ad generated yet")
            
            with tabs[4]:
                st.subheader("📝 Marketing Copy")
                
                # Generate copy
                marketing_copy = generate_ai_copy(
                    phone_data['name'],
                    price,
                    phone_data['specs'],
                    grok_key
                )
                
                # Display
                st.text_area("Ready-to-use marketing copy:", marketing_copy, height=300)
                
                # Copy buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 Copy to Clipboard", use_container_width=True):
                        st.code(marketing_copy)
                        st.success("Copied!")
                
                with col2:
                    st.download_button(
                        "📄 Download as Text",
                        marketing_copy,
                        f"TripleK_Copy_{phone_data['name'].replace(' ', '_')}.txt",
                        "text/plain",
                        use_container_width=True
                    )
    
    else:
        # Welcome screen
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="platform-card">', unsafe_allow_html=True)
            st.markdown("### 📸 Instagram")
            st.markdown("""
            • 1080x1080 Square Posts
            • Professional Design
            • Hashtag Optimized
            • High-Resolution
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="platform-card">', unsafe_allow_html=True)
            st.markdown("### 💬 WhatsApp")
            st.markdown("""
            • Share-Optimized
            • Clear Call-to-Action
            • Fast Loading
            • Mobile Friendly
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="platform-card">', unsafe_allow_html=True)
            st.markdown("### 🎵 TikTok")
            st.markdown("""
            • 1080x1920 Vertical
            • Video-Ready
            • Youth Appeal
            • Trend Integration
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick start guide
        st.markdown("### 🚀 Quick Start Guide")
        
        steps = st.columns(4)
        with steps[0]:
            st.markdown("#### 1. Search")
            st.markdown("Enter phone model name")
        with steps[1]:
            st.markdown("#### 2. Set Price")
            st.markdown("Enter price in KES")
        with steps[2]:
            st.markdown("#### 3. Generate")
            st.markdown("Click generate button")
        with steps[3]:
            st.markdown("#### 4. Download")
            st.markdown("Get all assets instantly")
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #C5A059; padding: 1rem;'>
        <b>Triple K Agency</b> | Nairobi, Kenya | Premium Mobile Solutions Since 2015
        </div>
        """, unsafe_allow_html=True)

# Cleanup on app close
import atexit
if 'video_engine' in st.session_state:
    atexit.register(st.session_state.video_engine.cleanup)

if __name__ == "__main__":
    main()
