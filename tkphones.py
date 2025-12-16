import streamlit as st
import requests
import re
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Optional, Dict, Any, List
import time
from datetime import datetime
from dateutil import parser
import pyperclip

# ==========================================
# CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Tripple K Marketing Suite",
    layout="wide",
    page_icon="📱"
)

# Brand colors & info
BRAND_MAROON = "#8B0000"
BRAND_GOLD = "#FFD700"
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"

# CSS Styling
st.markdown(f"""
<style>
    .main {{
        background: #f8f9fa;
    }}
    
    .spec-card {{
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 5px 20px rgba(139, 0, 0, 0.1);
        border-left: 5px solid {BRAND_MAROON};
    }}
    
    .image-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin-top: 20px;
    }}
    
    .image-card {{
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }}
    
    .image-card:hover {{
        transform: translateY(-5px);
    }}
    
    .post-card {{
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        line-height: 1.6;
    }}
    
    .platform-header {{
        color: {BRAND_MAROON};
        font-weight: bold;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 2px solid {BRAND_GOLD};
    }}
    
    .highlight {{
        background-color: #fff9e6;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 3px solid {BRAND_GOLD};
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# API FUNCTIONS
# ==========================================

@st.cache_data(ttl=3600)
def fetch_with_timeout(url: str) -> Optional[Dict]:
    """Fetch data with timeout"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
    return None

def search_phones(query: str) -> List[Dict]:
    """Search for phones"""
    url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(query)}"
    data = fetch_with_timeout(url)
    return data if data else []

def get_phone_details(phone_id: str) -> Dict:
    """Get phone info"""
    url = f"https://tkphsp2.vercel.app/gsm/info/{phone_id}"
    data = fetch_with_timeout(url)
    return data if data else {}

def get_phone_images(phone_id: str) -> List[str]:
    """Get phone images"""
    url = f"https://tkphsp2.vercel.app/gsm/images/{phone_id}"
    data = fetch_with_timeout(url)
    return data.get('images', []) if data else []

