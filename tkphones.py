import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from io import BytesIO
import numpy as np
import tempfile
import random
import re
from moviepy.editor import VideoClip
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================

# Online icons (no local files needed)
ICON_URLS = {
    "whatsapp": "https://cdn-icons-png.flaticon.com/512/733/733585.png",
    "location": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
    "web": "https://cdn-icons-png.flaticon.com/512/1006/1006771.png",
    "screen": "https://cdn-icons-png.flaticon.com/512/2972/2972543.png",
    "camera": "https://cdn-icons-png.flaticon.com/512/2983/2983067.png",
    "memory": "https://cdn-icons-png.flaticon.com/512/2959/2959323.png",
    "storage": "https://cdn-icons-png.flaticon.com/512/888/888013.png",
    "battery": "https://cdn-icons-png.flaticon.com/512/3103/3103476.png",
    "logo": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"
}

CONTACT = {
    "web": "www.triplek.co.ke",
    "location": "CBD, Nairobi, Kenya",
    "whatsapp": "+254 700 123 456"
}

CONFIG = {
    "brand": {
        "maroon": "#2D1B1B",  # Dark Maroon
        "gold": "#C5A059",    # Gold
        "mint": "#3EB489",    # Mint Green
        "light_gold": "#E6D4A5"
    },
    "api_base": "https://tkphsp2.vercel.app"
}

# ==========================================
# 2. PARTICLE SYSTEM
# ==========================================
class ParticleField:
    def __init__(self, count=25):
        self.particles = []
        for _ in range(count):
            self.particles.append({
                "x": random.randint(0, 1080),
                "y": random.randint(0, 1080),
                "size": random.randint(3, 8),
                "speed": random.uniform(0.1, 0.8),
                "opacity": random.randint(40, 150),
                "color": random.choice([(197, 160, 89), (255, 255, 255), (62, 180, 137)])
            })

    def draw(self, draw, time):
        for p in self.particles:
            y = (p["y"] - time * p["speed"] * 50) % 1080
            x = (p["x"] + np.sin(time + p["y"] * 0.01) * 20) % 1080
            color = (*p["color"], p["opacity"])
            draw.ellipse([x, y, x + p["size"], y + p["size"]], fill=color)

