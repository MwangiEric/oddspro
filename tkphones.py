import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import Optional, Tuple, Dict, List
import re
import base64

# ==========================================
# CONFIGURATION
# ==========================================
BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
BRAND_ACCENT = "#FF6B35"

TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

# Icon URLs
ICON_URLS = {
    "screen": "https://ik.imagekit.io/ericmwangi/screen.png",
    "camera": "https://ik.imagekit.io/ericmwangi/camera.png",
    "memory": "https://ik.imagekit.io/ericmwangi/memory.png",
    "storage": "https://ik.imagekit.io/ericmwangi/memory.png",
    "battery": "https://ik.imagekit.io/ericmwangi/battery.png",
    "processor": "https://ik.imagekit.io/ericmwangi/processor.png",
}

API_BASE = "https://tkphsp2.vercel.app"

st.set_page_config(page_title="Phone Ad Generator", layout="wide", page_icon="📱")

# ==========================================
# SIMPLE API FUNCTIONS
# ==========================================

@st.cache_data(ttl=3600)
def search_phone(query: str) -> List[Dict]:
    """Search for phones"""
    try:
        url = f"{API_BASE}/gsm/search?q={requests.utils.quote(query)}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json() or []
    except:
        pass
    return []

@st.cache_data(ttl=3600)
def get_phone_details(phone_id: str) -> Optional[Dict]:
    """Get phone details"""
    try:
        url = f"{API_BASE}/gsm/info/{phone_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def get_phone_image(phone_id: str) -> Optional[str]:
    """Get first phone image"""
    try:
        url = f"{API_BASE}/gsm/images/{phone_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "images" in data:
                images = data["images"]
                if images and len(images) > 0:
                    return images[0]
    except:
        pass
    return None