def download_image(url: str) -> Optional[Image.Image]:
    """Download image"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Convert to RGB to avoid transparency issues
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                return background
            return img.convert('RGB')
    except Exception as e:
        st.error(f"Image Error: {str(e)}")
    return None

# ==========================================
# SPEC PARSER
# ==========================================

def extract_screen_info(display_data: Dict) -> str:
    """Extract screen size and resolution"""
    size = display_data.get("size", "")
    resolution = display_data.get("resolution", "")
    
    # Extract inches
    inch_match = re.search(r'(\d+\.?\d*)\s*["]?inches', str(size), re.IGNORECASE)
    inches = inch_match.group(1) if inch_match else ""
    
    # Extract resolution
    res_match = re.search(r'(\d+)\s*x\s*(\d+)', str(resolution))
    pixels = f"{res_match.group(1)} x {res_match.group(2)}" if res_match else ""
    
    if inches and pixels:
        return f"{inches} inch ({pixels})"
    elif inches:
        return f"{inches} inch"
    elif pixels:
        return f"{pixels}"
    return "N/A"

def extract_memory_info(memory_data: List) -> tuple:
    """Extract RAM and storage"""
    ram = "N/A"
    storage = "N/A"
    
    for mem in memory_data:
        if isinstance(mem, dict) and mem.get("label") == "internal":
            val = str(mem.get("value", "")).upper()
            
            # Try to find RAM
            ram_patterns = [
                r'(\d+)\s*GB\s+RAM',
                r'RAM\s*:\s*(\d+)\s*GB',
                r'^(\d+)\s*GB\s*/\s*\d+',
            ]
            
            for pattern in ram_patterns:
                match = re.search(pattern, val)
                if match:
                    ram = f"{match.group(1)}GB"
                    break
            
            # Try to find storage
            storage_patterns = [
                r'(\d+)\s*GB\s+(?:ROM|STORAGE|Internal)',
                r'/\s*(\d+)\s*GB',
                r'ROM\s*:\s*(\d+)\s*GB',
            ]
            
            for pattern in storage_patterns:
                match = re.search(pattern, val)
                if match:
                    storage = f"{match.group(1)}GB"
                    break
    
    return ram, storage

def parse_phone_specs(raw_data: dict) -> Dict[str, Any]:
    """Parse phone specs from API response"""
    specs = {
        "name": raw_data.get("name", "Unknown Phone"),
        "id": raw_data.get("id", ""),
        "image": raw_data.get("image", ""),
    }
    
    # Screen
    display = raw_data.get("display", {})
    specs["screen"] = extract_screen_info(display)
    
    # Memory
    memory = raw_data.get("memory", [])
    specs["ram"], specs["storage"] = extract_memory_info(memory)
    
    # Camera
    camera = raw_data.get("mainCamera", {})
    camera_modules = camera.get("mainModules", "N/A")
    if isinstance(camera_modules, str) and "MP" in camera_modules.upper():
        mp_values = re.findall(r'(\d+\.?\d*)\s*MP', camera_modules.upper())
        if mp_values:
            specs["camera"] = f"{mp_values[0]}MP" + (f" + {mp_values[1]}MP" if len(mp_values) > 1 else "")
        else:
            specs["camera"] = "N/A"
    else:
        specs["camera"] = "N/A"
    
    # Other specs
    specs["battery"] = raw_data.get("battery", {}).get("battType", "N/A")
    specs["chipset"] = raw_data.get("platform", {}).get("chipset", "N/A")
    specs["os"] = raw_data.get("platform", {}).get("os", "N/A")
    
    # Launch info
    launch = raw_data.get("launced", {})
    specs["launch_date"] = launch.get("announced", launch.get("status", "N/A"))
    
    return specs

# ==========================================
# MARKETING CONTENT GENERATOR
# ==========================================

def generate_marketing_posts(phone_specs: Dict) -> Dict[str, str]:
    """Generate professional marketing posts"""
    name = phone_specs["name"]
    
    # Choose most appealing specs
    appealing_specs = []
    if phone_specs.get("camera") != "N/A":
        appealing_specs.append(f"{phone_specs['camera']} camera system")
    if phone_specs.get("screen") != "N/A":
        appealing_specs.append(f"{phone_specs['screen']} display")
    if phone_specs.get("ram") != "N/A":
        appealing_specs.append(f"{phone_specs['ram']} RAM")
    if phone_specs.get("battery") != "N/A":
        appealing_specs.append(f"Long-lasting {phone_specs['battery']} battery")
    
    # Create marketing messages
    posts = {
        "facebook": f"""New Arrival at Tripple K Communications!

{name} is now available!

This powerhouse features:
- {appealing_specs[0] if len(appealing_specs) > 0 else 'Premium specifications'}
- {appealing_specs[1] if len(appealing_specs) > 1 else 'Advanced features'}
- Perfect for work and entertainment

Why buy from Tripple K?
• 100% genuine with official warranty
• Free delivery in Nairobi
• Professional setup and support
• Flexible payment options

Get yours today and experience premium mobile technology.

Call/WhatsApp: {TRIPPLEK_PHONE}
Visit: {TRIPPLEK_URL}