# ==========================================
# 3. AD ENGINE WITH CREATIVE PHONE FRAME
# ==========================================
class TripleKEngine:
    def __init__(self):
        # Font loading with fallbacks
        try:
            self.f_title = ImageFont.truetype("arialbd.ttf", 72)
            self.f_price = ImageFont.truetype("arialbd.ttf", 60)
            self.f_spec = ImageFont.truetype("arial.ttf", 24)
            self.f_footer = ImageFont.truetype("arial.ttf", 20)
            self.f_badge = ImageFont.truetype("arialbd.ttf", 36)
        except:
            # Use larger default fonts
            self.f_title = ImageFont.load_default()
            self.f_price = ImageFont.load_default()
            self.f_spec = ImageFont.load_default()
            self.f_footer = ImageFont.load_default()
            self.f_badge = ImageFont.load_default()
    
    def load_icon(self, name, size=(40, 40)):
        """Load icon from URL with white color overlay for visibility"""
        try:
            response = requests.get(ICON_URLS[name], timeout=5)
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            
            # Make icons white for better visibility on dark background
            if name != "logo":  # Keep logo original color
                data = np.array(img)
                # Make white where not transparent
                white = np.full(data.shape, 255, dtype=np.uint8)
                white[:, :, 3] = data[:, :, 3]  # Keep alpha channel
                img = Image.fromarray(white)
            
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
        except:
            # Create a simple colored square as fallback
            img = Image.new("RGBA", size, (255, 255, 255, 200))
            draw = ImageDraw.Draw(img)
            draw.ellipse([2, 2, size[0]-2, size[1]-2], outline=CONFIG["brand"]["gold"], width=2)
            return img
    
    def create_phone_frame(self, phone_img):
        """Create creative phone frame with shadow and borders"""
        if not phone_img:
            return None
        
        # Resize phone image (larger)
        phone_img.thumbnail((750, 950), Image.Resampling.LANCZOS)
        pw, ph = phone_img.size
        
        # Create phone frame with creative design
        frame_w, frame_h = pw + 80, ph + 80
        frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        
        # Creative frame with rounded corners and metallic border
        # Outer glow
        for i in range(3):
            radius = 40 - i * 5
            draw.rounded_rectangle(
                [i, i, frame_w - i, frame_h - i],
                radius=radius,
                outline=(255, 255, 255, 30 - i * 10),
                width=1
            )
        
        # Main frame (white rectangle)
        draw.rounded_rectangle(
            [20, 20, frame_w - 20, frame_h - 20],
            radius=25,
            fill="white"
        )
        
        # Gold accent border
        draw.rounded_rectangle(
            [10, 10, frame_w - 10, frame_h - 10],
            radius=30,
            outline=CONFIG["brand"]["gold"],
            width=4
        )
        
        # Inner shadow
        shadow = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [15, 15, frame_w - 15, frame_h - 15],
            radius=27,
            fill=(0, 0, 0, 30)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(3))
        frame = Image.alpha_composite(frame, shadow)
        
        # Paste phone image centered
        phone_x = (frame_w - pw) // 2
        phone_y = (frame_h - ph) // 2
        frame.paste(phone_img, (phone_x, phone_y), phone_img if phone_img.mode == 'RGBA' else None)
        
        # Add reflection shine
        shine = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        shine_draw = ImageDraw.Draw(shine)
        shine_draw.polygon(
            [(frame_w * 0.7, 0), (frame_w, 0), (frame_w * 0.3, frame_h), (0, frame_h)],
            fill=(255, 255, 255, 15)
        )
        frame = Image.alpha_composite(frame, shine)
        
        return frame
    
    def render_ad(self, name, price, phone_img, specs):
        """Render Instagram square ad with balanced layout"""
        canvas = Image.new("RGB", (1080, 1080), CONFIG["brand"]["maroon"])
        draw = ImageDraw.Draw(canvas)
        
        # Creative background gradient
        for y in range(1080):
            factor = y / 1080
            # Dark to darker maroon gradient
            r = int(45 * (1 - factor) + 20 * factor)
            g = int(27 * (1 - factor) + 11 * factor)
            b = int(27 * (1 - factor) + 11 * factor)
            draw.line([(0, y), (1080, y)], fill=(r, g, b))
        
        # 1. Header with logo
        logo = self.load_icon("logo", (320, 120))
        if logo:
            canvas.paste(logo, (380, 30), logo)
        
        # 2. Device name (centered)
        name_text = name.upper()[:22]
        text_width = draw.textlength(name_text, font=self.f_title)
        draw.text(((1080 - text_width) // 2, 160), name_text, 
                 font=self.f_title, fill="white")
        
        # 3. Creative phone frame (LARGER - moved to center-right)
        if phone_img:
            phone_frame = self.create_phone_frame(phone_img)
            if phone_frame:
                # Position phone on right side
                phone_x = 1080 - phone_frame.width - 30
                phone_y = 250
                
                # Add dramatic shadow
                shadow = Image.new("RGBA", (phone_frame.width + 40, phone_frame.height + 40), (0, 0, 0, 0))
                shadow_draw = ImageDraw.Draw(shadow)
                shadow_draw.rounded_rectangle(
                    [20, 20, phone_frame.width + 20, phone_frame.height + 20],
                    radius=35,
                    fill=(0, 0, 0, 120)
                )
                shadow = shadow.filter(ImageFilter.GaussianBlur(20))
                canvas.paste(shadow, (phone_x - 10, phone_y + 10), shadow)
                
                # Paste phone frame
                canvas.paste(phone_frame, (phone_x, phone_y), phone_frame)
        
        # 4. Specifications (SMALLER - moved to left side)
        y_spec = 270
        spec_width = 350  # Narrower specs column
        
        for icon_key, value in specs[:4]:  # Show only 4 key specs
            # Spec card with creative design
            draw.rounded_rectangle([40, y_spec, 40 + spec_width, y_spec + 60], 
                                 radius=12, fill=(61, 43, 43, 220))
            
            # Icon with background
            icon_bg_size = 36
            icon_bg = Image.new("RGBA", (icon_bg_size, icon_bg_size), (255, 255, 255, 20))
            icon_bg_draw = ImageDraw.Draw(icon_bg)
            icon_bg_draw.ellipse([2, 2, icon_bg_size-2, icon_bg_size-2], 
                               fill=(197, 160, 89, 80))
            
            icon = self.load_icon(icon_key, (24, 24))
            if icon:
                icon_x = (icon_bg_size - icon.width) // 2
                icon_y = (icon_bg_size - icon.height) // 2
                icon_bg.paste(icon, (icon_x, icon_y), icon)
            
            canvas.paste(icon_bg, (55, y_spec + 12), icon_bg)
            
            # Spec text
            draw.text((100, y_spec + 15), value, font=self.f_spec, fill="white")
            
            y_spec += 75
        
        # 5. Price badge (prominent)
        price_text = f"KES {price}"
        text_width = draw.textlength(price_text, font=self.f_price)
        badge_width = max(text_width + 80, 300)
        badge_height = 90
        
        badge_x = (1080 - badge_width) // 2
        badge_y = 820
        
        # Creative badge with gradient effect
        for i in range(badge_height):
            factor = i / badge_height
            r = int(62 * (1 - factor) + 40 * factor)
            g = int(180 * (1 - factor) + 140 * factor)
            b = int(137 * (1 - factor) + 100 * factor)
            draw.line([(badge_x, badge_y + i), (badge_x + badge_width, badge_y + i)], 
                     fill=(r, g, b))
        
        # Rounded corners
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_width, badge_y + badge_height], 
                             radius=20, outline="white", width=3)
        
        # Price text with shadow
        price_x = badge_x + (badge_width - text_width) // 2
        draw.text((price_x + 2, badge_y + 23), price_text, font=self.f_price, 
                 fill=(0, 0, 0, 100))
        draw.text((price_x, badge_y + 20), price_text, font=self.f_price, 
                 fill="white")
        
        # 6. Footer with contact (IMPROVED VISIBILITY)
        footer_bg = Image.new("RGBA", (1080, 100), (26, 15, 15, 240))
        canvas.paste(footer_bg, (0, 980), footer_bg)
        
        # Contact items with better spacing
        contacts = [
            ("web", CONTACT["web"], 150),
            ("location", CONTACT["location"], 450),
            ("whatsapp", CONTACT["whatsapp"], 750)
        ]
        
        for icon_key, text, x_pos in contacts:
            icon = self.load_icon(icon_key, (28, 28))
            if icon:
                # Icon with circular background
                icon_bg = Image.new("RGBA", (36, 36), (197, 160, 89, 150))
                icon_bg_draw = ImageDraw.Draw(icon_bg)
                icon_bg_draw.ellipse([2, 2, 34, 34], outline="white", width=1)
                
                icon_x = (36 - icon.width) // 2
                icon_y = (36 - icon.height) // 2
                icon_bg.paste(icon, (icon_x, icon_y), icon)
                
                canvas.paste(icon_bg, (x_pos, 990), icon_bg)
            
            # Text with better contrast
            text_color = CONFIG["brand"]["light_gold"]
            draw.text((x_pos + 45, 995), text, font=self.f_footer, fill=text_color)
        
        return canvas

