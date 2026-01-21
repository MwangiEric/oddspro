# app.py - Final Complete Version
import streamlit as st
import requests
import json
import re
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
import tempfile
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

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .product-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .price-badge {
        background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .feature-tag {
        background: #e3f2fd;
        color: #1976d2;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        margin: 0.2rem;
        font-size: 0.9rem;
        display: inline-block;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 25px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(102,126,234,0.4);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "search": {
        "api_url": "https://far-paule-emw-a67bd497.koyeb.app/search",
        "timeout": 60,  # Increased to 60 seconds
        "max_retries": 2,
        "image_categories": "images",
        "general_categories": "general",
    },
    "images": {
        "min_width": 500,
        "min_height": 500,
        "preferred_size": (800, 800),
        "require_transparent": True,
        "quality_score_weights": {
            "size": 40,
            "transparency": 30,
            "aspect_ratio": 20,
            "source": 10
        }
    },
    "fonts": {
        "primary": "arial.ttf",
        "fallback": "arialbd.ttf",  # Bold version
        "sizes": {
            "title": 72,      # Increased from 48
            "price_badge": 48, # Increased from 32
            "features": 32,   # Increased from 24
            "specs": 28,      # Increased from 20
            "footer": 22      # Increased from 14
        }
    },
    "poster": {
        "size": (1200, 1600),
        "margins": 80,
        "product_max_size": 600,
        "background_blur": 3
    }
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_font(size, bold=False):
    """Get Arial font with fallback"""
    try:
        if bold:
            return ImageFont.truetype(CONFIG["fonts"]["fallback"], size)
        return ImageFont.truetype(CONFIG["fonts"]["primary"], size)
    except:
        # Fallback to default with scaling
        font = ImageFont.load_default()
        # Scale up default font
        return ImageFont.load_default()

def download_image_with_retry(url, max_retries=3):
    """Download image with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        except Exception as e:
            if attempt == max_retries - 1:
                st.warning(f"Failed to download image after {max_retries} attempts: {e}")
            continue
    return None

def extract_official_product_name(search_results):
    """Extract official product name from search results"""
    name_patterns = [
        r"(Oraimo\s+[\w\s\-]+\d+\w*)",  # Oraimo AirBuds 3
        r"(Oraimo\s+[\w\-]+\d+)",       # Oraimo OEB-E06DN
        r"(FreePods\s+\d+\w*)",         # FreePods 3
        r"(AirBuds\s+\d+\w*)",          # AirBuds 3
    ]
    
    name_counts = {}
    for result in search_results:
        content = f"{result.get('title', '')} {result.get('content', '')}"
        for pattern in name_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_name = match.strip()
                name_counts[clean_name] = name_counts.get(clean_name, 0) + 1
    
    # Return most frequently mentioned name
    if name_counts:
        return max(name_counts.items(), key=lambda x: x[1])[0]
    return None

def calculate_image_score(image_url, image_info):
    """Calculate quality score for image based on size, transparency, etc."""
    score = 0
    
    # Size scoring
    resolution = image_info.get('resolution', '')
    match = re.search(r'(\d+)\s*x\s*(\d+)', resolution)
    if match:
        width, height = int(match.group(1)), int(match.group(2))
        min_w, min_h = CONFIG["images"]["min_width"], CONFIG["images"]["min_height"]
        
        if width >= min_w and height >= min_h:
            size_score = min(CONFIG["images"]["quality_score_weights"]["size"], 
                           (width * height) / 2500)
            score += size_score
    
    # Transparency check (from URL/description)
    if '.png' in image_url.lower():
        score += CONFIG["images"]["quality_score_weights"]["transparency"]
    
    # Source quality
    if 'oraimo.com' in image_url:
        score += CONFIG["images"]["quality_score_weights"]["source"]
    
    return score

def remove_white_background(image):
    """Remove white/light background from image"""
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    data = image.getdata()
    new_data = []
    
    for item in data:
        # Make white/light pixels transparent
        if item[0] > 220 and item[1] > 220 and item[2] > 220:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    
    image.putdata(new_data)
    return image

def create_price_badge(price):
    """Create circular price badge"""
    size = 200
    badge = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    
    # Draw badge
    draw.ellipse([0, 0, size, size], fill=(220, 53, 69, 230))
    
    # Add price text
    font_large = get_font(48, bold=True)  # Increased from 36
    font_small = get_font(24, bold=True)  # Increased from 20
    
    # Format price
    price_text = f"Ksh\n{price:,.0f}" if price >= 1000 else f"Ksh\n{price}"
    
    draw.text(
        (size//2, size//2 - 10),
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

# ============================================================================
# SEARCH ENGINE
# ============================================================================

class OraimoSearchEngine:
    """Search engine for Oraimo products with improved timeouts"""
    
    def __init__(self):
        self.session = requests.Session()
        self.timeout = CONFIG["search"]["timeout"]
    
    def search_products(self, query):
        """Search for Oraimo products with extended timeout"""
        search_query = f"{query} Oraimo price in Kenya"
        params = {
            "q": search_query.replace(" ", "+"),
            "categories": CONFIG["search"]["general_categories"],
            "format": "json",
        }
        
        with st.spinner(f"Searching for Oraimo products (timeout: {self.timeout}s)..."):
            try:
                response = self.session.get(
                    CONFIG["search"]["api_url"],
                    params=params,
                    timeout=self.timeout
                )
                data = response.json()
                
                if data.get("results"):
                    return self.process_search_results(data["results"])
                else:
                    st.warning("No results found. Using sample data.")
                    return self.get_sample_products()
                    
            except requests.exceptions.Timeout:
                st.error(f"Search timed out after {self.timeout} seconds. Please try a simpler search term.")
                return self.get_sample_products()
            except Exception as e:
                st.error(f"Search error: {e}")
                return self.get_sample_products()
    
    def process_search_results(self, results):
        """Process and extract product information"""
        products = {}
        
        for result in results:
            content = result.get("content", "").lower()
            title = result.get("title", "")
            
            # Only process Oraimo products
            if "oraimo" in content.lower() or "oraimo" in title.lower():
                
                # Extract official name
                official_name = extract_official_product_name([result])
                if not official_name:
                    official_name = self.extract_name_from_title(title)
                
                if official_name and official_name not in products:
                    # Extract prices
                    prices = self.extract_prices(content, title)
                    
                    # Extract features
                    features = self.extract_features(content)
                    
                    products[official_name] = {
                        "name": official_name,
                        "official_name": official_name,
                        "prices": prices,
                        "highest_price": max(prices) if prices else None,
                        "lowest_price": min(prices) if prices else None,
                        "features": list(features)[:8],
                        "source_url": result.get("url", ""),
                        "description": title[:120],
                    }
        
        # Convert to list and sort by price
        product_list = list(products.values())
        product_list.sort(key=lambda x: x["highest_price"] or 0, reverse=True)
        
        return product_list
    
    def extract_name_from_title(self, title):
        """Extract product name from title"""
        # Remove unnecessary parts
        clean_title = title.split("|")[0].split("-")[0].strip()
        return clean_title
    
    def extract_prices(self, content, title):
        """Extract prices from content"""
        prices = []
        patterns = [
            r"(?:Ksh|KSH|Kes)\s*([\d,]+(?:\.\d{2})?)",
            r"price[\s:]*K?sh?\s*([\d,]+)",
            r"buy[\s:]*([\d,]+)",
            r"ksh\s*([\d,]+)",
        ]
        
        all_text = f"{title} {content}"
        
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = str(match).replace(',', '')
                    price = float(price_str) if '.' in price_str else int(price_str)
                    
                    # Filter reasonable prices
                    if 1000 <= price <= 50000:
                        prices.append(price)
                except:
                    continue
        
        return list(set(prices))
    
    def extract_features(self, content):
        """Extract features from content"""
        features = set()
        
        # Look for feature keywords
        feature_keywords = [
            "waterproof", "battery", "wireless", "bluetooth", 
            "noise cancellation", "bass", "touch", "voice assistant",
            "charging", "comfort", "lightweight", "sweatproof",
            "stereo", "microphone", "fast charging", "long battery",
            "ipx7", "ipx5", "anc", "true wireless", "app control"
        ]
        
        content_lower = content.lower()
        
        for keyword in feature_keywords:
            if keyword in content_lower:
                # Extract context around keyword
                start = max(0, content_lower.find(keyword) - 30)
                end = min(len(content_lower), content_lower.find(keyword) + len(keyword) + 40)
                phrase = content[start:end].strip()
                
                # Clean up the phrase
                phrase = re.sub(r'[^\w\s\-]', ' ', phrase)
                phrase = ' '.join(phrase.split()).title()
                
                if phrase and len(phrase) > 5:
                    features.add(phrase)
        
        # Add default features if needed
        if len(features) < 3:
            features.update([
                "Wireless Bluetooth Connectivity",
                "High Quality Sound",
                "Long Battery Life",
                "Comfortable Fit",
                "Noise Cancellation",
                "Voice Assistant Support",
            ])
        
        return features
    
    def get_sample_products(self):
        """Return sample products for demo"""
        return [
            {
                "name": "Oraimo AirBuds 3",
                "official_name": "Oraimo AirBuds 3",
                "prices": [5000, 5499],
                "highest_price": 5499,
                "lowest_price": 5000,
                "features": ["IPX7 Waterproof", "30H Battery Life", "Bluetooth 5.3", "Touch Controls", "Voice Assistant"],
                "source_url": "",
                "description": "Powerful Bass IPX7 Waterproof TWS True Wireless Earbuds"
            },
            {
                "name": "Oraimo FreePods 3",
                "official_name": "Oraimo FreePods 3",
                "prices": [3800],
                "highest_price": 3800,
                "lowest_price": 3800,
                "features": ["True Wireless", "Bass Boost", "Comfort Fit", "Fast Charging"],
                "source_url": "",
                "description": "TWS True Wireless Stereo Earbuds"
            },
            {
                "name": "Oraimo FreePods Pro",
                "official_name": "Oraimo FreePods Pro",
                "prices": [8495],
                "highest_price": 8495,
                "lowest_price": 8495,
                "features": ["Active Noise Cancellation", "35H Playtime", "App Control", "Voice Assistant"],
                "source_url": "",
                "description": "ANC Active Noise Cancellation TWS True Wireless Earbuds"
            }
        ]
    
    def search_product_images(self, official_name):
        """Search for product images using official name"""
        # Use official name for image search
        search_query = f'"{official_name}" product image png transparent background'
        params = {
            "q": search_query.replace(" ", "+"),
            "categories": CONFIG["search"]["image_categories"],
            "format": "json",
        }
        
        with st.spinner(f"Searching for product images (timeout: {self.timeout}s)..."):
            try:
                response = self.session.get(
                    CONFIG["search"]["api_url"],
                    params=params,
                    timeout=self.timeout
                )
                data = response.json()
                
                if data.get("results"):
                    return self.filter_best_images(data["results"])
                else:
                    st.warning("No images found. Will use placeholder.")
                    return []
                    
            except requests.exceptions.Timeout:
                st.error(f"Image search timed out after {self.timeout} seconds.")
                return []
            except Exception as e:
                st.error(f"Image search error: {e}")
                return []
    
    def filter_best_images(self, image_results):
        """Filter and rank images by quality"""
        scored_images = []
        
        for img_data in image_results:
            img_url = img_data.get("img_src")
            if not img_url:
                continue
            
            # Calculate quality score
            score = calculate_image_score(img_url, img_data)
            
            # Only include images with minimum score
            if score >= 30:  # Minimum threshold
                scored_images.append({
                    "url": img_url,
                    "score": score,
                    "resolution": img_data.get("resolution", ""),
                    "title": img_data.get("title", ""),
                })
        
        # Sort by score (highest first)
        scored_images.sort(key=lambda x: x["score"], reverse=True)
        
        # Log selection
        if scored_images:
            st.info(f"Found {len(scored_images)} quality images. Best: {scored_images[0]['score']:.1f} points")
        
        return scored_images[:5]  # Return top 5

# ============================================================================
# POSTER GENERATOR
# ============================================================================

class OraimoPosterGenerator:
    """Generate professional posters for Oraimo products"""
    
    def __init__(self):
        self.search_engine = OraimoSearchEngine()
    
    def generate_poster(self, product, selected_image=None):
        """Generate poster for product"""
        # Create background
        background = self.create_background()
        
        # Prepare product image
        product_image = self.prepare_product_image(selected_image) if selected_image else self.create_placeholder()
        
        # Create poster
        poster = Image.new('RGBA', CONFIG["poster"]["size"], (255, 255, 255, 0))
        poster.paste(background, (0, 0))
        
        # Add product image
        img_width, img_height = product_image.size
        img_x = (CONFIG["poster"]["size"][0] - img_width) // 2
        img_y = 150
        poster.paste(product_image, (img_x, img_y), product_image)
        
        # Add price badge
        if product.get('highest_price'):
            badge = create_price_badge(product['highest_price'])
            badge_x = CONFIG["poster"]["size"][0] - 250
            badge_y = 50
            poster.paste(badge, (badge_x, badge_y), badge)
        
        # Add text elements
        draw = ImageDraw.Draw(poster)
        
        # Product name
        self.add_product_name(draw, product['official_name'], img_y + img_height + 60)
        
        # Features
        features_y = img_y + img_height + 180
        self.add_features(draw, product['features'], features_y)
        
        # Footer
        self.add_footer(draw)
        
        return poster
    
    def create_background(self):
        """Create abstract background"""
        width, height = CONFIG["poster"]["size"]
        bg = Image.new('RGB', (width, height), (245, 247, 250))
        draw = ImageDraw.Draw(bg)
        
        # Add gradient
        for i in range(height):
            alpha = int(50 * (i / height))
            draw.line([(0, i), (width, i)], fill=(70, 130, 180, alpha))
        
        # Add abstract shapes
        colors = [
            (70, 130, 180, 20),
            (52, 152, 219, 15),
            (231, 76, 60, 10),
        ]
        
        for _ in range(15):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(100, 400)
            color = random.choice(colors)
            
            if random.choice([True, False]):
                draw.ellipse([x, y, x + size, y + size], fill=color)
            else:
                draw.rectangle([x, y, x + size, y + size], fill=color)
        
        # Apply blur
        bg = bg.filter(ImageFilter.GaussianBlur(CONFIG["poster"]["background_blur"]))
        
        return bg
    
    def prepare_product_image(self, image):
        """Prepare product image for poster"""
        # Remove background and resize
        image = remove_white_background(image)
        
        # Resize to fit poster
        max_size = CONFIG["poster"]["product_max_size"]
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        return image
    
    def create_placeholder(self):
        """Create placeholder product image"""
        img = Image.new('RGBA', (400, 400), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw earbud
        draw.ellipse([50, 50, 350, 350], outline=(100, 100, 100), width=5)
        draw.ellipse([100, 100, 300, 300], fill=(70, 130, 180, 200))
        
        # Add text
        font = get_font(40, bold=True)
        draw.text((200, 200), "ORAIMO", fill=(255, 255, 255), anchor="mm", font=font)
        
        return img
    
    def add_product_name(self, draw, name, y_position):
        """Add product name to poster"""
        font = get_font(CONFIG["fonts"]["sizes"]["title"], bold=True)
        
        # Truncate if too long
        if len(name) > 25:
            name = name[:22] + "..."
        
        draw.text(
            (CONFIG["poster"]["size"][0] // 2, y_position),
            name.upper(),
            font=font,
            fill=(33, 37, 41),
            anchor="mm"
        )
    
    def add_features(self, draw, features, start_y):
        """Add features to poster"""
        font = get_font(CONFIG["fonts"]["sizes"]["features"])
        
        # Display features in two columns
        mid_point = CONFIG["poster"]["size"][0] // 2
        left_x = mid_point - 200
        right_x = mid_point + 200
        
        for i, feature in enumerate(features[:8]):  # Max 8 features
            if i % 2 == 0:
                x = left_x
            else:
                x = right_x
            
            y = start_y + ((i // 2) * 70)
            
            # Truncate feature if too long
            if len(feature) > 25:
                feature = feature[:22] + "..."
            
            draw.text(
                (x, y),
                f"• {feature}",
                font=font,
                fill=(52, 58, 64),
                anchor="lm"
            )
    
    def add_footer(self, draw):
        """Add footer to poster"""
        font = get_font(CONFIG["fonts"]["sizes"]["footer"])
        
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        draw.text(
            (CONFIG["poster"]["size"][0] // 2, CONFIG["poster"]["size"][1] - 40),
            footer_text,
            font=font,
            fill=(108, 117, 125),
            anchor="mm"
        )

# ============================================================================
# STREAMLIT APP
# ============================================================================

def main():
    """Main Streamlit application"""
    
    # Title
    st.title("🎨 Oraimo Product Poster Generator")
    st.markdown("Create professional posters for Oraimo products with automatic price extraction")
    
    # Initialize session state
    if 'products' not in st.session_state:
        st.session_state.products = []
    if 'selected_product' not in st.session_state:
        st.session_state.selected_product = None
    if 'product_images' not in st.session_state:
        st.session_state.product_images = []
    if 'generated_poster' not in st.session_state:
        st.session_state.generated_poster = None
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Search settings
        st.subheader("Search Settings")
        search_query = st.text_input(
            "Search Query",
            value="Oraimo earbuds price in Kenya",
            help="Enter search terms for Oraimo products"
        )
        
        # Image settings
        st.subheader("Image Settings")
        min_size = st.slider("Minimum Image Size", 300, 1000, 500)
        require_transparent = st.checkbox("Prefer Transparent PNGs", value=True)
        
        # Poster settings
        st.subheader("Poster Settings")
        badge_position = st.selectbox(
            "Price Badge Position",
            ["Top Right", "Top Left", "Bottom Right", "Bottom Left"],
            index=0
        )
        
        # Update config
        CONFIG["images"]["min_width"] = min_size
        CONFIG["images"]["min_height"] = min_size
        CONFIG["images"]["require_transparent"] = require_transparent
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Search Products", "🎨 Design Poster", "📥 Download"])
    
    with tab1:
        st.header("Step 1: Find Oraimo Products")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search_input = st.text_input(
                "Enter product search",
                value=search_query,
                placeholder="e.g., Oraimo AirBuds 3, Oraimo FreePods Pro"
            )
        
        with col2:
            if st.button("🔍 Search", use_container_width=True):
                with st.spinner(f"Searching (timeout: {CONFIG['search']['timeout']}s)..."):
                    search_engine = OraimoSearchEngine()
                    st.session_state.products = search_engine.search_products(search_input)
                    st.session_state.selected_product = None
                    st.session_state.product_images = []
                    st.session_state.generated_poster = None
        
        # Display products
        if st.session_state.products:
            st.subheader(f"Found {len(st.session_state.products)} Products")
            
            for idx, product in enumerate(st.session_state.products):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"### {product['name']}")
                        st.caption(product['description'])
                        
                        # Features
                        if product['features']:
                            cols = st.columns(4)
                            for i, feature in enumerate(product['features'][:4]):
                                with cols[i % 4]:
                                    st.markdown(f'<span class="feature-tag">{feature}</span>', 
                                               unsafe_allow_html=True)
                    
                    with col2:
                        if product['highest_price']:
                            st.markdown(f'<div class="price-badge">Ksh {product["highest_price"]:,.0f}</div>', 
                                       unsafe_allow_html=True)
                        else:
                            st.warning("No price")
                    
                    with col3:
                        if st.button("Select", key=f"select_{idx}", use_container_width=True):
                            st.session_state.selected_product = product
                            
                            # Search for images of this product
                            with st.spinner("Searching for product images..."):
                                search_engine = OraimoSearchEngine()
                                images = search_engine.search_product_images(product['official_name'])
                                st.session_state.product_images = images
                            
                            st.success(f"Selected: {product['name']}")
                            st.rerun()
                    
                    st.divider()
        
        else:
            st.info("👆 Enter a search query and click 'Search' to find Oraimo products")
    
    with tab2:
        st.header("Step 2: Design Your Poster")
        
        if not st.session_state.selected_product:
            st.warning("Please select a product from the Search tab first.")
        else:
            product = st.session_state.selected_product
            
            # Product info
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(product['name'])
                st.write(product['description'])
                
                # Price info
                if product['highest_price']:
                    st.metric("Price", f"Ksh {product['highest_price']:,.0f}")
                
                # Features
                st.write("**Features:**")
                for feature in product['features']:
                    st.write(f"• {feature}")
            
            with col2:
                # Image selection
                st.subheader("Product Image")
                
                if st.session_state.product_images:
                    selected_image_idx = 0
                    
                    # Show image options
                    for i, img_info in enumerate(st.session_state.product_images[:3]):
                        col_img, col_info = st.columns([2, 3])
                        
                        with col_img:
                            # Try to display thumbnail
                            try:
                                # Download and show thumbnail
                                img = download_image_with_retry(img_info['url'])
                                if img:
                                    img.thumbnail((100, 100))
                                    st.image(img, use_column_width=True)
                            except:
                                st.write("📷")
                        
                        with col_info:
                            st.caption(f"Score: {img_info['score']:.1f}")
                            st.caption(img_info['resolution'])
                            
                            if st.button(f"Use Image {i+1}", key=f"img_{i}"):
                                selected_image_idx = i
                    
                    # Download selected image
                    if st.button("🔄 Load Selected Image", use_container_width=True):
                        with st.spinner("Downloading image..."):
                            img_info = st.session_state.product_images[selected_image_idx]
                            image = download_image_with_retry(img_info['url'])
                            
                            if image:
                                # Generate poster
                                generator = OraimoPosterGenerator()
                                poster = generator.generate_poster(product, image)
                                st.session_state.generated_poster = poster
                                st.success("Poster generated!")
                            else:
                                st.error("Failed to download image")
                
                else:
                    st.info("No images found for this product")
                    
                    if st.button("Use Placeholder Image", use_container_width=True):
                        generator = OraimoPosterGenerator()
                        poster = generator.generate_poster(product)
                        st.session_state.generated_poster = poster
                        st.success("Poster generated with placeholder!")
            
            # Generate poster button
            if st.button("✨ Generate Poster Now", type="primary", use_container_width=True):
                generator = OraimoPosterGenerator()
                
                if st.session_state.product_images:
                    # Use first image
                    img_info = st.session_state.product_images[0]
                    image = download_image_with_retry(img_info['url'])
                    poster = generator.generate_poster(product, image)
                else:
                    poster = generator.generate_poster(product)
                
                st.session_state.generated_poster = poster
                st.success("Poster generated successfully!")
    
    with tab3:
        st.header("Step 3: Download Your Poster")
        
        if not st.session_state.generated_poster:
            st.warning("Please generate a poster in the Design tab first.")
        else:
            # Show poster
            st.image(st.session_state.generated_poster, use_column_width=True)
            
            # Download options
            col1, col2 = st.columns(2)
            
            with col1:
                # Convert to bytes for download
                buf = io.BytesIO()
                st.session_state.generated_poster.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                
                # Download button
                product_name = st.session_state.selected_product['name']
                filename = f"oraimo_{product_name.replace(' ', '_')}_poster.png"
                
                st.download_button(
                    label="📥 Download PNG",
                    data=img_bytes,
                    file_name=filename,
                    mime="image/png",
                    use_container_width=True
                )
            
            with col2:
                # Quality options
                quality = st.slider("Quality", 50, 100, 95)
                
                if st.button("🔄 Regenerate with Quality", use_container_width=True):
                    # Regenerate with quality setting
                    st.info(f"Will regenerate with {quality}% quality")
            
            # Additional options
            st.subheader("Export Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Instagram Version", use_container_width=True):
                    st.info("Instagram square version (1080x1080)")
            
            with col2:
                if st.button("E-commerce Version", use_container_width=True):
                    st.info("E-commerce version (800x800)")
            
            with col3:
                if st.button("Print Version", use_container_width=True):
                    st.info("High-res print version (2400x3200)")
            
            # Poster info
            st.divider()
            st.subheader("Poster Information")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Size", f"{CONFIG['poster']['size'][0]}x{CONFIG['poster']['size'][1]}")
            
            with col2:
                if st.session_state.selected_product:
                    price = st.session_state.selected_product.get('highest_price', 'N/A')
                    st.metric("Price Displayed", f"Ksh {price:,}" if isinstance(price, (int, float)) else price)
            
            with col3:
                features_count = len(st.session_state.selected_product.get('features', []))
                st.metric("Features Displayed", features_count)

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == "__main__":
    main()