#TrippleKCommunications #KenyaTech #MobilePhones #PhoneDeals #GenuinePhones #NairobiBusiness""",
        
        "instagram": f"""Just arrived at Tripple K!

{name}

Featuring:
✓ {appealing_specs[0] if len(appealing_specs) > 0 else 'Premium performance'}
✓ {appealing_specs[1] if len(appealing_specs) > 1 else 'Advanced technology'}

Experience premium quality and reliability with Tripple K Communications.

Tap the link in bio for details
DM for special pricing

Tripple K Communications
Your trusted phone partner in Kenya

{TRIPPLEK_PHONE}

#TrippleK #PhoneKenya #TechNairobi #MobileKenya #Gadgets""",
        
        "whatsapp": f"""*NEW PHONE ALERT*

{name} now available at Tripple K Communications!

Key Features:
• {appealing_specs[0] if len(appealing_specs) > 0 else 'High-performance specs'}
• {appealing_specs[1] if len(appealing_specs) > 1 else 'Advanced features'}
• {appealing_specs[2] if len(appealing_specs) > 2 else 'Premium build quality'}

Tripple K Guarantee:
✓ 100% Genuine Products
✓ Official Warranty Included
✓ Free Nairobi Delivery
✓ Professional Setup

Price includes:
- Original accessories
- Screen protector application
- 1-year warranty

*Contact us now:*
Phone/WhatsApp: {TRIPPLEK_PHONE}
Website: {TRIPPLEK_URL}

Limited stock available. Call now to reserve yours!

*Tripple K Communications - Your Trusted Phone Partner*""",
        
        "twitter": f"""New phone alert! {name} now available at Tripple K Communications.

Featuring {appealing_specs[0] if len(appealing_specs) > 0 else 'premium specifications'}.

Get yours today with:
• Official warranty
• Free delivery
• Professional setup

{TRIPPLEK_PHONE} | {TRIPPLEK_URL}

#TrippleK #PhoneDeals #KenyaTech #MobilePhones"""
    }
    
    return posts

# ==========================================
# SIMPLE AD GENERATOR (FIXED TRANSPARENCY)
# ==========================================