# ==========================================
# 4. DATA FETCHING
# ==========================================
def fetch_phone_data(query):
    """Fetch phone data from API"""
    try:
        # Search for phone
        search_url = f"{CONFIG['api_base']}/gsm/search?q={query}"
        search_res = requests.get(search_url, timeout=10)
        if search_res.status_code != 200:
            return None
            
        search_data = search_res.json()
        if not search_data:
            return None
        
        phone = search_data[0]
        phone_id = phone['id']
        
        # Get details
        info_url = f"{CONFIG['api_base']}/gsm/info/{phone_id}"
        info = requests.get(info_url, timeout=10).json()
        
        # Get images
        img_url = f"{CONFIG['api_base']}/gsm/images/{phone_id}"
        images = requests.get(img_url, timeout=10).json()
        
        # Get best image
        hero_url = images['images'][1] if len(images['images']) > 1 else images['images'][0]
        
        # Parse specs
        specs = []
        
        # Display
        display = info.get("display", {}).get("size", "6.7")
        specs.append(("screen", f"{display.split()[0]}\" Display"))
        
        # Camera
        camera = info.get("mainCamera", {}).get("mainModules", "12MP")
        specs.append(("camera", f"{camera.split()[0]} Camera"))
        
        # Memory
        memory = info.get("memory", [{}])[0].get("value", "")
        ram_match = re.search(r'(\d+GB)\s+RAM', memory, re.IGNORECASE)
        storage_match = re.search(r'(\d+GB)\s+(?:internal|storage)', memory, re.IGNORECASE)
        
        specs.append(("memory", ram_match.group(1) if ram_match else "8GB RAM"))
        specs.append(("storage", storage_match.group(1) if storage_match else "256GB"))
        
        # Battery
        battery = info.get("battery", {}).get("battType", "5000")
        specs.append(("battery", f"{battery.split()[0]} mAh"))
        
        return {
            "name": phone['name'],
            "image_url": hero_url,
            "specs": specs
        }
        
    except Exception as e:
        st.warning(f"Could not fetch data: {str(e)[:100]}")
        return None

