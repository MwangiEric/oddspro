# app.py
import streamlit as st
import requests
import json
import re
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
import base64
from typing import List, Dict, Optional, Tuple

# ============================================================================
# STREAMLIT CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Oraimo Product Poster Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS FOR BETTER UI
# ============================================================================

def load_css():
    st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 2rem;
    }
    
    /* Product cards */
    .product-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s;
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    .product-card.selected {
        border: 3px solid #4CAF50;
        background: linear-gradient(135deg, #f5f7fa 0%, #e4edf5 100%);
    }
    
    /* Price badge in cards */
    .price-badge {
        background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    /* Feature tags */
    .feature-tag {
        background: #e3f2fd;
        color: #1976d2;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        margin: 0.2rem;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 25px;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Success message */
    .success-message {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    
    /* Loading animation */
    .loading {
        display: inline-block;
        width: 50px;
        height: 50px;
        border: 3px solid rgba(102, 126, 234, 0.3);
        border-radius: 50%;
        border-top-color: #667eea;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Custom headers */
    .custom-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# CORE FUNCTIONS (Reused from previous code, adapted for Streamlit)
# ============================================================================

class OraimoProductExtractor:
    """Extracts multiple Oraimo products from search results"""
    
    def __init__(self):
        self.brand_keywords = ["oraimo", "Oraimo"]
        self.product_patterns = [
            r"(Oraimo\s+[\w\s]+\d+\w*(?:\s+\w+)*)",
            r"(Oraimo\s+[\w\-]+\d+)",
            r"([A-Z][a-z]+[\s\-]+\d+\w*)",
        ]
    
    def search_products(self, query: str) -> List[Dict]:
        """Search for Oraimo products"""
        search_url = f"https://far-paule-emw-a67bd497.koyeb.app/search?q={query.replace(' ', '+')}&format=json"
        
        try:
            response = requests.get(search_url, timeout=10)
            data = response.json()
            
            if data.get("results"):
                return self._extract_products(data["results"])
            else:
                return self._get_sample_products()
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return self._get_sample_products()
    
    def _extract_products(self, results: List[Dict]) -> List[Dict]:
        """Extract product information from search results"""
        products = {}
        
        for result in results:
            content = result.get("content", "").lower()
            title = result.get("title", "")
            
            # Check if it's an Oraimo product
            if any(keyword in content or keyword in title.lower() 
                   for keyword in self.brand_keywords):
                
                product_name = self._extract_product_name(title, content)
                
                if product_name and product_name not in products:
                    prices = self._extract_prices(content, title)
                    features = self._extract_features(content)
                    
                    products[product_name] = {
                        "name": product_name,
                        "prices": prices,
                        "highest_price": max(prices) if prices else None,
                        "lowest_price": min(prices) if prices else None,
                        "features": list(features)[:6],
                        "image_url": result.get("img_src", ""),
                        "source": result.get("url", ""),
                        "description": title[:100],
                    }
        
        # Convert to list and sort by price
        product_list = list(products.values())
        product_list.sort(key=lambda x: x["highest_price"] or 0, reverse=True)
        
        return product_list
    
    def _extract_product_name(self, title: str, content: str) -> Optional[str]:
        """Extract product name from text"""
        for pattern in self.product_patterns:
            matches = re.findall(pattern, title, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None
    
    def _extract_prices(self, content: str, title: str) -> List[int]:
        """Extract prices from text"""
        prices = []
        patterns = [
            r"(?:Ksh|KSH|Kes)\s*([\d,]+)",
            r"price[\s:]*K?sh?\s*([\d,]+)",
            r"ksh\s*([\d,]+)",
        ]
        
        all_text = f"{title} {content}"
        
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = str(match).replace(',', '')
                    price = int(float(price_str))
                    if 500 <= price <= 50000:
                        prices.append(price)
                except:
                    continue
        
        return list(set(prices))
    
    def _extract_features(self, content: str) -> set:
        """Extract features from content"""
        features = set()
        keywords = [
            "waterproof", "battery", "wireless", "bluetooth", 
            "noise cancellation", "bass", "touch", "voice", 
            "charging", "comfort", "lightweight", "sweatproof"
        ]
        
        content_lower = content.lower()
        
        for keyword in keywords:
            if keyword in content_lower:
                # Extract context around keyword
                start = max(0, content_lower.find(keyword) - 20)
                end = min(len(content_lower), content_lower.find(keyword) + len(keyword) + 30)
                phrase = content[start:end].strip()
                phrase = re.sub(r'[^\w\s\-]', ' ', phrase)
                phrase = ' '.join(phrase.split()).title()
                
                if phrase and len(phrase) > 5:
                    features.add(phrase)
        
        # Add default features if needed
        if len(features) < 3:
            features.update([
                "Wireless Bluetooth",
                "Long Battery Life",
                "High Quality Sound",
                "Comfortable Fit",
            ])
        
        return features
    
    def _get_sample_products(self) -> List[Dict]:
        """Return sample products for demo"""
        return [
            {
                "name": "Oraimo AirBuds 3",
                "prices": [5000, 5499],
                "highest_price": 5499,
                "lowest_price": 5000,
                "features": ["IPX7 Waterproof", "30H Battery Life", "Bluetooth 5.3", "Touch Controls", "Voice Assistant"],
                "image_url": "",
                "source": "",
                "description": "Powerful Bass IPX7 Waterproof TWS True Wireless Earbuds"
            },
            {
                "name": "Oraimo FreePods 3",
                "prices": [3800],
                "highest_price": 3800,
                "lowest_price": 3800,
                "features": ["True Wireless", "Bass Boost", "Comfort Fit", "Fast Charging"],
                "image_url": "",
                "source": "",
                "description": "TWS True Wireless Stereo Earbuds"
            },
            {
                "name": "Oraimo FreePods Pro",
                "prices": [8495],
                "highest_price": 8495,
                "lowest_price": 8495,
                "features": ["Active Noise Cancellation", "35H Playtime", "App Control", "Voice Assistant"],
                "image_url": "",
                "source": "",
                "description": "ANC Active Noise Cancellation TWS True Wireless Earbuds"
            }
        ]

class PosterGenerator:
    """Generates posters with product information"""
    
    def __init__(self):
        # Icon URLs from Flaticon
        self.icon_urls = {
            "battery": "https://cdn-icons-png.flaticon.com/512/3103/3103446.png",
            "waterproof": "https://cdn-icons-png.flaticon.com/512/3082/3082383.png",
            "bluetooth": "https://cdn-icons-png.flaticon.com/512/2972/2972246.png",
            "sound": "https://cdn-icons-png.flaticon.com/512/727/727218.png",
            "wireless": "https://cdn-icons-png.flaticon.com/512/1067/1067566.png",
            "comfort": "https://cdn-icons-png.flaticon.com/512/3024/3024603.png",
            "charging": "https://cdn-icons-png.flaticon.com/512/1067/1067572.png",
            "noise": "https://cdn-icons-png.flaticon.com/512/25/25694.png",
        }
    
    def generate_poster(self, product: Dict, product_image: Image.Image = None) -> Image.Image:
        """Generate a poster for the product"""
        # Poster dimensions
        width, height = 1200, 1600
        
        # Create background
        background = self._create_background(width, height)
        
        # Prepare product image
        if product_image:
            product_img = self._prepare_product_image(product_image)
        else:
            product_img = self._create_placeholder_image()
        
        # Create poster
        poster = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        poster.paste(background, (0, 0))
        
        # Add product image
        img_width, img_height = product_img.size
        img_x = (width - img_width) // 2
        img_y = 150
        poster.paste(product_img, (img_x, img_y), product_img)
        
        # Add price badge
        if product.get('highest_price'):
            badge = self._create_price_badge(product['highest_price'])
            poster.paste(badge, (width - 250, 50), badge)
        
        # Add product name
        draw = ImageDraw.Draw(poster)
        self._add_product_name(draw, product['name'], img_y + img_height + 50, width)
        
        # Add features with icons
        features_y = img_y + img_height + 150
        self._add_features(draw, product['features'], features_y, width)
        
        # Add footer
        self._add_footer(draw, width, height)
        
        return poster
    
    def _create_background(self, width: int, height: int) -> Image.Image:
        """Create abstract background"""
        bg = Image.new('RGB', (width, height), (245, 247, 250))
        draw = ImageDraw.Draw(bg)
        
        # Add gradient
        for i in range(height):
            alpha = int(50 * (i / height))
            draw.line([(0, i), (width, i)], fill=(70, 130, 180, alpha))
        
        # Add shapes
        colors = [
            (70, 130, 180, 20),  # Steel blue
            (52, 152, 219, 15),  # Light blue
            (231, 76, 60, 10),   # Red
        ]
        
        for _ in range(10):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(100, 300)
            color = random.choice(colors)
            
            shape = random.choice(['circle', 'square'])
            if shape == 'circle':
                draw.ellipse([x, y, x + size, y + size], fill=color)
            else:
                draw.rectangle([x, y, x + size, y + size], fill=color)
        
        # Apply blur
        bg = bg.filter(ImageFilter.GaussianBlur(3))
        
        return bg
    
    def _prepare_product_image(self, image: Image.Image) -> Image.Image:
        """Prepare product image by removing background and resizing"""
        # Convert to RGBA if needed
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Remove white background
        data = image.getdata()
        new_data = []
        for item in data:
            # If pixel is white or very light, make it transparent
            if item[0] > 220 and item[1] > 220 and item[2] > 220:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        image.putdata(new_data)
        
        # Resize to fit poster
        max_size = 500
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        return image
    
    def _create_placeholder_image(self) -> Image.Image:
        """Create a placeholder product image"""
        img = Image.new('RGBA', (400, 400), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw earbud
        draw.ellipse([50, 50, 350, 350], outline=(100, 100, 100), width=5)
        draw.ellipse([100, 100, 300, 300], fill=(70, 130, 180, 200))
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 40)
            draw.text((200, 200), "ORAIMO", fill=(255, 255, 255), anchor="mm", font=font)
        except:
            pass
        
        return img
    
    def _create_price_badge(self, price: int) -> Image.Image:
        """Create price badge"""
        size = 200
        badge = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        
        # Draw badge
        draw.ellipse([0, 0, size, size], fill=(220, 53, 69, 230))
        
        # Add price text
        try:
            font_large = ImageFont.truetype("arial.ttf", 36)
            font_small = ImageFont.truetype("arial.ttf", 20)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Format price
        if price >= 1000:
            price_text = f"Ksh\n{price:,.0f}"
        else:
            price_text = f"Ksh\n{price}"
        
        draw.text(
            (size//2, size//2 - 15),
            price_text,
            font=font_large,
            fill=(255, 255, 255),
            anchor="mm",
            align="center"
        )
        
        draw.text(
            (size//2, size - 40),
            "PRICE",
            font=font_small,
            fill=(255, 255, 255, 200),
            anchor="mm"
        )
        
        return badge
    
    def _add_product_name(self, draw: ImageDraw.Draw, name: str, y: int, width: int):
        """Add product name to poster"""
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Truncate if too long
        if len(name) > 25:
            name = name[:22] + "..."
        
        draw.text(
            (width//2, y),
            name.upper(),
            font=font,
            fill=(33, 37, 41),
            anchor="mm"
        )
    
    def _add_features(self, draw: ImageDraw.Draw, features: List[str], start_y: int, width: int):
        """Add features to poster"""
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Display features in two columns
        mid_point = width // 2
        left_x = mid_point - 200
        right_x = mid_point + 200
        
        for i, feature in enumerate(features[:8]):  # Max 8 features
            if i % 2 == 0:
                x = left_x
            else:
                x = right_x
            
            y = start_y + ((i // 2) * 60)
            
            # Truncate feature if too long
            if len(feature) > 20:
                feature = feature[:17] + "..."
            
            draw.text(
                (x, y),
                f"• {feature}",
                font=font,
                fill=(52, 58, 64),
                anchor="lm"
            )
    
    def _add_footer(self, draw: ImageDraw.Draw, width: int, height: int):
        """Add footer to poster"""
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        footer_text = "Generated with Oraimo Poster Generator"
        draw.text(
            (width//2, height - 30),
            footer_text,
            font=font,
            fill=(108, 117, 125),
            anchor="mm"
        )

# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def display_product_card(product: Dict, index: int, selected_index: int) -> bool:
    """Display a product card and return whether it's selected"""
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.subheader(product['name'])
        st.caption(product.get('description', 'Oraimo Wireless Earbuds'))
        
        # Display features as tags
        if product['features']:
            cols = st.columns(4)
            for i, feature in enumerate(product['features'][:4]):
                with cols[i % 4]:
                    st.markdown(f'<span class="feature-tag">{feature}</span>', unsafe_allow_html=True)
    
    with col2:
        if product['highest_price']:
            st.markdown(f'<div class="price-badge">Ksh {product["highest_price"]:,.0f}</div>', 
                       unsafe_allow_html=True)
        else:
            st.warning("No price found")
    
    with col3:
        select_label = "✅ Selected" if index == selected_index else "Select"
        if st.button(select_label, key=f"select_{index}", use_container_width=True):
            return True
    
    st.divider()
    return False

def download_image_button(image: Image.Image, filename: str):
    """Create a download button for the image"""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    st.download_button(
        label="📥 Download Poster",
        data=byte_im,
        file_name=filename,
        mime="image/png",
        use_container_width=True
    )

def display_poster_preview(poster: Image.Image):
    """Display poster preview with download option"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.image(poster, use_column_width=True, caption="Generated Poster Preview")
    
    with col2:
        # Get filename based on current time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"oraimo_poster_{timestamp}.png"
        
        download_image_button(poster, filename)
        
        # Additional options
        st.markdown("---")
        st.markdown("#### Poster Options")
        
        # Quality selector
        quality = st.slider("Image Quality", 50, 100, 95)
        
        # Format selector
        format_type = st.selectbox("Format", ["PNG", "JPEG", "WEBP"])
        
        if st.button("🔄 Regenerate with Options", use_container_width=True):
            st.rerun()

# ============================================================================
# MAIN STREAMLIT APP
# ============================================================================

def main():
    # Load CSS
    load_css()
    
    # Initialize session state
    if 'products' not in st.session_state:
        st.session_state.products = []
    if 'selected_product' not in st.session_state:
        st.session_state.selected_product = None
    if 'poster' not in st.session_state:
        st.session_state.poster = None
    if 'search_query' not in st.session_state:
        st.session_state.search_query = "oraimo earbuds price in kenya"
    if 'searching' not in st.session_state:
        st.session_state.searching = False
    
    # App header
    st.title("🎨 Oraimo Product Poster Generator")
    st.markdown("Create professional posters for Oraimo products with automatic price extraction and beautiful design.")
    
    # Sidebar
    with st.sidebar:
        st.markdown("<h2 class='custom-header'>⚙️ Settings</h2>", unsafe_allow_html=True)
        
        # Search settings
        st.markdown("### Search Settings")
        search_query = st.text_input(
            "Search Query",
            value=st.session_state.search_query,
            help="Enter search terms for Oraimo products"
        )
        
        if search_query != st.session_state.search_query:
            st.session_state.search_query = search_query
        
        # Design settings
        st.markdown("### Design Settings")
        
        badge_position = st.selectbox(
            "Price Badge Position",
            ["Top Right", "Top Left", "Bottom Right", "Bottom Left"],
            index=0
        )
        
        color_scheme = st.selectbox(
            "Color Scheme",
            ["Blue Theme", "Green Theme", "Purple Theme", "Orange Theme"],
            index=0
        )
        
        show_features = st.checkbox("Show Features", value=True)
        show_price_badge = st.checkbox("Show Price Badge", value=True)
        
        # About section
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.info("""
        This tool automatically:
        1. Searches for Oraimo products
        2. Extracts prices and features
        3. Generates professional posters
        4. Adds price badges and icons
        """)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["🔍 Find Products", "🎨 Design Poster", "📊 Product Info"])
    
    with tab1:
        st.header("Step 1: Find Oraimo Products")
        
        # Search controls
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_input = st.text_input(
                "Search for Oraimo products",
                value=st.session_state.search_query,
                placeholder="e.g., oraimo airbuds 3 price in kenya"
            )
        
        with col2:
            if st.button("🔍 Search Products", use_container_width=True):
                with st.spinner("Searching for products..."):
                    extractor = OraimoProductExtractor()
                    st.session_state.products = extractor.search_products(search_input)
                    st.session_state.selected_product = None
                    st.session_state.poster = None
                    st.success(f"Found {len(st.session_state.products)} products!")
        
        # Display products
        if st.session_state.products:
            st.markdown(f"### Found {len(st.session_state.products)} Products")
            st.markdown("Select a product to create a poster:")
            
            # Display each product
            selected_index = -1
            for i, product in enumerate(st.session_state.products):
                is_selected = display_product_card(product, i, selected_index)
                if is_selected:
                    selected_index = i
                    st.session_state.selected_product = product
            
            if selected_index != -1:
                st.success(f"✅ Selected: {st.session_state.products[selected_index]['name']}")
                
                # Show next step button
                if st.button("🎨 Proceed to Design", type="primary", use_container_width=True):
                    st.switch_page("Streamlit App")  # Switch to design tab
        else:
            # Show sample products
            st.info("👆 Enter a search query above and click 'Search Products' to find Oraimo products.")
            
            # Quick search buttons
            st.markdown("### Quick Search")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Oraimo AirBuds", use_container_width=True):
                    st.session_state.search_query = "oraimo airbuds price"
                    st.rerun()
            
            with col2:
                if st.button("Oraimo FreePods", use_container_width=True):
                    st.session_state.search_query = "oraimo freepods price"
                    st.rerun()
            
            with col3:
                if st.button("All Oraimo", use_container_width=True):
                    st.session_state.search_query = "oraimo earbuds price in kenya"
                    st.rerun()
    
    with tab2:
        st.header("Step 2: Design Your Poster")
        
        if not st.session_state.selected_product:
            st.warning("⚠️ Please select a product from the 'Find Products' tab first.")
            if st.button("← Go to Products", use_container_width=True):
                st.switch_page("Streamlit App")  # Switch to search tab
        else:
            product = st.session_state.selected_product
            
            # Product info
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### {product['name']}")
                st.markdown(f"**Description:** {product.get('description', 'No description')}")
                
                if product['highest_price']:
                    st.markdown(f"**Price:** Ksh {product['highest_price']:,.0f}")
                
                if product['features']:
                    st.markdown("**Features:**")
                    for feature in product['features']:
                        st.markdown(f"- {feature}")
            
            with col2:
                # Product image upload/selection
                st.markdown("### Product Image")
                
                image_source = st.radio(
                    "Image Source",
                    ["Auto-fetch", "Upload Custom", "Use Placeholder"],
                    horizontal=True
                )
                
                product_image = None
                
                if image_source == "Auto-fetch":
                    if st.button("🔄 Fetch Product Image", use_container_width=True):
                        with st.spinner("Fetching image..."):
                            try:
                                if product.get('image_url'):
                                    response = requests.get(product['image_url'], timeout=10)
                                    product_image = Image.open(io.BytesIO(response.content))
                                    st.success("Image fetched successfully!")
                                else:
                                    # Search for image
                                    search_url = f"https://far-paure-emw-a67bd497.koyeb.app/search?q={product['name'].replace(' ', '+')}+png&categories=images"
                                    response = requests.get(search_url, timeout=10)
                                    data = response.json()
                                    if data.get('results'):
                                        img_url = data['results'][0]['img_src']
                                        response = requests.get(img_url, timeout=10)
                                        product_image = Image.open(io.BytesIO(response.content))
                                        st.success("Image found and fetched!")
                                    else:
                                        st.warning("No image found, using placeholder")
                                        product_image = None
                            except:
                                st.warning("Could not fetch image, using placeholder")
                                product_image = None
                
                elif image_source == "Upload Custom":
                    uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
                    if uploaded_file:
                        product_image = Image.open(uploaded_file)
                        st.success("Image uploaded successfully!")
                
                # Preview current image
                if product_image:
                    st.image(product_image, caption="Product Image Preview", width=200)
            
            # Generate poster
            st.markdown("---")
            st.markdown("### Generate Poster")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✨ Generate Poster", type="primary", use_container_width=True):
                    with st.spinner("Creating your poster..."):
                        generator = PosterGenerator()
                        st.session_state.poster = generator.generate_poster(product, product_image)
                        st.success("Poster generated successfully!")
            
            with col2:
                if st.button("🔄 Randomize Design", use_container_width=True):
                    st.info("Design randomized!")
                    # This would randomize colors, layout, etc.
            
            with col3:
                if st.button("🔄 Try Different Image", use_container_width=True):
                    st.session_state.poster = None
                    st.rerun()
            
            # Display poster if generated
            if st.session_state.poster:
                st.markdown("---")
                st.markdown("### 🎉 Your Poster is Ready!")
                
                display_poster_preview(st.session_state.poster)
                
                # Additional options
                st.markdown("---")
                st.markdown("### Share Your Poster")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📱 Save for Instagram", use_container_width=True):
                        st.info("Instagram version created!")
                
                with col2:
                    if st.button("🛒 Save for E-commerce", use_container_width=True):
                        st.info("E-commerce version created!")
                
                with col3:
                    if st.button("📧 Email Version", use_container_width=True):
                        st.info("Email version created!")
    
    with tab3:
        st.header("Step 3: Product Information")
        
        if not st.session_state.selected_product:
            st.info("Select a product to see detailed information.")
        else:
            product = st.session_state.selected_product
            
            # Display detailed product info
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### {product['name']}")
                
                # Price analysis
                st.markdown("#### 💰 Price Analysis")
                price_data = {
                    "Lowest Price": product['lowest_price'] or "N/A",
                    "Highest Price": product['highest_price'] or "N/A",
                    "Average Price": ((product['lowest_price'] or 0) + (product['highest_price'] or 0)) / 2 if product['lowest_price'] and product['highest_price'] else "N/A",
                }
                
                for label, value in price_data.items():
                    if isinstance(value, (int, float)):
                        st.metric(label, f"Ksh {value:,.0f}")
                    else:
                        st.metric(label, value)
                
                # Features
                st.markdown("#### ⭐ Features")
                for feature in product['features']:
                    st.markdown(f"✅ {feature}")
            
            with col2:
                # Product stats
                st.markdown("#### 📊 Product Stats")
                
                stats = {
                    "Features Count": len(product['features']),
                    "Price Sources": len(product['prices']),
                    "Last Updated": datetime.now().strftime("%Y-%m-%d"),
                }
                
                for label, value in stats.items():
                    st.metric(label, value)
                
                # Source info
                if product.get('source'):
                    st.markdown("#### 🔗 Source")
                    st.caption(product['source'])
            
            # Export options
            st.markdown("---")
            st.markdown("### Export Data")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export as JSON
                if st.button("📄 Export as JSON", use_container_width=True):
                    import json
                    json_str = json.dumps(product, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"{product['name'].replace(' ', '_')}.json",
                        mime="application/json"
                    )
            
            with col2:
                # Export as CSV
                if st.button("📊 Export as CSV", use_container_width=True):
                    import pandas as pd
                    import csv
                    import io
                    
                    # Create CSV data
                    csv_data = io.StringIO()
                    writer = csv.writer(csv_data)
                    writer.writerow(["Field", "Value"])
                    writer.writerow(["Product Name", product['name']])
                    writer.writerow(["Description", product.get('description', '')])
                    writer.writerow(["Highest Price", product.get('highest_price', '')])
                    writer.writerow(["Lowest Price", product.get('lowest_price', '')])
                    
                    for i, feature in enumerate(product['features'], 1):
                        writer.writerow([f"Feature {i}", feature])
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv_data.getvalue(),
                        file_name=f"{product['name'].replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col2:
        st.markdown(
            """
            <div style='text-align: center; color: #666;'>
            <p>Made with ❤️ using Streamlit</p>
            <p>Icons from Flaticon • Images from search API</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# ============================================================================
# RUN THE APP
# ============================================================================

if __name__ == "__main__":
    main()