def create_whatsapp_ad(phone_specs: Dict, phone_image_url: str) -> Image.Image:
    """Create simple WhatsApp ad without transparency issues"""
    width, height = 1080, 1350
    
    # Create white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("poppins.ttf", 48)
        header_font = ImageFont.truetype("poppins.ttf", 36)
        body_font = ImageFont.truetype("poppins.ttf", 28)
        cta_font = ImageFont.truetype("poppins.ttf", 32)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        cta_font = ImageFont.load_default()
    
    # Header with brand color
    draw.rectangle([0, 0, width, 120], fill=BRAND_MAROON)
    draw.text((width//2, 60), "TRIPPLE K COMMUNICATIONS", 
              fill="white", font=title_font, anchor="mm")
    
    # Phone name
    draw.text((width//2, 180), phone_specs["name"], 
              fill=BRAND_MAROON, font=header_font, anchor="mm")
    
    # Phone image
    y_offset = 230
    if phone_image_url:
        phone_img = download_image(phone_image_url)
        if phone_img:
            # Resize to fit
            phone_img.thumbnail((600, 600))
            x_pos = (width - phone_img.width) // 2
            img.paste(phone_img, (x_pos, y_offset))
            y_offset += phone_img.height + 30
    
    # Key specs box
    specs_box_top = y_offset
    specs_box_height = 200
    
    # Draw specs box
    draw.rectangle([50, specs_box_top, width-50, specs_box_top + specs_box_height], 
                   fill="#f8f9fa", outline=BRAND_GOLD, width=3)
    
    # Add specs text
    specs = [
        ("SCREEN:", phone_specs.get("screen", "N/A")),
        ("CAMERA:", phone_specs.get("camera", "N/A")),
        ("STORAGE:", phone_specs.get("storage", "N/A")),
        ("BATTERY:", phone_specs.get("battery", "N/A")),
    ]
    
    col1_x = 80
    col2_x = width // 2 + 30
    
    for i, (label, value) in enumerate(specs):
        if i < 2:
            x = col1_x
            y = specs_box_top + 40 + (i * 50)
        else:
            x = col2_x
            y = specs_box_top + 40 + ((i-2) * 50)
        
        draw.text((x, y), label, fill=BRAND_MAROON, font=body_font)
        draw.text((x + 150, y), value, fill="#333", font=body_font)
    
    y_offset = specs_box_top + specs_box_height + 40
    
    # Value proposition
    draw.text((width//2, y_offset), "WHY CHOOSE TRIPPLE K?", 
              fill=BRAND_MAROON, font=header_font, anchor="mm")
    y_offset += 50
    
    benefits = [
        "✓ 100% Genuine with Warranty",
        "✓ Free Delivery in Nairobi",
        "✓ Professional Setup",
        "✓ Flexible Payment Options"
    ]
    
    for benefit in benefits:
        draw.text((width//2, y_offset), benefit, 
                  fill="#333", font=body_font, anchor="mm")
        y_offset += 40
    
    # CTA Button
    cta_y = height - 180
    draw.rounded_rectangle([width//2 - 200, cta_y, width//2 + 200, cta_y + 70], 
                          radius=15, fill=BRAND_MAROON)
    draw.text((width//2, cta_y + 35), "ORDER NOW", 
              fill="white", font=cta_font, anchor="mm")
    
    # Contact info
    draw.text((width//2, height - 80), f"Call/WhatsApp: {TRIPPLEK_PHONE}", 
              fill="#666", font=body_font, anchor="mm")
    draw.text((width//2, height - 40), TRIPPLEK_URL, 
              fill=BRAND_MAROON, font=body_font, anchor="mm")
    
    return img

# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    # Header
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: {BRAND_MAROON}; margin-bottom: 0.5rem;">📱 Tripple K Marketing Suite</h1>
        <p style="color: #666;">Professional Phone Marketing Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'phone_specs' not in st.session_state:
        st.session_state.phone_specs = None
    if 'phone_images' not in st.session_state:
        st.session_state.phone_images = []
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Find Phone", "📱 Create Posts", "🎨 Generate Ad"])
    
    # TAB 1: FIND PHONE
    with tab1:
        st.markdown("### Search Phone Database")
        
        # Search
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("Enter phone model:", 
                                        placeholder="e.g., Samsung Galaxy S23, iPhone 15")
        with col2:
            search_btn = st.button("Search", type="primary", use_container_width=True)
        
        if search_btn and search_query:
            with st.spinner("Searching..."):
                results = search_phones(search_query)
                
                if results:
                    st.success(f"Found {len(results)} phone(s)")
                    
                    # Phone selection
                    phone_names = [r.get('name', 'Unknown') for r in results]
                    selected_name = st.selectbox("Select phone:", phone_names)
                    
                    if selected_name:
                        selected_phone = next(r for r in results if r['name'] == selected_name)
                        
                        with st.spinner("Getting details..."):
                            # Get phone details
                            details = get_phone_details(selected_phone['id'])
                            
                            if details:
                                # Parse specs
                                specs = parse_phone_specs(details)
                                
                                # Get phone images
                                images = get_phone_images(selected_phone['id'])
                                
                                # Store in session state
                                st.session_state.phone_specs = specs
                                st.session_state.phone_images = images
                                
                                # Display phone info
                                st.markdown(f"### {specs['name']}")
                                
                                # Create two columns for specs
                                col_spec1, col_spec2 = st.columns(2)
                                
                                with col_spec1:
                                    st.markdown('<div class="spec-card">', unsafe_allow_html=True)
                                    st.markdown("**Display:** " + specs.get('screen', 'N/A'))
                                    st.markdown("**Camera:** " + specs.get('camera', 'N/A'))
                                    st.markdown("**RAM:** " + specs.get('ram', 'N/A'))
                                    st.markdown("**Storage:** " + specs.get('storage', 'N/A'))
                                    st.markdown('</div>', unsafe_allow_html=True)
                                
                                with col_spec2:
                                    st.markdown('<div class="spec-card">', unsafe_allow_html=True)
                                    st.markdown("**Battery:** " + specs.get('battery', 'N/A'))
                                    st.markdown("**Chipset:** " + specs.get('chipset', 'N/A'))
                                    st.markdown("**OS:** " + specs.get('os', 'N/A'))
                                    st.markdown("**Launch:** " + specs.get('launch_date', 'N/A'))
                                    st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Show phone images after specs
                                if images:
                                    st.markdown("### 📸 Phone Images")
                                    st.markdown("First 3 images from the gallery:")
                                    
                                    # Create columns for images
                                    cols = st.columns(3)
                                    for idx, img_url in enumerate(images[:3]):
                                        with cols[idx]:
                                            try:
                                                img = download_image(img_url)
                                                if img:
                                                    st.image(img, use_column_width=True, 
                                                            caption=f"Image {idx+1}")
                                            except Exception as e:
                                                st.error(f"Could not load image {idx+1}")
                else:
                    st.error("No phones found. Try a different search term.")
    
    # TAB 2: CREATE POSTS
    with tab2:
        st.markdown("### Generate Marketing Posts")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone")
        else:
            phone_specs = st.session_state.phone_specs
            
            # Generate posts button
            if st.button("Generate Marketing Content", type="primary"):
                with st.spinner("Creating content..."):
                    posts = generate_marketing_posts(phone_specs)
                    
                    # Display posts
                    st.markdown("#### Facebook Post")
                    st.markdown('<div class="post-card">', unsafe_allow_html=True)
                    st.markdown('<div class="platform-header">Facebook</div>', unsafe_allow_html=True)
                    st.write(posts["facebook"])
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("Copy Facebook Post", key="copy_fb"):
                        try:
                            pyperclip.copy(posts["facebook"])
                            st.success("Copied to clipboard!")
                        except:
                            st.info("Text ready for copying")
                    
                    st.markdown("#### Instagram Post")
                    st.markdown('<div class="post-card">', unsafe_allow_html=True)
                    st.markdown('<div class="platform-header">Instagram</div>', unsafe_allow_html=True)
                    st.write(posts["instagram"])
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("Copy Instagram Post", key="copy_ig"):
                        try:
                            pyperclip.copy(posts["instagram"])
                            st.success("Copied to clipboard!")
                        except:
                            st.info("Text ready for copying")
                    
                    st.markdown("#### WhatsApp Message")
                    st.markdown('<div class="post-card">', unsafe_allow_html=True)
                    st.markdown('<div class="platform-header">WhatsApp</div>', unsafe_allow_html=True)
                    st.write(posts["whatsapp"])
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("Copy WhatsApp Message", key="copy_wa"):
                        try:
                            pyperclip.copy(posts["whatsapp"])
                            st.success("Copied to clipboard!")
                        except:
                            st.info("Text ready for copying")
    
    # TAB 3: GENERATE AD
    with tab3:
        st.markdown("### Create WhatsApp Ad")
        
        if not st.session_state.phone_specs:
            st.info("👈 First search and select a phone")
        elif not st.session_state.phone_images:
            st.info("No images available for this phone")
        else:
            phone_specs = st.session_state.phone_specs
            phone_images = st.session_state.phone_images
            
            # Ad preview
            if st.button("Generate WhatsApp Ad", type="primary"):
                with st.spinner("Creating ad..."):
                    # Use first image
                    main_image_url = phone_images[0]
                    ad_image = create_whatsapp_ad(phone_specs, main_image_url)
                    
                    # Display ad
                    st.image(ad_image, use_column_width=True, 
                            caption="WhatsApp Marketing Ad (1080x1350)")
                    
                    # Download button
                    buf = BytesIO()
                    ad_image.save(buf, format="PNG", quality=95)
                    img_bytes = buf.getvalue()
                    
                    st.download_button(
                        label="📥 Download Ad",
                        data=img_bytes,
                        file_name=f"tripplek_{phone_specs['name'].replace(' ', '_')}_ad.png",
                        mime="image/png",
                        use_container_width=True
                    )
                    
                    # Ad tips
                    with st.expander("📝 How to use this ad"):
                        st.markdown("""
                        **Best Practices:**
                        1. **Share on WhatsApp Status** - Upload as status image
                        2. **Send to Groups** - Share with relevant WhatsApp groups
                        3. **Broadcast Lists** - Send to your customer lists
                        4. **Business Profile** - Add to your WhatsApp business profile
                        
                        **When to post:**
                        - Weekdays: 11 AM - 2 PM
                        - Weekends: 10 AM - 4 PM
                        - Avoid late evenings
                        
                        **Call to Action:**
                        - Include your contact number
                        - Mention delivery areas
                        - State warranty terms
                        """)

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {BRAND_MAROON}; padding: 2rem 0;">
        <h4>Tripple K Communications</h4>
        <p>📞 {TRIPPLEK_PHONE} | 🌐 {TRIPPLEK_URL}</p>
        <p style="color: #666; font-size: 0.9rem;">Professional Phone Marketing Platform</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()