# ==========================================
# 5. VIDEO GENERATOR
# ==========================================
def create_cinematic_video(static_image, duration=5):
    """Create cinematic video from static image"""
    
    def make_frame(t):
        # Create canvas
        canvas = Image.new("RGB", (1080, 1080), CONFIG["brand"]["maroon"])
        draw = ImageDraw.Draw(canvas)
        
        # Add dynamic particles
        particles = ParticleField(30)
        particles.draw(draw, t)
        
        # Apply blur to background
        canvas = canvas.filter(ImageFilter.GaussianBlur(3))
        
        # Add static ad with creative effects
        img = static_image.copy()
        
        # Zoom effect
        zoom = 1.0 + 0.03 * np.sin(t * 2)  # Gentle pulsing zoom
        new_w = int(1080 * zoom)
        new_h = int(1080 * zoom)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Crop to center
        left = (new_w - 1080) // 2
        top = (new_h - 1080) // 2
        img = img.crop((left, top, left + 1080, top + 1080))
        
        # Add vignette effect
        vignette = Image.new("RGB", (1080, 1080), (0, 0, 0))
        vignette_draw = ImageDraw.Draw(vignette, 'RGBA')
        vignette_draw.ellipse([-200, -200, 1280, 1280], fill=(0, 0, 0, 0))
        vignette_draw.ellipse([100, 100, 980, 980], fill=(0, 0, 0, 80))
        img = Image.blend(img, vignette, 0.2)
        
        return np.array(img)
    
    return VideoClip(make_frame, duration=duration)

