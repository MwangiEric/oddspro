import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from typing import Optional, Tuple, Dict, List
import re

# ==========================================
# CONFIGURATION
# ==========================================
BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
BRAND_ACCENT = "#FF6B35"

TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"

API_BASE = "https://tkphsp2.vercel.app"

st.set_page_config(page_title="Phone Ad Generator", layout="centered", page_icon="📱")

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
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            return img
    except:
        pass
    return None

# ==========================================
# PARSE SPECS - EXTRACT TOP 5
# ==========================================

def extract_top_5_specs(details: Dict) -> Dict[str, str]:
    """Extract exactly 5 key specs"""
    specs = {}
    
    # 1. SCREEN
    display = details.get("display", {})
    screen_size = display.get("size", "")
    if screen_size:
        match = re.search(r'(\d+\.?\d*)\s*inches', str(screen_size), re.IGNORECASE)
        specs["Screen"] = f"{match.group(1)} inches" if match else "N/A"
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
    
    # 3. RAM
    memory = details.get("memory", [])
    specs["RAM"] = "N/A"
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            value = str(mem.get("value", ""))
            ram_match = re.search(r'(\d+)\s*GB\s+RAM', value, re.IGNORECASE)
            if ram_match:
                specs["RAM"] = f"{ram_match.group(1)}GB"
                break
    
    # 4. STORAGE
    specs["Storage"] = "N/A"
    for mem in memory:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            value = str(mem.get("value", ""))
            storage_match = re.search(r'(\d+)\s*GB\s+(?:ROM|storage)', value, re.IGNORECASE)
            if storage_match:
                specs["Storage"] = f"{storage_match.group(1)}GB"
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
# SIMPLE AD GENERATOR
# ==========================================

def create_phone_ad(phone_name: str, specs: Dict[str, str], 
                   price: str, phone_img_url: str) -> Image.Image:
    """Create a simple phone ad - 1200x630 Facebook format"""
    
    width, height = 1200, 630
    
    # Create gradient background
    img = Image.new('RGB', (width, height), BRAND_MAROON)
    draw = ImageDraw.Draw(img)
    
    # Gradient
    for y in range(height):
        factor = y / height
        r = int(139 * (1 - factor * 0.5))
        draw.line([(0, y), (width, y)], fill=(r, 0, 0))
    
    # Load fonts
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 42)
        subtitle_font = ImageFont.truetype("arialbd.ttf", 28)
        body_font = ImageFont.truetype("arial.ttf", 24)
        price_font = ImageFont.truetype("arialbd.ttf", 38)
    except:
        default = ImageFont.load_default()
        title_font = subtitle_font = body_font = price_font = default
    
    # ===== LOGO (TOP LEFT) =====
    logo = download_image(LOGO_URL)
    if logo:
        logo.thumbnail((180, 60), Image.Resampling.LANCZOS)
        img.paste(logo, (40, 35), logo)
    
    # ===== PHONE IMAGE (LEFT SIDE - BIG) =====
    if phone_img_url:
        phone_img = download_image(phone_img_url)
        if phone_img:
            # Resize to 500x500 maintaining aspect ratio
            phone_img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            
            # Position
            img_x = 80
            img_y = (height - phone_img.height) // 2
            
            # Shadow
            shadow = Image.new('RGBA', (phone_img.width + 20, phone_img.height + 20), (0, 0, 0, 80))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
            img.paste(shadow, (img_x - 10, img_y + 10), shadow)
            
            # Paste phone
            img.paste(phone_img, (img_x, img_y), phone_img)
    
    # ===== CONTENT AREA (RIGHT SIDE) =====
    content_x = 650
    content_y = 120
    
    # Phone name
    lines = wrap_text(phone_name, title_font, 500)
    for line in lines[:2]:  # Max 2 lines
        draw.text((content_x, content_y), line, fill="white", font=title_font)
        content_y += 50
    
    content_y += 30
    
    # ===== 5 SPECS =====
    spec_icons = {
        "Screen": "🖥️",
        "Camera": "📸",
        "RAM": "⚡",
        "Storage": "💾",
        "Battery": "🔋"
    }
    
    for spec_name, spec_value in specs.items():
        if spec_value != "N/A":
            icon = spec_icons.get(spec_name, "•")
            text = f"{icon} {spec_name}: {spec_value}"
            draw.text((content_x, content_y), text, fill="white", font=body_font)
            content_y += 45
    
    content_y += 20
    
    # ===== PRICE =====
    formatted_price = format_price(price)
    price_text = f"KES {formatted_price}"
    
    # Price background
    price_bbox = draw.textbbox((0, 0), price_text, font=price_font)
    price_width = price_bbox[2] - price_bbox[0] + 40
    price_height = 70
    
    draw.rounded_rectangle(
        [content_x, content_y, content_x + price_width, content_y + price_height],
        radius=15,
        fill=BRAND_GOLD
    )
    
    # Price text
    draw.text(
        (content_x + 20, content_y + 15),
        price_text,
        fill=BRAND_MAROON,
        font=price_font
    )
    
    content_y += price_height + 25
    
    # ===== CTA BUTTON =====
    cta_text = "SHOP NOW"
    cta_width = 220
    cta_height = 60
    
    draw.rounded_rectangle(
        [content_x, content_y, content_x + cta_width, content_y + cta_height],
        radius=12,
        fill=BRAND_ACCENT,
        outline=BRAND_GOLD,
        width=3
    )
    
    cta_bbox = draw.textbbox((0, 0), cta_text, font=subtitle_font)
    cta_text_width = cta_bbox[2] - cta_bbox[0]
    cta_x = content_x + (cta_width - cta_text_width) // 2
    
    draw.text((cta_x, content_y + 15), cta_text, fill="white", font=subtitle_font)
    
    # ===== FOOTER =====
    footer_y = height - 60
    contact_text = f"📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}"
    
    try:
        footer_font = ImageFont.truetype("arial.ttf", 18)
    except:
        footer_font = ImageFont.load_default()
    
    footer_bbox = draw.textbbox((0, 0), contact_text, font=footer_font)
    footer_width = footer_bbox[2] - footer_bbox[0]
    footer_x = (width - footer_width) // 2
    
    draw.text((footer_x, footer_y), contact_text, fill=BRAND_GOLD, font=footer_font)
    
    return img

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Wrap text to fit width"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        try:
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
        except:
            width = len(test_line) * 10
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines if lines else [text]

