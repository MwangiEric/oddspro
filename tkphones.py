import streamlit as st
import requests
import re
import numpy as np
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from moviepy.editor import VideoClip, CompositeVideoClip
import random

# ==========================================
# 1. CONFIGURATION
# ==========================================
CONTACT = {
    "whatsapp": "+254 700 123 456",
    "website": "www.triplek.co.ke",
    "location": "CBD, Nairobi, Kenya"
}

BRAND = {
    "primary": "#1A0F0F",      # Deep Maroon
    "secondary": "#D4AF37",    # Rich Gold
    "accent": "#3EB489",       # Mint Green
    "dark": "#0A0707",         # Near Black
    "light": "#F5F5F5",        # Off White
    "spec_bg": "#2A1E1E"       # Spec badge background
}

LAYOUTS = {
    "TikTok": {"size": (1080, 1920), "type": "story", "video": True},
    "WhatsApp": {"size": (1080, 1920), "type": "story", "video": True},
    "Facebook": {"size": (1200, 630), "type": "landscape", "video": True}
}

# ==========================================
# 2. UTILITY FUNCTIONS
# ==========================================
def get_font(size, bold=False):
    """Safe font loader with fallback"""
    try:
        if bold:
            return ImageFont.truetype("assets/font/poppins_bold.ttf", size)
        else:
            return ImageFont.truetype("assets/font/poppins_regular.ttf", size)
    except:
        # Fallback to default font
        return ImageFont.load_default()