# ==========================================
# 6. MAIN APP
# ==========================================
def main():
    st.set_page_config(
        page_title="Triple K Studio Pro",
        layout="wide",
        page_icon="📱"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(45deg, #2D1B1B, #C5A059);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #3EB489;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .stButton > button {
        background: linear-gradient(45deg, #2D1B1B, #C5A059);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        font-weight: bold;
        border-radius: 10px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(197, 160, 89, 0.4);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: pre-wrap;
        background-color: #2D1B1B;
        border-radius: 5px 5px 0 0;
        gap: 1rem;
        padding: 10px 16px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">📱 TRIPLE K CREATIVE STUDIO</h1>', unsafe_allow_html=True)
    st.markdown("### *Professional Mobile Advertising Generator*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Campaign Settings")
        
        # Device search
        device_query = st.text_input(
            "📱 Device Name", 
            value="iPhone 15 Pro Max",
            help="Enter phone model (e.g., Samsung S23 Ultra)"
        )
        
        # Price
        price = st.text_input(
            "💰 Price (KES)", 
            value="185,000",
            help="Enter price in Kenyan Shillings"
        )
        
        # Status badge
        status = st.selectbox(
            "🏷️ Status Badge",
            options=["None", "🔥 FLASH SALE", "🆕 JUST LAUNCHED", "⚡ LIMITED STOCK", "⭐ PREMIUM"],
            index=0
        )
        
        # Additional options
        with st.expander("🎨 Advanced Options"):
            video_duration = st.slider("Video Duration (seconds)", 3, 10, 5)
            particle_intensity = st.slider("Particle Effects", 0, 100, 50)
        
        st.markdown("---")
        st.markdown("### 📞 Contact Info")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**WhatsApp**")
            st.code(CONTACT["whatsapp"])
        with col2:
            st.markdown("**Website**")
            st.code(CONTACT["web"])
        with col3:
            st.markdown("**Location**")
            st.code(CONTACT["location"])
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<p class="sub-header">🔍 Device Search</p>', unsafe_allow_html=True)
        
        if st.button("🔍 SEARCH DEVICE DATABASE", use_container_width=True):
            with st.spinner("Searching global database..."):
                phone_data = fetch_phone_data(device_query)
                
                if phone_data:
                    st.session_state.phone_data = phone_data
                    st.success(f"✅ Found: **{phone_data['name']}**")
                    
                    # Display specs
                    with st.expander("📊 Device Specifications", expanded=True):
                        for icon, spec in phone_data['specs']:
                            st.markdown(f"• **{spec}**")
                    
                    # Try to show device image
                    try:
                        response = requests.get(phone_data['image_url'], timeout=10)
                        if response.status_code == 200:
                            phone_img = Image.open(BytesIO(response.content))
                            st.image(phone_img, caption="Original Product Image", use_container_width=True)
                    except:
                        st.info("📷 Phone image available for ad generation")
                else:
                    st.error("❌ Device not found in database")
                    st.info("Try: iPhone 15 Pro, Samsung S23, Google Pixel 8, etc.")
        
        # Manual input option
        with st.expander("📝 Manual Specification Input"):
            manual_name = st.text_input("Custom Device Name", value=device_query)
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                display = st.text_input("Display", "6.7\" Super Retina XDR")
                camera = st.text_input("Camera", "48MP Pro System")
            with col_s2:
                memory = st.text_input("Memory", "8GB RAM")
                battery = st.text_input("Battery", "5000mAh")
            
            if st.button("Use Custom Specs", use_container_width=True):
                specs_list = [
                    ("screen", display),
                    ("camera", camera),
                    ("memory", memory),
                    ("battery", battery)
                ]
                st.session_state.phone_data = {
                    "name": manual_name,
                    "image_url": "",
                    "specs": specs_list
                }
                st.success("Custom specs saved!")
    
    with col2:
        st.markdown('<p class="sub-header">🎨 Ad Generator</p>', unsafe_allow_html=True)
        
        if 'phone_data' not in st.session_state:
            st.info("👈 Search for a device first to generate ads")
        else:
            phone_data = st.session_state.phone_data
            
            if st.button("✨ GENERATE CREATIVE AD", use_container_width=True):
                # Create tabs
                tab1, tab2, tab3 = st.tabs(["🎨 Image Ad", "🎥 Video Ad", "📋 Marketing Copy"])
                
                with tab1:
                    with st.spinner("Creating premium ad design..."):
                        try:
                            # Get phone image
                            phone_img = None
                            if phone_data.get('image_url'):
                                response = requests.get(phone_data['image_url'], timeout=10)
                                if response.status_code == 200:
                                    phone_img = Image.open(BytesIO(response.content)).convert("RGBA")
                            
                            # Render ad
                            engine = TripleKEngine()
                            ad_image = engine.render_ad(
                                phone_data['name'],
                                price,
                                phone_img,
                                phone_data['specs']
                            )
                            
                            # Display
                            st.image(ad_image, use_container_width=True)
                            
                            # Download buttons
                            col_d1, col_d2 = st.columns(2)
                            
                            with col_d1:
                                img_bytes = BytesIO()
                                ad_image.save(img_bytes, format='PNG', optimize=True)
                                st.download_button(
                                    label="📥 Download PNG",
                                    data=img_bytes.getvalue(),
                                    file_name=f"TripleK_{phone_data['name'].replace(' ', '_')}.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                            
                            with col_d2:
                                jpg_bytes = BytesIO()
                                ad_image.convert('RGB').save(jpg_bytes, format='JPEG', quality=95)
                                st.download_button(
                                    label="📥 Download JPEG",
                                    data=jpg_bytes.getvalue(),
                                    file_name=f"TripleK_{phone_data['name'].replace(' ', '_')}.jpg",
                                    mime="image/jpeg",
                                    use_container_width=True
                                )
                            
                            # Store for video
                            st.session_state.ad_image = ad_image
                            
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                
                with tab2:
                    if 'ad_image' in st.session_state:
                        if st.button("🎬 GENERATE CINEMATIC VIDEO", use_container_width=True):
                            with st.spinner("Rendering cinematic video..."):
                                try:
                                    video_clip = create_cinematic_video(
                                        st.session_state.ad_image, 
                                        duration=video_duration
                                    )
                                    
                                    # Save to temp file
                                    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                                        video_clip.write_videofile(
                                            tmp.name,
                                            fps=30,
                                            codec='libx264',
                                            audio=False,
                                            ffmpeg_params=['-pix_fmt', 'yuv420p', '-crf', '18'],
                                            logger=None
                                        )
                                        
                                        # Display
                                        st.video(tmp.name)
                                        
                                        # Download
                                        with open(tmp.name, 'rb') as f:
                                            video_bytes = f.read()
                                        
                                        st.download_button(
                                            label="🎥 Download MP4",
                                            data=video_bytes,
                                            file_name=f"TripleK_Video_{phone_data['name'].replace(' ', '_')}.mp4",
                                            mime="video/mp4",
                                            use_container_width=True
                                        )
                                        
                                except Exception as e:
                                    st.error(f"Video error: {str(e)}")
                    else:
                        st.info("Generate an image first to create video")
                
                with tab3:
                    # Marketing copy generator
                    st.markdown("### 📱 Marketing Copy (Ready to Post)")
                    
                    copy_text = f"""
🔥 **{phone_data['name'].upper()} - NOW AVAILABLE!** 🔥

✨ **PREMIUM FEATURES:**
"""
                    for icon, spec in phone_data['specs'][:4]:
                        copy_text += f"• {spec}\n"
                    
                    copy_text += f"""

💰 **EXCLUSIVE PRICE: KES {price}**
✅ Brand New | Genuine Warranty
✅ Official Kenya Stock | Ready for Delivery

📍 **VISIT OUR PREMIUM SHOWROOM:**
📱 WhatsApp: {CONTACT['whatsapp']}
🌐 Website: {CONTACT['web']}
🗺️ Location: {CONTACT['location']}

#TripleK #MobileTech #Nairobi #Kenya #SmartphoneDeal #{phone_data['name'].replace(' ', '')}
"""
                    
                    st.text_area("Copy and paste for social media:", copy_text, height=250)
                    
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        if st.button("📋 Copy to Clipboard", use_container_width=True):
                            st.code(copy_text)
                            st.success("Copied!")
                    with col_c2:
                        st.download_button(
                            label="📄 Download as Text",
                            data=copy_text,
                            file_name=f"TripleK_Copy_{phone_data['name'].replace(' ', '_')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

# Run the app
if __name__ == "__main__":
    main()