def format_price(price_str: str) -> str:
    """Format price with commas"""
    if not price_str:
        return "99,999"
    
    # Remove non-digits
    clean = re.sub(r'[^\d]', '', price_str)
    
    try:
        if clean:
            num = int(clean)
            return f"{num:,}"
    except:
        pass
    
    return "99,999"

# ==========================================
# STREAMLIT APP
# ==========================================

def main():
    st.title("📱 Phone Ad Generator")
    st.markdown("**Simple workflow:** Phone Name + Price → Professional Ad")
    
    st.markdown("---")
    
    # ===== STEP 1: SEARCH PHONE =====
    st.subheader("Step 1: Search Phone")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        phone_query = st.text_input(
            "Enter phone name:",
            placeholder="e.g., Poco X3 Pro, iPhone 14, Samsung S23",
            label_visibility="collapsed"
        )
    
    with col2:
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
    
    # ===== DISPLAY SEARCH RESULTS =====
    if 'search_results' in st.session_state and st.session_state.search_results:
        st.markdown("### Select a Phone")
        
        for idx, phone in enumerate(st.session_state.search_results[:5]):
            phone_name = phone.get("name", "Unknown")
            
            if st.button(f"📱 {phone_name}", key=f"phone_{idx}", use_container_width=True):
                with st.spinner("Loading phone details..."):
                    # Get details
                    phone_id = phone.get("id", "")
                    details = get_phone_details(phone_id)
                    
                    if details:
                        # Extract specs
                        specs = extract_top_5_specs(details)
                        
                        # Get image
                        image_url = get_phone_image(phone_id)
                        if not image_url:
                            image_url = phone.get("image", "")
                        
                        # Save to session
                        st.session_state.selected_phone = {
                            "name": phone_name,
                            "specs": specs,
                            "image_url": image_url
                        }
                        
                        st.success(f"✅ Loaded: {phone_name}")
                        st.rerun()
    
    # ===== STEP 2: SET PRICE & GENERATE =====
    if 'selected_phone' in st.session_state and st.session_state.selected_phone:
        st.markdown("---")
        st.subheader("Step 2: Set Price & Generate Ad")
        
        phone = st.session_state.selected_phone
        
        # Display selected phone info
        st.success(f"**Selected:** {phone['name']}")
        
        # Show specs
        with st.expander("📋 View Specs", expanded=False):
            for spec_name, spec_value in phone['specs'].items():
                st.write(f"**{spec_name}:** {spec_value}")
        
        # Price input
        col_price, col_gen = st.columns([2, 1])
        
        with col_price:
            price = st.text_input(
                "Enter Price (KES):",
                placeholder="e.g., 45999 or 45,999",
                value=st.session_state.get('price', '45999')
            )
            st.session_state.price = price
        
        with col_gen:
            st.write("")  # Spacing
            st.write("")  # Spacing
            generate_btn = st.button("✨ Generate Ad", type="primary", use_container_width=True)
        
        # Show formatted price preview
        if price:
            formatted = format_price(price)
            st.info(f"💰 Price will display as: **KES {formatted}**")
        
        # ===== GENERATE AD =====
        if generate_btn:
            if not price:
                st.error("⚠️ Please enter a price")
            else:
                with st.spinner("Creating your ad..."):
                    try:
                        # Generate ad
                        ad_image = create_phone_ad(
                            phone_name=phone['name'],
                            specs=phone['specs'],
                            price=price,
                            phone_img_url=phone['image_url']
                        )
                        
                        # Display
                        st.markdown("---")
                        st.subheader("✅ Your Ad is Ready!")
                        st.image(ad_image, use_container_width=True)
                        
                        # Download
                        buf = BytesIO()
                        ad_image.save(buf, format='PNG', quality=95)
                        
                        safe_name = re.sub(r'[^\w\s-]', '', phone['name']).strip().replace(' ', '_')
                        filename = f"tripplek_{safe_name}_ad.png"
                        
                        st.download_button(
                            label="📥 Download PNG",
                            data=buf.getvalue(),
                            file_name=filename,
                            mime="image/png",
                            use_container_width=True
                        )
                        
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    else:
        st.info("👆 Start by searching for a phone above")
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: {BRAND_MAROON};'>"
        f"<p><strong>Tripple K Communications</strong></p>"
        f"<p>📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}</p>"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()