def fetch_phone_image(url):
    """Download phone image with better error handling"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        # Return a placeholder if image fails to load
        placeholder = Image.new("RGBA", (500, 800), (100, 100, 100, 100))
        draw = ImageDraw.Draw(placeholder)
        draw.text((100, 400), "📱", font=get_font(100), fill=(255, 255, 255, 180))
        return placeholder

def load_local_icon(icon_name, size=(40, 40)):
    """Load icon from local assets folder"""
    icon_paths = {
        "display": "assets/img/screen.png",
        "camera": "assets/img/camera.png",
        "storage": "assets/img/storage.png",
        "battery": "assets/img/battery.png",
        "ram": "assets/img/memory.png",
        "processor": "assets/img/camera.png",  # Placeholder, use camera icon
        "logo": "assets/img/logo.png",
        "whatsapp": "assets/img/whatsapp.png",
        "location": "assets/img/location.png",
        "web": "assets/img/web.png"
    }
    
    try:
        if icon_name in icon_paths:
            icon = Image.open(icon_paths[icon_name]).convert("RGBA")
            icon.thumbnail(size, Image.Resampling.LANCZOS)
            return icon
    except:
        pass
    
    # Fallback: create simple icon
    return Image.new("RGBA", size, (255, 255, 255, 30))

def parse_specs(info):
    """Improved spec parsing with RAM and Processor"""
    specs = []
    
    # Display
    display_size = info.get("display", {}).get("size", "6.7")
    display_match = re.search(r'(\d+\.?\d*)', str(display_size))
    specs.append(("display", f"{display_match.group(1) if display_match else '6.7'}\" Display"))
    
    # Camera
    camera = info.get("mainCamera", {}).get("mainModules", "48MP")
    camera_match = re.search(r'(\d+MP)', str(camera))
    specs.append(("camera", f"{camera_match.group(1) if camera_match else '48MP'} Camera"))
    
    # Storage
    memory_text = str(info.get("memory", ""))
    storage_match = re.search(r'(\d+GB|\d+TB)', memory_text)
    specs.append(("storage", storage_match.group(1) if storage_match else "256GB"))
    
    # Battery - IMPROVED PARSING
    battery_data = info.get("battery", {})
    battery_str = str(battery_data.get("battType", "5000"))
    
    # Try multiple patterns
    patterns = [
        r'(\d+)\s*mAh',  # "5000 mAh"
        r'(\d+)mAh',     # "5000mAh"
        r'(\d+)\s*MAh',  # "5000 MAh"
        r'(\d+)',        # Just digits
    ]
    
    battery_value = "5000"
    for pattern in patterns:
        match = re.search(pattern, battery_str, re.IGNORECASE)
        if match:
            battery_value = match.group(1)
            break
    
    specs.append(("battery", f"{battery_value} mAh Battery"))
    
    # RAM
    ram_match = re.search(r'(\d+GB)\s+RAM', memory_text, re.IGNORECASE)
    specs.append(("ram", ram_match.group(1) if ram_match else "8GB RAM"))
    
    # Processor
    platform_data = info.get("platform", {})
    processor = platform_data.get("chipset", platform_data.get("CPU", "Octa-core"))
    # Clean up processor name
    if "octa" in processor.lower() or "8-" in processor.lower():
        processor = "Octa-core"
    elif "hexa" in processor.lower() or "6-" in processor.lower():
        processor = "Hexa-core"
    elif "quad" in processor.lower() or "4-" in processor.lower():
        processor = "Quad-core"
    
    specs.append(("processor", f"{processor[:15]}"))
    
    return specs[:6]  # Return first 6 specs max

# ==========================================
# 3. PROFESSIONAL AD ENGINE
# ==========================================
class ProAdEngine:
    def __init__(self, layout_name):
        self.layout_name = layout_name
        self.layout = LAYOUTS[layout_name]
        self.width, self.height = self.layout["size"]
        
        # Professional font sizing
        if self.layout["type"] == "story":
            self.f_title = get_font(72, True)     # Device name
            self.f_price = get_font(64, True)     # Price
            self.f_spec_label = get_font(32, True) # Spec label
            self.f_spec_value = get_font(36)      # Spec value
            self.f_cta = get_font(42, True)       # Call to action
            self.f_footer = get_font(30)          # Footer text
        else:  # landscape
            self.f_title = get_font(56, True)
            self.f_price = get_font(60, True)
            self.f_spec_label = get_font(26, True)
            self.f_spec_value = get_font(28)
            self.f_cta = get_font(34, True)
            self.f_footer = get_font(24)
    
    def add_phone_effects(self, phone_img):
        """Add professional shadow and border to phone image"""
        if not phone_img:
            return None
            
        # Create shadow
        shadow_size = (phone_img.width + 40, phone_img.height + 40)
        shadow = Image.new('RGBA', shadow_size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        
        # Draw elliptical shadow at bottom
        shadow_draw.ellipse([
            20, phone_img.height - 10,
            phone_img.width + 20, phone_img.height + 50
        ], fill=(0, 0, 0, 80))
        
        # Blur the shadow
        shadow = shadow.filter(ImageFilter.GaussianBlur(15))
        
        # Create bordered phone
        bordered_phone = phone_img.copy()
        
        # Add white border
        border_width = 2
        border_img = Image.new('RGBA', bordered_phone.size, (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_img)
        border_draw.rectangle(
            [(border_width, border_width), 
             (bordered_phone.width - border_width, 
              bordered_phone.height - border_width)],
            outline=(255, 255, 255, 60),
            width=border_width
        )
        
        bordered_phone = Image.alpha_composite(bordered_phone, border_img)
        
        return bordered_phone, shadow
    
    def create_spec_row(self, icon_name, label, value, width=800, height=80):
        """Create professional spec row with icon, label, and value"""
        badge = Image.new('RGBA', (width, height), (255, 255, 255, 20))
        draw = ImageDraw.Draw(badge)
        
        # Background with subtle gradient
        draw.rounded_rectangle(
            [(0, 0), (width, height)], 
            radius=20, 
            fill=BRAND["spec_bg"]
        )
        
        # Left border accent
        draw.rectangle([(0, 0), (5, height)], fill=BRAND["accent"])
        
        # Load icon
        icon = load_local_icon(icon_name, (40, 40))
        if icon:
            badge.paste(icon, (20, (height - icon.height) // 2), icon)
        
        # Label (left side)
        draw.text(
            (75, height // 2 - 20), 
            label.upper(), 
            font=self.f_spec_label, 
            fill=BRAND["secondary"]
        )
        
        # Value (right side, aligned)
        value_width = draw.textlength(value, font=self.f_spec_value)
        draw.text(
            (width - value_width - 30, height // 2 - 18), 
            value, 
            font=self.f_spec_value, 
            fill=BRAND["light"]
        )
        
        # Divider line
        draw.line([(75, height - 2), (width - 30, height - 2)], 
                 fill=BRAND["accent"], width=1)
        
        return badge
    
    def render_tiktok_whatsapp(self, name, price, phone_img, specs):
        """Render for TikTok/WhatsApp (Story format)"""
        canvas = Image.new('RGB', (self.width, self.height), BRAND["primary"])
        draw = ImageDraw.Draw(canvas)
        
        # Background with gradient
        for y in range(self.height):
            ratio = y / self.height
            r = int(26 * (1 - ratio) + 10 * ratio)
            g = int(15 * (1 - ratio) + 7 * ratio)
            b = int(15 * (1 - ratio) + 7 * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        # Add subtle noise texture
        noise = Image.effect_noise((self.width, self.height), 10)
        canvas = Image.blend(canvas.convert('RGB'), noise.convert('RGB'), 0.02)
        draw = ImageDraw.Draw(canvas)
        
        # Phone image with effects (ALWAYS SHOW)
        phone_with_effects = None
        if phone_img:
            phone_img.thumbnail((650, 850), Image.Resampling.LANCZOS)
            bordered_phone, shadow = self.add_phone_effects(phone_img)
            
            # Position phone
            phone_x = (self.width - bordered_phone.width) // 2
            phone_y = 200
            
            # Paste shadow first
            shadow_x = phone_x - 20
            shadow_y = phone_y - 20
            canvas.paste(shadow, (shadow_x, shadow_y), shadow)
            
            # Paste phone
            canvas.paste(bordered_phone, (phone_x, phone_y), bordered_phone)
            
            phone_with_effects = bordered_phone
        
        # Device name (top center)
        name_text = name.upper()[:22]
        name_width = draw.textlength(name_text, font=self.f_title)
        name_x = (self.width - name_width) // 2
        draw.text((name_x, 80), name_text, font=self.f_title, fill=BRAND["light"])
        
        # Specifications - ONE PER ROW
        spec_start_y = phone_y + (phone_img.height if phone_img else 0) + 100
        spec_gap = 15
        spec_width = 900
        
        # Center specs
        spec_x = (self.width - spec_width) // 2
        
        for i, (icon_key, spec_text) in enumerate(specs[:5]):  # Show first 5 specs
            spec_y = spec_start_y + i * (85 + spec_gap)
            
            # Create spec row
            spec_badge = self.create_spec_row(
                icon_key, 
                icon_key.upper(), 
                spec_text, 
                spec_width, 
                80
            )
            
            canvas.paste(spec_badge, (spec_x, spec_y), spec_badge)
        
        # Price badge - CENTERED AND PROPER
        price_y = spec_start_y + 5 * (85 + spec_gap) + 40
        price_width = 600
        price_height = 100
        
        # Price background with gradient
        for py in range(price_height):
            factor = py / price_height
            r = int(62 * (1 - factor) + 40 * factor)
            g = int(180 * (1 - factor) + 140 * factor)
            b = int(137 * (1 - factor) + 100 * factor)
            if py == 0:
                price_bg_color = (r, g, b)
        
        price_x = (self.width - price_width) // 2
        
        # Draw price badge
        draw.rounded_rectangle(
            [price_x, price_y, price_x + price_width, price_y + price_height],
            radius=25,
            fill=BRAND["accent"]
        )
        
        # Price text - PERFECTLY CENTERED
        price_text = f"KES {price}"
        text_width = draw.textlength(price_text, font=self.f_price)
        text_x = price_x + (price_width - text_width) // 2
        text_y = price_y + (price_height - 64) // 2
        
        draw.text(
            (text_x, text_y),
            price_text,
            font=self.f_price,
            fill=BRAND["primary"]
        )
        
        # Call to Action
        cta_y = price_y + price_height + 40
        cta_text = "🔥 LIMITED STOCK | FREE DELIVERY"
        cta_width = draw.textlength(cta_text, font=self.f_cta)
        cta_x = (self.width - cta_width) // 2
        draw.text((cta_x, cta_y), cta_text, font=self.f_cta, fill=BRAND["secondary"])
        
        # Contact footer
        footer_y = self.height - 150
        draw.rectangle([0, footer_y, self.width, self.height], fill=BRAND["dark"])
        
        # Load and add logo to footer
        logo = load_local_icon("logo", (120, 40))
        if logo:
            logo_x = (self.width - logo.width) // 2
            canvas.paste(logo, (logo_x, footer_y + 20), logo)
        
        # Contact info
        contact_text = f"📱 {CONTACT['whatsapp']}  |  🌐 {CONTACT['website']}"
        contact_width = draw.textlength(contact_text, font=self.f_footer)
        contact_x = (self.width - contact_width) // 2
        
        draw.text(
            (contact_x, footer_y + 80),
            contact_text,
            font=self.f_footer,
            fill=BRAND["secondary"]
        )
        
        # Location
        location_text = f"📍 {CONTACT['location']}"
        location_width = draw.textlength(location_text, font=self.f_footer)
        location_x = (self.width - location_width) // 2
        
        draw.text(
            (location_x, footer_y + 120),
            location_text,
            font=self.f_footer,
            fill=(255, 255, 255, 200)
        )
        
        return canvas
    
    def render_facebook(self, name, price, phone_img, specs):
        """Render for Facebook (Landscape)"""
        canvas = Image.new('RGB', (self.width, self.height), BRAND["primary"])
        draw = ImageDraw.Draw(canvas)
        
        # Gradient background
        for x in range(self.width):
            ratio = x / self.width
            r = int(26 * (1 - ratio) + 15 * ratio)
            g = int(15 * (1 - ratio) + 10 * ratio)
            b = int(15 * (1 - ratio) + 10 * ratio)
            draw.line([(x, 0), (x, self.height)], fill=(r, g, b))
        
        # Left content area
        content_width = 650
        
        # Load and add logo
        logo = load_local_icon("logo", (180, 60))
        if logo:
            canvas.paste(logo, (50, 30), logo)
        
        # Device name
        name_text = name.upper()[:25]
        draw.text((50, 110), name_text, font=self.f_title, fill=BRAND["light"])
        
        # Specifications - ONE PER ROW
        y_offset = 200
        spec_width = 500
        
        for icon_key, spec_text in specs[:5]:  # Show first 5 specs
            spec_badge = self.create_spec_row(
                icon_key,
                icon_key.upper(),
                spec_text,
                spec_width,
                65
            )
            canvas.paste(spec_badge, (50, y_offset), spec_badge)
            y_offset += 80
        
        # Price badge - PROPERLY ALIGNED
        price_width = 500
        price_height = 90
        price_x = 50
        price_y = y_offset + 20
        
        # Price background
        draw.rounded_rectangle(
            [price_x, price_y, price_x + price_width, price_y + price_height],
            radius=20,
            fill=BRAND["accent"]
        )
        
        # Price text - CENTERED
        price_text = f"KES {price}"
        text_width = draw.textlength(price_text, font=self.f_price)
        text_x = price_x + (price_width - text_width) // 2
        text_y = price_y + (price_height - 60) // 2
        
        draw.text(
            (text_x, text_y),
            price_text,
            font=self.f_price,
            fill=BRAND["primary"]
        )
        
        # Phone image on right - ALWAYS SHOW
        if phone_img:
            phone_img.thumbnail((450, 600), Image.Resampling.LANCZOS)
            bordered_phone, shadow = self.add_phone_effects(phone_img)
            
            # Position phone with shadow
            phone_x = self.width - bordered_phone.width - 100
            phone_y = (self.height - bordered_phone.height) // 2
            
            # Paste shadow
            shadow_x = phone_x - 15
            shadow_y = phone_y - 15
            canvas.paste(shadow, (shadow_x, shadow_y), shadow)
            
            # Paste phone
            canvas.paste(bordered_phone, (phone_x, phone_y), bordered_phone)
        else:
            # Create placeholder phone
            placeholder = Image.new("RGBA", (400, 550), (50, 50, 50, 180))
            placeholder_draw = ImageDraw.Draw(placeholder)
            placeholder_draw.rectangle([(10, 10), (390, 540)], 
                                     outline=BRAND["secondary"], width=2)
            placeholder_draw.text((150, 250), "📱", font=get_font(80), 
                                fill=BRAND["secondary"])
            
            phone_x = self.width - placeholder.width - 100
            phone_y = (self.height - placeholder.height) // 2
            canvas.paste(placeholder, (phone_x, phone_y), placeholder)
        
        # Call to Action
        cta_text = "🚀 ORDER NOW | FREE DELIVERY IN NAIROBI"
        cta_width = draw.textlength(cta_text, font=self.f_cta)
        cta_x = (self.width - cta_width) // 2
        
        draw.text(
            (cta_x, self.height - 120),
            cta_text,
            font=self.f_cta,
            fill=BRAND["secondary"]
        )
        
        # Footer
        footer_y = self.height - 70
        draw.rectangle([0, footer_y, self.width, self.height], fill=BRAND["dark"])
        
        # Contact info
        contact_text = f"📱 {CONTACT['whatsapp']}  |  📍 {CONTACT['location']}"
        contact_width = draw.textlength(contact_text, font=self.f_footer)
        contact_x = (self.width - contact_width) // 2
        
        draw.text(
            (contact_x, footer_y + 20),
            contact_text,
            font=self.f_footer,
            fill=BRAND["secondary"]
        )
        
        return canvas
    
    def render_ad(self, name, price, phone_img, specs):
        """Main render method"""
        if self.layout_name in ["TikTok", "WhatsApp"]:
            return self.render_tiktok_whatsapp(name, price, phone_img, specs)
        else:  # Facebook
            return self.render_facebook(name, price, phone_img, specs)

# ==========================================
# 4. SIMPLE VIDEO ENGINE
# ==========================================
class VideoEngine:
    def generate_video(self, pil_image, duration=6):
        """Simple Ken Burns zoom effect"""
        w, h = pil_image.size
        
        def make_frame(t):
            # Smooth zoom
            zoom = 1.0 + (0.08 * (t / duration))
            nw, nh = int(w * zoom), int(h * zoom)
            
            # Resize
            resized = pil_image.resize((nw, nh), Image.Resampling.LANCZOS)
            
            # Center crop
            left = (nw - w) // 2
            top = (nh - h) // 2
            
            # Ensure bounds
            left = max(0, min(left, nw - w))
            top = max(0, min(top, nh - h))
            right = left + w
            bottom = top + h
            
            cropped = resized.crop((left, top, right, bottom))
            return np.array(cropped.convert("RGB"))
        
        return VideoClip(make_frame, duration=duration)

# ==========================================
# 5. STREAMLIT APP
# ==========================================
def main():
    st.set_page_config(
        page_title="Triple K Pro Studio",
        layout="wide",
        page_icon="📱"
    )
    
    # Professional CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #1A0F0F 0%, #D4AF37 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .stButton>button {
        background: linear-gradient(45deg, #1A0F0F, #3EB489);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-weight: bold;
        width: 100%;
        margin: 0.5rem 0;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(45deg, #3EB489, #D4AF37);
        color: #1A0F0F;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(212, 175, 55, 0.4);
    }
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px;
        border: 2px solid #D4AF37;
    }
    .stTextInput input {
        border-radius: 10px;
        border: 2px solid #3EB489;
    }
    .info-box {
        background: rgba(62, 180, 137, 0.1);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3EB489;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📱 TRIPLE K AGENCY STUDIO</h1>
        <p style="opacity: 0.9;">Professional Mobile Advertising Generator</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'phone_data' not in st.session_state:
        st.session_state.phone_data = None
    if 'ad_image' not in st.session_state:
        st.session_state.ad_image = None
    if 'generated_video' not in st.session_state:
        st.session_state.generated_video = None
    
    # Layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### ⚙️ Campaign Settings")
        
        # Device search
        query = st.text_input("**Search Device**", "iPhone 15 Pro")
        
        # Price
        price = st.text_input("**Price (KES)**", "135,000")
        
        # Platform selection
        platform = st.selectbox("**Platform**", list(LAYOUTS.keys()))
        
        # Generate button
        if st.button("🚀 Fetch & Generate Ad", use_container_width=True, type="primary"):
            with st.spinner("Creating professional ad..."):
                try:
                    # Fetch phone data
                    search_url = f"https://tkphsp2.vercel.app/gsm/search?q={query}"
                    search = requests.get(search_url, timeout=10).json()
                    
                    if search and len(search) > 0:
                        phone_id = search[0]['id']
                        
                        # Get info and images
                        info_url = f"https://tkphsp2.vercel.app/gsm/info/{phone_id}"
                        info = requests.get(info_url, timeout=10).json()
                        
                        imgs_url = f"https://tkphsp2.vercel.app/gsm/images/{phone_id}"
                        imgs = requests.get(imgs_url, timeout=10).json()
                        
                        # Get best image (try multiple indices)
                        image_url = ""
                        if imgs.get('images'):
                            for idx in [0, 1, 2]:
                                if idx < len(imgs['images']):
                                    image_url = imgs['images'][idx]
                                    if image_url.startswith('http'):
                                        break
                        
                        # Parse specs (with RAM and Processor)
                        specs = parse_specs(info)
                        
                        # Store data
                        st.session_state.phone_data = {
                            "name": search[0]['name'],
                            "specs": specs,
                            "image_url": image_url,
                            "raw_info": info
                        }
                        
                        # Generate ad
                        engine = ProAdEngine(platform)
                        phone_img = fetch_phone_image(image_url)
                        
                        ad_image = engine.render_ad(
                            search[0]['name'],
                            price,
                            phone_img,
                            specs
                        )
                        
                        st.session_state.ad_image = ad_image
                        st.session_state.generated_video = None  # Clear previous video
                        st.success(f"✅ {platform} ad generated successfully!")
                        
                    else:
                        st.error("Device not found. Try another name.")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Manual input section
        with st.expander("📝 Manual Input (Optional)"):
            manual_name = st.text_input("Device Name", query)
            manual_price = st.text_input("Price", price)
            
            if st.button("Use Manual Data", use_container_width=True):
                st.session_state.phone_data = {
                    "name": manual_name,
                    "specs": [
                        ("display", "6.7\" Super Retina"),
                        ("camera", "48MP Pro System"),
                        ("storage", "256GB"),
                        ("battery", "5000 mAh"),
                        ("ram", "8GB RAM"),
                        ("processor", "A16 Bionic")
                    ],
                    "image_url": ""
                }
                st.success("✅ Using manual data")
        
        # Information box
        st.markdown("""
        <div class="info-box">
        <h4>ℹ️ How to use:</h4>
        <ol>
        <li>Enter device name</li>
        <li>Set price in KES</li>
        <li>Select platform</li>
        <li>Click "Fetch & Generate"</li>
        <li>Download your ad</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Contact info
        st.markdown("---")
        st.markdown("### 📞 Contact")
        st.caption(f"**WhatsApp:** {CONTACT['whatsapp']}")
        st.caption(f"**Website:** {CONTACT['website']}")
        st.caption(f"**Location:** {CONTACT['location']}")
    
    with col2:
        st.markdown("### 🎨 Ad Preview")
        
        if st.session_state.ad_image:
            # Display ad
            st.image(st.session_state.ad_image, use_container_width=True)
            
            # Display specs if available
            if st.session_state.phone_data:
                with st.expander("📊 Device Specifications"):
                    specs = st.session_state.phone_data["specs"]
                    for icon_key, spec_text in specs:
                        st.write(f"• **{icon_key.upper()}:** {spec_text}")
            
            # Download section
            st.markdown("---")
            st.markdown("### 📥 Export Options")
            
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                # PNG download
                buf = BytesIO()
                st.session_state.ad_image.save(buf, format="PNG", quality=95)
                st.download_button(
                    "📥 Download PNG",
                    buf.getvalue(),
                    f"triplek_{platform.lower()}.png",
                    "image/png",
                    use_container_width=True
                )
            
            with col_d2:
                # JPEG download
                buf_jpg = BytesIO()
                st.session_state.ad_image.convert("RGB").save(buf_jpg, 
                                                           format="JPEG", 
                                                           quality=95)
                st.download_button(
                    "📥 Download JPEG",
                    buf_jpg.getvalue(),
                    f"triplek_{platform.lower()}.jpg",
                    "image/jpeg",
                    use_container_width=True
                )
            
            # Video generation
            st.markdown("---")
            st.markdown("### 🎬 Video Ad")
            
            if st.button("🎥 Generate Video Ad", use_container_width=True):
                with st.spinner("Creating cinematic video..."):
                    try:
                        video_engine = VideoEngine()
                        clip = video_engine.generate_video(st.session_state.ad_image)
                        
                        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                            clip.write_videofile(
                                tmp.name,
                                fps=24,
                                codec='libx264',
                                ffmpeg_params=['-pix_fmt', 'yuv420p', '-crf', '18'],
                                logger=None
                            )
                            
                            with open(tmp.name, "rb") as f:
                                video_bytes = f.read()
                                st.session_state.generated_video = video_bytes
                            
                            # Clean up temp file
                            os.unlink(tmp.name)
                        
                        st.success("✅ Video generated successfully!")
                        
                    except Exception as e:
                        st.error(f"Video generation error: {str(e)}")
            
            # Display and download video if available
            if st.session_state.generated_video:
                st.video(st.session_state.generated_video)
                
                st.download_button(
                    "📥 Download MP4",
                    st.session_state.generated_video,
                    f"triplek_{platform.lower()}_video.mp4",
                    "video/mp4",
                    use_container_width=True
                )
        
        else:
            # Welcome message
            st.markdown("""
            <div class="info-box">
            <h3>Welcome to Triple K Agency Studio</h3>
            <p>Create professional mobile ads in seconds!</p>
            
            <h4>🎯 Supported Platforms:</h4>
            <ul>
            <li><strong>TikTok</strong> - 1080x1920 (Vertical Story)</li>
            <li><strong>WhatsApp</strong> - 1080x1920 (Status Format)</li>
            <li><strong>Facebook</strong> - 1200x630 (Landscape Post)</li>
            </ul>
            
            <h4>✨ Features:</h4>
            <ul>
            <li>Professional design with icons</li>
            <li>Phone shadows & borders</li>
            <li>One spec per row layout</li>
            <li>RAM & Processor included</li>
            <li>Video ad generation</li>
            <li>Multiple export formats</li>
            </ul>
            
            <p><strong>👈 Start by entering device details in the sidebar</strong></p>
            </div>
            """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.caption("© 2024 Triple K Mobile Agency • Premium Mobile Advertising Solutions")

if __name__ == "__main__":
    main()