@st.cache_data(ttl=86400)
def download_image(url: str) -> Optional[Image.Image]:
    """Download image"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            return img
    except:
        pass
    return None

@st.cache_data(ttl=86400)
def get_icon(icon_name: str, size: int = 50) -> Optional[Image.Image]:
    """Get icon"""
    if icon_name not in ICON_URLS:
        return create_fallback_icon(icon_name, size)
    
    img = download_image(ICON_URLS[icon_name])
    if img:
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img
    
    return create_fallback_icon(icon_name, size)

def create_fallback_icon(name: str, size: int) -> Image.Image:
    """Create fallback icon"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    colors = {
        "screen": "#2196F3", "camera": "#FF5722", "memory": "#9C27B0",
        "storage": "#673AB7", "battery": "#FF9800", "processor": "#4CAF50",
    }
    
    color = colors.get(name, BRAND_MAROON)
    draw.ellipse([0, 0, size, size], fill=color)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    
    letter = name[0].upper()
    draw.text((size//2, size//2), letter, fill="white", font=font, anchor="mm")
    
    return img

# ==========================================
# IMPROVED SPEC PARSING - FIX STORAGE
# ==========================================

def extract_top_5_specs(details: Dict) -> Dict[str, str]:
    """Extract exactly 5 key specs with FIXED storage parsing"""
    specs = {}
    
    # 1. SCREEN
    display = details.get("display", {})
    screen_size = display.get("size", "")
    if screen_size:
        match = re.search(r'(\d+\.?\d*)\s*inches', str(screen_size), re.IGNORECASE)
        specs["Screen"] = f"{match.group(1)}″ Display" if match else "N/A"
    else:
        specs["Screen"] = "N/A"
    
    # 2. CAMERA
    camera = details.get("mainCamera", {})
    modules = camera.get("mainModules", "")
    if modules:
        mp_matches = re.findall(r'(\d+)\s*MP', str(modules), re.IGNORECASE)
        if mp_matches:
            specs["Camera"] = " + ".join(mp_matches[:2]) + "MP"
        else:
            specs["Camera"] = "N/A"
    else:
        specs["Camera"] = "N/A"
    
    # 3. RAM & 4. STORAGE - IMPROVED PARSING
    memory = details.get("memory", [])
    specs["RAM"] = "N/A"
    specs["Storage"] = "N/A"
    
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            value = str(mem.get("value", ""))
            
            # Try pattern: "8GB RAM, 128GB ROM"
            ram_match = re.search(r'(\d+)\s*GB\s+RAM', value, re.IGNORECASE)
            if ram_match:
                specs["RAM"] = f"{ram_match.group(1)}GB RAM"
            
            # Try storage patterns
            storage_match = re.search(r'(\d+)\s*GB\s+(?:ROM|storage|internal)', value, re.IGNORECASE)
            if storage_match:
                specs["Storage"] = f"{storage_match.group(1)}GB Storage"
            
            # Try pattern: "8GB/128GB" or "128GB"
            if specs["Storage"] == "N/A":
                # Find all GB values
                all_gb = re.findall(r'(\d+)\s*GB', value, re.IGNORECASE)
                if len(all_gb) >= 2:
                    # Second one is likely storage
                    specs["Storage"] = f"{all_gb[1]}GB Storage"
                elif len(all_gb) == 1 and specs["RAM"] == "N/A":
                    # Only one GB value, might be storage
                    specs["Storage"] = f"{all_gb[0]}GB Storage"
            
            break
    
    # 5. BATTERY
    battery = details.get("battery", {})
    batt_type = battery.get("battType", "")
    if batt_type:
        mah_match = re.search(r'(\d+)\s*mAh', str(batt_type), re.IGNORECASE)
        specs["Battery"] = f"{mah_match.group(1)}mAh" if mah_match else "N/A"
    else:
        specs["Battery"] = "N/A"
    
    return specs

# ==========================================
# BACKGROUND REMOVAL
# ==========================================

def remove_white_background(img: Image.Image) -> Image.Image:
    """Remove white background from phone image"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    data = img.getdata()
    new_data = []
    
    for item in data:
        # Get RGB values
        r, g, b = item[:3]
        a = item[3] if len(item) == 4 else 255
        
        # Remove white and near-white pixels
        if r > 240 and g > 240 and b > 240:
            new_data.append((255, 255, 255, 0))  # Transparent
        else:
            new_data.append((r, g, b, a))
    
    img.putdata(new_data)
    return img

# ==========================================
# MODERN AD GENERATORS WITH ICONS
# ==========================================

class ModernAdGenerator:
    """Modern ad generator with icons and clean design"""
    
    def __init__(self, platform: str):
        self.platform = platform
        
        # Platform sizes
        self.sizes = {
            "facebook": (1200, 630),
            "whatsapp": (1080, 1080),
            "instagram": (1080, 1350)
        }
        
        self.width, self.height = self.sizes[platform]
        
        # Load fonts with BIGGER sizes
        try:
            self.title_font = ImageFont.truetype("arialbd.ttf", 52)
            self.subtitle_font = ImageFont.truetype("arialbd.ttf", 36)
            self.body_font = ImageFont.truetype("arial.ttf", 32)
            self.price_font = ImageFont.truetype("arialbd.ttf", 48)
            self.small_font = ImageFont.truetype("arial.ttf", 24)
        except:
            default = ImageFont.load_default()
            self.title_font = self.subtitle_font = self.body_font = default
            self.price_font = self.small_font = default
    
    def create_gradient_bg(self, color1: str, color2: str) -> Image.Image:
        """Create gradient background"""
        img = Image.new('RGB', (self.width, self.height), color1)
        draw = ImageDraw.Draw(img)
        
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        
        for y in range(self.height):
            factor = y / self.height
            r = int(r1 * (1 - factor) + r2 * factor)
            g = int(g1 * (1 - factor) + g2 * factor)
            b = int(b1 * (1 - factor) + b2 * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def generate_facebook(self, phone_name: str, specs: Dict, price: str, phone_img_url: str) -> Image.Image:
        """Generate Facebook ad (1200x630)"""
        # Gradient background
        img = self.create_gradient_bg(BRAND_MAROON, "#4a0000")
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Logo
        logo = download_image(LOGO_URL)
        if logo:
            logo.thumbnail((200, 70), Image.Resampling.LANCZOS)
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            img.paste(logo, (40, 40), logo)
        
        # Phone image (LEFT - 50% width)
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                phone_img = remove_white_background(phone_img)
                phone_img.thumbnail((550, 550), Image.Resampling.LANCZOS)
                
                x = 80
                y = (self.height - phone_img.height) // 2
                
                # Shadow
                shadow = Image.new('RGBA', (phone_img.width + 30, phone_img.height + 30), (0, 0, 0, 100))
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
                img.paste(shadow, (x - 15, y + 15), shadow)
                
                img.paste(phone_img, (x, y), phone_img)
        
        # Content area (RIGHT)
        content_x = 680
        content_y = 120
        
        # Phone name
        draw.text((content_x, content_y), phone_name[:25], fill="white", font=self.title_font)
        content_y += 80
        
        # Specs with icons
        icon_size = 50
        spec_mapping = [
            ("screen", "Screen"),
            ("camera", "Camera"),
            ("memory", "RAM"),
            ("storage", "Storage"),
            ("battery", "Battery")
        ]
        
        for icon_name, spec_name in spec_mapping:
            spec_value = specs.get(spec_name, "N/A")
            if spec_value != "N/A":
                # Icon
                icon = get_icon(icon_name, icon_size)
                if icon:
                    img.paste(icon, (content_x, content_y), icon)
                
                # Text
                draw.text((content_x + icon_size + 20, content_y + 10), 
                         spec_value, fill="white", font=self.body_font)
                content_y += 65
        
        content_y += 20
        
        # Price badge
        formatted_price = format_price(price)
        price_text = f"KES {formatted_price}"
        
        draw.rounded_rectangle(
            [content_x, content_y, content_x + 380, content_y + 80],
            radius=15,
            fill=BRAND_GOLD
        )
        draw.text((content_x + 20, content_y + 18), price_text, 
                 fill=BRAND_MAROON, font=self.price_font)
        
        # Footer
        footer_y = self.height - 50
        draw.text((self.width // 2, footer_y), f"📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}",
                 fill=BRAND_GOLD, font=self.small_font, anchor="mm")
        
        return img
    
    def generate_whatsapp(self, phone_name: str, specs: Dict, price: str, phone_img_url: str) -> Image.Image:
        """Generate WhatsApp ad (1080x1080)"""
        # White background
        img = Image.new('RGB', (self.width, self.height), "white")
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Header gradient
        for y in range(180):
            factor = y / 180
            r = int(139 * (1 - factor) + 255 * factor)
            draw.line([(0, y), (self.width, y)], fill=(r, 0, 0))
        
        # Logo
        logo = download_image(LOGO_URL)
        if logo:
            logo.thumbnail((200, 70), Image.Resampling.LANCZOS)
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            img.paste(logo, (50, 55), logo)
        
        draw.text((300, 60), "TRIPPLE K COMMUNICATIONS", fill="white", font=self.subtitle_font)
        draw.text((300, 110), "100% Genuine | Official Warranty", fill=BRAND_GOLD, font=self.small_font)
        
        # Phone image (CENTERED, BIG)
        content_y = 200
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                phone_img = remove_white_background(phone_img)
                phone_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
                
                x = (self.width - phone_img.width) // 2
                
                shadow = Image.new('RGBA', (phone_img.width + 20, phone_img.height + 20), (0, 0, 0, 60))
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
                img.paste(shadow, (x - 10, content_y + 15), shadow)
                
                img.paste(phone_img, (x, content_y), phone_img)
                content_y += phone_img.height + 40
        
        # Phone name (centered)
        name_bbox = draw.textbbox((0, 0), phone_name[:30], font=self.title_font)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text(((self.width - name_width) // 2, content_y), phone_name[:30],
                 fill=BRAND_MAROON, font=self.title_font)
        content_y += 70
        
        # Specs in 2 columns
        col1_x = self.width // 4
        col2_x = 3 * self.width // 4
        
        icon_size = 45
        spec_list = list(specs.items())
        
        # Column 1 (first 3 specs)
        spec_y = content_y
        for i in range(min(3, len(spec_list))):
            spec_name, spec_value = spec_list[i]
            if spec_value != "N/A":
                icon_name = ["screen", "camera", "memory"][i]
                icon = get_icon(icon_name, icon_size)
                if icon:
                    img.paste(icon, (col1_x - 50, spec_y), icon)
                
                draw.text((col1_x, spec_y + 8), spec_value, fill="#333", font=self.body_font, anchor="lm")
                spec_y += 60
        
        # Column 2 (last 2 specs)
        spec_y = content_y
        for i in range(3, min(5, len(spec_list))):
            spec_name, spec_value = spec_list[i]
            if spec_value != "N/A":
                icon_name = ["storage", "battery"][i - 3]
                icon = get_icon(icon_name, icon_size)
                if icon:
                    img.paste(icon, (col2_x - 50, spec_y), icon)
                
                draw.text((col2_x, spec_y + 8), spec_value, fill="#333", font=self.body_font, anchor="lm")
                spec_y += 60
        
        content_y += 200
        
        # Price badge (centered)
        formatted_price = format_price(price)
        price_text = f"KES {formatted_price}"
        
        price_width = 450
        price_x = (self.width - price_width) // 2
        
        draw.rounded_rectangle(
            [price_x, content_y, price_x + price_width, content_y + 90],
            radius=20,
            fill=BRAND_MAROON
        )
        
        price_bbox = draw.textbbox((0, 0), price_text, font=self.price_font)
        price_text_width = price_bbox[2] - price_bbox[0]
        draw.text((price_x + (price_width - price_text_width) // 2, content_y + 20),
                 price_text, fill=BRAND_GOLD, font=self.price_font)
        
        # Footer
        footer_y = self.height - 80
        draw.text((self.width // 2, footer_y), f"📞 {TRIPPLEK_PHONE}",
                 fill=BRAND_MAROON, font=self.body_font, anchor="mm")
        draw.text((self.width // 2, footer_y + 45), f"🌐 {TRIPPLEK_URL}",
                 fill=BRAND_MAROON, font=self.small_font, anchor="mm")
        
        return img
    
    def generate_instagram(self, phone_name: str, specs: Dict, price: str, phone_img_url: str) -> Image.Image:
        """Generate Instagram ad (1080x1350)"""
        # Gradient background
        img = self.create_gradient_bg("#0c2461", "#1e3799")
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Logo (centered top)
        logo = download_image(LOGO_URL)
        if logo:
            logo.thumbnail((200, 70), Image.Resampling.LANCZOS)
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            img.paste(logo, ((self.width - logo.width) // 2, 40), logo)
        
        # Phone image
        content_y = 140
        if phone_img_url:
            phone_img = download_image(phone_img_url)
            if phone_img:
                phone_img = remove_white_background(phone_img)
                phone_img.thumbnail((700, 700), Image.Resampling.LANCZOS)
                
                x = (self.width - phone_img.width) // 2
                
                shadow = Image.new('RGBA', (phone_img.width + 30, phone_img.height + 30), (0, 0, 0, 120))
                shadow = shadow.filter(ImageFilter.GaussianBlur(radius=25))
                img.paste(shadow, (x - 15, content_y + 20), shadow)
                
                img.paste(phone_img, (x, content_y), phone_img)
                content_y += phone_img.height + 50
        
        # Phone name
        name_bbox = draw.textbbox((0, 0), phone_name[:30], font=self.title_font)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text(((self.width - name_width) // 2, content_y), phone_name[:30],
                 fill="white", font=self.title_font)
        content_y += 80
        
        # Specs horizontally
        icon_size = 60
        spec_list = [(k, v) for k, v in specs.items() if v != "N/A"][:4]
        
        if spec_list:
            total_width = len(spec_list) * 200
            start_x = (self.width - total_width) // 2
            
            icon_names = ["screen", "camera", "memory", "battery"]
            
            for i, (spec_name, spec_value) in enumerate(spec_list):
                x = start_x + i * 200
                
                # Icon
                icon = get_icon(icon_names[i], icon_size)
                if icon:
                    img.paste(icon, (x + 70, content_y), icon)
                
                # Text below icon
                text_bbox = draw.textbbox((0, 0), spec_value, font=self.small_font)
                text_width = text_bbox[2] - text_bbox[0]
                draw.text((x + 70 + (icon_size - text_width) // 2, content_y + icon_size + 10),
                         spec_value, fill="white", font=self.small_font)
            
            content_y += icon_size + 80
        
        # Price
        formatted_price = format_price(price)
        price_text = f"KES {formatted_price}"
        
        price_width = 500
        price_x = (self.width - price_width) // 2
        
        draw.rounded_rectangle(
            [price_x, content_y, price_x + price_width, content_y + 90],
            radius=20,
            fill=BRAND_GOLD
        )
        
        price_bbox = draw.textbbox((0, 0), price_text, font=self.price_font)
        price_text_width = price_bbox[2] - price_bbox[0]
        draw.text((price_x + (price_width - price_text_width) // 2, content_y + 20),
                 price_text, fill=BRAND_MAROON, font=self.price_font)
        
        # Footer
        footer_y = self.height - 60
        draw.text((self.width // 2, footer_y), f"📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}",
                 fill=BRAND_GOLD, font=self.small_font, anchor="mm")
        
        return img

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def format_price(price_str: str) -> str:
    """Format price with commas"""
    if not price_str:
        return "99,999"
    
    clean = re.sub(r'[^\d]', '', price_str)
    
    try:
        if clean:
            num = int(clean)
            return f"{num:,}"
    except:
        pass
    
    return "99,999"

def create_video_html(images: List[Image.Image], duration: int = 6) -> str:
    """Create animated video HTML (6 seconds loop)"""
    # Convert images to base64
    img_data_list = []
    for img in images:
        buf = BytesIO()
        img.save(buf, format='PNG')
        img_data = base64.b64encode(buf.getvalue()).decode()
        img_data_list.append(img_data)
    
    # Time per frame
    frame_duration = duration / len(images)
    
    html = f"""
    <style>
        @keyframes slideshow {{
            {" ".join([f"{i * (100 / len(images)):.1f}% {{ opacity: 1; }}" for i in range(len(images))])}
            {" ".join([f"{(i + 0.8) * (100 / len(images)):.1f}% {{ opacity: 0; }}" for i in range(len(images))])}
        }}
        .slideshow-container {{
            position: relative;
            width: 100%;
            height: auto;
            background: #000;
        }}
        .slideshow-container img {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: auto;
            opacity: 0;
            animation: slideshow {duration}s infinite;
        }}
        {"".join([f".slideshow-container img:nth-child({i+1}) {{ animation-delay: {i * frame_duration}s; }}" for i in range(len(images))])}
    </style>
    <div class="slideshow-container">
        {"".join([f'<img src="data:image/png;base64,{img_data}" />' for img_data in img_data_list])}
    </div>
    """
    
    return html

# ==========================================
# STREAMLIT APP
# ==========================================

def main():
    st.title("📱 Professional Phone Ad Generator")
    st.markdown("**Create stunning ads with modern icons and clean design**")
    
    st.markdown("---")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Platform selection
        platform = st.selectbox(
            "📱 Select Platform:",
            ["Facebook (1200x630)", "WhatsApp (1080x1080)", "Instagram (1080x1350)"],
            index=0
        )
        
        platform_key = platform.split()[0].lower()
        
        st.markdown("---")
        st.markdown("### 🎨 Features")
        st.success("✅ Modern icons for specs")
        st.success("✅ Clean professional design")
        st.success("✅ Bigger, readable fonts")
        st.success("✅ Auto background removal")
        st.success("✅ Download image & video")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Step 1: Search Phone")
        
        phone_query = st.text_input(
            "Enter phone name:",
            placeholder="e.g., Poco X3 Pro, iPhone 14",
            label_visibility="collapsed"
        )
        
        search_btn = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_btn and phone_query:
            with st.spinner("Searching..."):
                results = search_phone(phone_query)
                
                if results:
                    st.session_state.search_results = results
                    st.session_state.selected_phone = None
                    st.success(f"✅ Found {len(results)} phones")
                else:
                    st.error("❌ No phones found")
        
        # Display results
        if 'search_results' in st.session_state and st.session_state.search_results:
            st.markdown("**Select a phone:**")
            
            for idx, phone in enumerate(st.session_state.search_results[:5]):
                phone_name = phone.get("name", "Unknown")
                
                if st.button(f"📱 {phone_name}", key=f"phone_{idx}", use_container_width=True):
                    with st.spinner("Loading details..."):
                        phone_id = phone.get("id", "")
                        details = get_phone_details(phone_id)
                        
                        if details:
                            specs = extract_top_5_specs(details)
                            image_url = get_phone_image(phone_id) or phone.get("image", "")
                            
                            st.session_state.selected_phone = {
                                "name": phone_name,
                                "specs": specs,
                                "image_url": image_url
                            }
                            
                            st.success(f"✅ Loaded: {phone_name}")
                            st.rerun()
    
    with col2:
        st.subheader("Step 2: Set Price & Generate")
        
        if 'selected_phone' in st.session_state and st.session_state.selecte