import requests
import json
import re
import random
from datetime import datetime

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# ----------------------------------------------------------------------------
# Search Configuration
# ----------------------------------------------------------------------------
SEARCH_CONFIG = {
    "api_url": "https://far-paule-emw-a67bd497.koyeb.app/search",
    "categories": "general",
    "language": "auto",
    "safesearch": 0,
    "format": "json",
    "max_results": 5,
    
    "search_templates": {
        "price_search": "{product} price in kenya",
        "review_search": "{product} review features specifications",
        "store_search": "{product} site:kenyatronics.com OR site:jumia.co.ke",
    },
    
    "currency_symbols": {
        "KES": ["Ksh", "KSH", "Kenya Shillings"],
        "USD": ["$", "USD"],
        "EUR": ["€", "EUR"],
    }
}

# ----------------------------------------------------------------------------
# Regex Patterns for Information Extraction
# ----------------------------------------------------------------------------
EXTRACTION_PATTERNS = {
    "price": [
        r"(?:Ksh|KSH|Kes)\s*([\d,]+(?:\.\d{2})?)",
        r"\$?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s*(?:dollars|USD)",
        r"price[\s:]*([\d,]+)",
        r"buy[\s:]*([\d,]+)",
        r"ksh\s*([\d,]+)",
    ],
    
    "features": [
        r"(?:features?|specifications?|key\s+points)[:;]?(.*?)(?:\n|\.|$)",
        r"(?:including|with)\s+(.*?)(?:\.|,)",
        r"(?:bass|waterproof|battery|wireless|bluetooth|noise\s+cancellation|anc|ipx\d+)",
    ],
    
    "product_model": [
        r"(Oraimo\s+(?:AirBuds|FreePods|OEB)[\s\d\-]+\d+)",
        r"([A-Z][a-z]+\s+[\w\s]+\d+\w?)",
        r"(Model\s*[:]?\s*[\w\d\-]+)",
    ],
    
    "specifications": [
        r"(\d+\s*hr(?:\s*playtime|battery)?)",
        r"(IPX\d+\s*waterproof)",
        r"(\d+mm\s*driver)",
        r"(Bluetooth\s*\d+\.?\d*)",
        r"(\d+\s*hrs?\s*charging)",
    ],
}

# ----------------------------------------------------------------------------
# Product Information Database
# ----------------------------------------------------------------------------
PRODUCT_INFO_CONFIG = {
    "default_features": [
        "Wireless Bluetooth Connectivity",
        "High Quality Sound",
        "Long Battery Life",
        "Comfortable Fit",
        "Noise Cancellation",
        "Voice Assistant Support",
        "Water Resistant",
        "Touch Controls",
    ],
    
    "category_features": {
        "earbuds": ["True Wireless", "Charging Case", "In-Ear Detection"],
        "speakers": ["Portable", "Bass Boost", "Party Mode"],
        "headphones": ["Over-Ear", "Foldable", "Adjustable Headband"],
    },
    
    "price_ranges": {
        "budget": {"min": 1000, "max": 3000, "label": "Budget"},
        "mid_range": {"min": 3000, "max": 8000, "label": "Mid-Range"},
        "premium": {"min": 8000, "max": 20000, "label": "Premium"},
    }
}

# ============================================================================
# PRODUCT INFORMATION EXTRACTOR
# ============================================================================

class ProductInfoExtractor:
    """Extracts product information from search results"""
    
    def __init__(self, search_config=SEARCH_CONFIG, extraction_patterns=EXTRACTION_PATTERNS):
        self.search_config = search_config
        self.patterns = extraction_patterns
    
    def search_product_info(self, product_query):
        """Search for product information"""
        query = product_query.replace(" ", "+")
        
        params = {
            "q": query,
            "categories": self.search_config["categories"],
            "language": self.search_config["language"],
            "safesearch": self.search_config["safesearch"],
            "format": self.search_config["format"],
        }
        
        try:
            print(f"🔍 Searching for: {product_query}")
            response = requests.get(
                self.search_config["api_url"],
                params=params,
                timeout=15
            )
            data = response.json()
            
            if data.get("number_of_results", 0) > 0:
                return self._extract_info_from_results(data["results"])
            else:
                print("⚠️ No search results found")
                return self._get_default_info(product_query)
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            return self._get_default_info(product_query)
    
    def _extract_info_from_results(self, results):
        """Extract information from search results"""
        product_info = {
            "name": "",
            "prices": [],
            "features": set(),
            "specifications": set(),
            "source_urls": [],
            "best_price": None,
            "price_range": "unknown",
            "extracted_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        for result in results[:self.search_config["max_results"]]:
            content = result.get("content", "").lower()
            title = result.get("title", "")
            url = result.get("url", "")
            
            # Extract product name
            if not product_info["name"]:
                product_info["name"] = self._extract_product_name(title, content)
            
            # Extract prices
            prices = self._extract_prices(content, title)
            product_info["prices"].extend(prices)
            
            # Extract features and specifications
            features = self._extract_features(content)
            product_info["features"].update(features)
            
            specs = self._extract_specifications(content)
            product_info["specifications"].update(specs)
            
            # Store source URL if it contains price
            if prices and url:
                product_info["source_urls"].append(url)
        
        # Process extracted data
        product_info = self._process_extracted_info(product_info)
        
        return product_info
    
    def _extract_product_name(self, title, content):
        """Extract product name from title/content"""
        # Try regex patterns first
        for pattern in self.patterns["product_model"]:
            matches = re.findall(pattern, title, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # Fallback: Use title (clean it up)
        if title:
            # Remove store names, prices, etc.
            clean_title = re.sub(r'[-|]', ' ', title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            
            # Split and take first meaningful part
            parts = clean_title.split()
            if len(parts) > 3:
                return " ".join(parts[:4])
            return clean_title
        
        # Last resort
        return "Premium Wireless Earbuds"
    
    def _extract_prices(self, content, title):
        """Extract prices from text"""
        prices = []
        all_text = f"{title} {content}"
        
        for pattern in self.patterns["price"]:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the price string
                    price_str = str(match).replace(',', '')
                    if '.' in price_str:
                        price = float(price_str)
                    else:
                        price = int(price_str)
                    
                    # Check if it's a reasonable price (not too high/low for electronics)
                    if 100 <= price <= 50000:  # Reasonable range for earbuds in Kenya
                        prices.append({
                            "amount": price,
                            "currency": "KES",
                            "source": "extracted",
                            "raw_match": match
                        })
                except (ValueError, AttributeError):
                    continue
        
        return prices
    
    def _extract_features(self, content):
        """Extract features from content"""
        features = set()
        
        # Check for feature sections
        for pattern in self.patterns["features"][:2]:
            matches = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                feature_text = matches.group(1)
                # Split by commas, semicolons, or "and"
                split_features = re.split(r'[,;]|\band\b', feature_text)
                for feature in split_features:
                    clean_feature = feature.strip()
                    if clean_feature and len(clean_feature) > 3:
                        features.add(clean_feature.capitalize())
        
        # Look for specific keywords
        for keyword in self.patterns["features"][2:]:
            if re.search(keyword, content, re.IGNORECASE):
                features.add(keyword.replace("\\s+", " ").title())
        
        return features
    
    def _extract_specifications(self, content):
        """Extract technical specifications"""
        specs = set()
        
        for pattern in self.patterns["specifications"]:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                specs.add(match.title())
        
        return specs
    
    def _process_extracted_info(self, product_info):
        """Process and clean extracted information"""
        # Convert sets to lists for JSON serialization
        product_info["features"] = list(product_info["features"])
        product_info["specifications"] = list(product_info["specifications"])
        
        # Find best price (lowest)
        if product_info["prices"]:
            valid_prices = [p["amount"] for p in product_info["prices"]]
            min_price = min(valid_prices)
            max_price = max(valid_prices)
            
            # Find the price object with minimum amount
            best_price_obj = min(product_info["prices"], key=lambda x: x["amount"])
            product_info["best_price"] = best_price_obj
            
            # Determine price range
            avg_price = sum(valid_prices) / len(valid_prices)
            product_info["price_range"] = self._categorize_price_range(avg_price)
            
            # Format price display
            product_info["formatted_price"] = f"Ksh {min_price:,.0f}"
            if max_price != min_price:
                product_info["formatted_price"] += f" - Ksh {max_price:,.0f}"
        else:
            product_info["formatted_price"] = "Price not available"
        
        # Enhance features if too few
        if len(product_info["features"]) < 3:
            product_info["features"].extend(self._get_smart_features(product_info))
        
        # Limit features to reasonable number
        product_info["features"] = product_info["features"][:8]
        product_info["specifications"] = product_info["specifications"][:6]
        
        return product_info
    
    def _categorize_price_range(self, price):
        """Categorize price into range"""
        for range_name, range_info in PRODUCT_INFO_CONFIG["price_ranges"].items():
            if range_info["min"] <= price <= range_info["max"]:
                return range_info["label"]
        return "Premium" if price > 8000 else "Budget"
    
    def _get_smart_features(self, product_info):
        """Generate smart features based on product info"""
        features = []
        
        # Based on product name
        name_lower = product_info["name"].lower()
        
        if any(word in name_lower for word in ["airbuds", "freepods", "earbuds", "earphone"]):
            features.extend(PRODUCT_INFO_CONFIG["category_features"]["earbuds"])
        
        if "waterproof" in name_lower or any("ipx" in spec.lower() for spec in product_info["specifications"]):
            features.append("Water Resistant")
        
        if "bass" in name_lower:
            features.append("Enhanced Bass")
        
        if any(word in name_lower for word in ["pro", "premium", "max"]):
            features.append("Premium Build Quality")
        
        # Based on price range
        if product_info["price_range"] == "Premium":
            features.append("Premium Materials")
            features.append("Advanced Features")
        elif product_info["price_range"] == "Mid-Range":
            features.append("Great Value")
            features.append("Balanced Performance")
        
        # Add some defaults
        defaults = random.sample(PRODUCT_INFO_CONFIG["default_features"], 3)
        features.extend(defaults)
        
        return list(set(features))  # Remove duplicates
    
    def _get_default_info(self, product_query):
        """Get default product information when search fails"""
        return {
            "name": product_query.title(),
            "prices": [],
            "features": random.sample(PRODUCT_INFO_CONFIG["default_features"], 5),
            "specifications": [],
            "source_urls": [],
            "best_price": None,
            "price_range": "Mid-Range",
            "formatted_price": "Check store for price",
            "extracted_date": datetime.now().strftime("%Y-%m-%d")
        }

# ============================================================================
# ENHANCED POSTER GENERATOR WITH PRODUCT INFO
# ============================================================================

class EnhancedPosterGenerator:
    """Generates posters with product information"""
    
    def __init__(self, product_extractor=None):
        self.extractor = product_extractor or ProductInfoExtractor()
        self.s3_storage = None  # Would be initialized from previous code
        self.product_info = None
    
    def generate_product_poster(self, product_query):
        """Generate poster with product information"""
        print(f"\n📊 Extracting product information...")
        
        # Extract product information
        self.product_info = self.extractor.search_product_info(product_query)
        
        # Display extracted info
        self._display_product_info()
        
        # Search for product image (using existing code)
        product_image = self._search_product_image(product_query)
        
        if product_image:
            # Generate poster with product info
            poster = self._create_enhanced_poster(product_image)
            
            # Save and upload
            self._save_and_distribute(poster, product_query)
            
            return poster
        else:
            print("❌ Could not find product image")
            return None
    
    def _display_product_info(self):
        """Display extracted product information"""
        if not self.product_info:
            return
        
        print(f"\n✅ EXTRACTED PRODUCT INFORMATION")
        print(f"   {'─' * 50}")
        print(f"   Product: {self.product_info['name']}")
        print(f"   Price: {self.product_info['formatted_price']}")
        print(f"   Price Range: {self.product_info['price_range']}")
        
        if self.product_info['features']:
            print(f"   Features:")
            for feature in self.product_info['features'][:4]:
                print(f"     • {feature}")
        
        if self.product_info['specifications']:
            print(f"   Specifications:")
            for spec in self.product_info['specifications'][:3]:
                print(f"     • {spec}")
        
        if self.product_info['source_urls']:
            print(f"   Sources: {len(self.product_info['source_urls'])} found")
        
        print(f"   Extracted: {self.product_info['extracted_date']}")
        print(f"   {'─' * 50}")
    
    def _search_product_image(self, product_query):
        """Search for product image (simplified version)"""
        # This would use the existing image search code
        # For now, return a placeholder
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (500, 500), (70, 130, 180))
            draw = ImageDraw.Draw(img)
            draw.ellipse([100, 100, 400, 400], fill=(50, 50, 50))
            return img
        except:
            return None
    
    def _create_enhanced_poster(self, product_image):
        """Create poster with product information"""
        # This would integrate with the existing poster generation code
        # Enhanced to include product info
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple poster for demonstration
        width, height = 800, 1200
        poster = Image.new('RGB', (width, height), (240, 240, 240))
        draw = ImageDraw.Draw(poster)
        
        # Add product image placeholder
        product_image = product_image.resize((400, 400))
        poster.paste(product_image, (200, 100))
        
        # Add product info
        try:
            font_large = ImageFont.truetype("arial.ttf", 36)
            font_medium = ImageFont.truetype("arial.ttf", 24)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Product name
        name = self.product_info['name'][:30]
        draw.text((width//2, 550), name, fill=(0, 0, 0), font=font_large, anchor="mm")
        
        # Price (prominent)
        price_y = 600
        if self.product_info['best_price']:
            price_text = f"Ksh {self.product_info['best_price']['amount']:,.0f}"
            draw.text((width//2, price_y), price_text, fill=(0, 100, 0), 
                     font=ImageFont.truetype("arial.ttf", 48), anchor="mm")
        
        # Features
        features_y = 680
        draw.text((50, features_y), "Key Features:", fill=(0, 0, 0), font=font_medium)
        
        for i, feature in enumerate(self.product_info['features'][:5]):
            y = features_y + 40 + i * 30
            draw.text((70, y), f"• {feature}", fill=(50, 50, 50), font=font_small)
        
        # Footer
        footer_y = height - 50
        footer_text = f"Extracted from {len(self.product_info['source_urls'])} sources"
        draw.text((width//2, footer_y), footer_text, fill=(100, 100, 100), 
                 font=font_small, anchor="mm")
        
        return poster
    
    def _save_and_distribute(self, poster, product_query):
        """Save poster and upload to cloud"""
        # Save locally
        filename = f"product_poster_{product_query.replace(' ', '_')}.png"
        poster.save(filename, "PNG")
        print(f"\n✅ Poster saved: {filename}")
        
        # Upload to S3 if configured
        # self._upload_to_s3(poster, filename)
        
        return filename

# ============================================================================
# QUERY BUILDER FOR SMART SEARCHES
# ============================================================================

class SmartQueryBuilder:
    """Builds smart search queries for product information"""
    
    def __init__(self, search_config=SEARCH_CONFIG):
        self.config = search_config
    
    def build_queries(self, product_name):
        """Build multiple search queries for comprehensive results"""
        queries = []
        
        # Basic price search
        price_query = self.config["search_templates"]["price_search"].format(product=product_name)
        queries.append(("Price Search", price_query))
        
        # Reviews and features
        review_query = self.config["search_templates"]["review_search"].format(product=product_name)
        queries.append(("Feature Search", review_query))
        
        # Store-specific search
        store_query = self.config["search_templates"]["store_search"].format(product=product_name)
        queries.append(("Store Search", store_query))
        
        # Brand-specific searches
        if "oraimo" in product_name.lower():
            queries.append(("Oraimo Official", "oraimo.com " + product_name))
        
        return queries
    
    def execute_multi_search(self, product_name):
        """Execute multiple searches and combine results"""
        queries = self.build_queries(product_name)
        all_results = []
        
        print(f"\n🔍 Executing smart search for: {product_name}")
        
        for query_type, query in queries:
            print(f"   Searching: {query_type}...")
            
            params = {
                "q": query.replace(" ", "+"),
                "categories": self.config["categories"],
                "language": self.config["language"],
                "safesearch": self.config["safesearch"],
                "format": self.config["format"],
            }
            
            try:
                response = requests.get(self.config["api_url"], params=params, timeout=10)
                data = response.json()
                
                if data.get("results"):
                    for result in data["results"][:2]:  # Take top 2 from each search
                        result["query_type"] = query_type
                        all_results.append(result)
                
            except Exception as e:
                print(f"   ❌ {query_type} failed: {e}")
        
        return all_results

# ============================================================================
# MAIN APPLICATION WITH PRODUCT INFO
# ============================================================================

def main():
    """Main application with product information extraction"""
    print("=" * 60)
    print("🛍️  SMART PRODUCT POSTER GENERATOR WITH PRICE DETECTION")
    print("=" * 60)
    
    # Initialize components
    extractor = ProductInfoExtractor()
    poster_gen = EnhancedPosterGenerator(extractor)
    query_builder = SmartQueryBuilder()
    
    # Get product query
    product_query = input("\nEnter product name (e.g., 'Oraimo AirBuds 3'): ").strip()
    
    if not product_query:
        product_query = "Oraimo AirBuds 3"
        print(f"Using default: {product_query}")
    
    # Option for smart multi-search
    smart_search = input("\nUse smart multi-search? (y/n): ").lower()
    
    if smart_search == 'y':
        print("\n🧠 Executing smart multi-search...")
        all_results = query_builder.execute_multi_search(product_query)
        
        if all_results:
            print(f"\nFound {len(all_results)} results from multiple searches")
            
            # Combine and extract from all results
            combined_content = " ".join([r.get("content", "") for r in all_results])
            combined_title = " ".join([r.get("title", "") for r in all_results[:2]])
            
            # Use the extractor on combined results
            product_info = extractor._extract_info_from_results([{
                "content": combined_content,
                "title": combined_title
            }])
            
            poster_gen.product_info = product_info
            poster_gen._display_product_info()
    
    # Generate poster
    print(f"\n🎨 Generating product poster...")
    poster = poster_gen.generate_product_poster(product_query)
    
    if poster:
        # Show options
        print(f"\n✅ Poster generated successfully!")
        
        # Additional options
        export_json = input("\nExport product info as JSON? (y/n): ").lower()
        if export_json == 'y' and poster_gen.product_info:
            import json
            json_filename = f"product_info_{product_query.replace(' ', '_')}.json"
            with open(json_filename, 'w') as f:
                json.dump(poster_gen.product_info, f, indent=2)
            print(f"✅ Product info saved as: {json_filename}")
        
        # Show poster
        show_poster = input("\nShow generated poster? (y/n): ").lower()
        if show_poster == 'y':
            poster.show()

def test_extraction():
    """Test the extraction with sample data"""
    print("\n🧪 TESTING EXTRACTION WITH SAMPLE DATA")
    print("=" * 50)
    
    # Sample content from the provided JSON
    sample_content = """
    Oraimo AirBuds 3 Powerful Bass IPX7 Waterproof TWS True Wireless Earbuds, 
    Other Ear-Headphones Mobile Phones Buy for Ksh 5,000. 
    Features: 30-hour battery life, IPX7 waterproof, Bluetooth 5.3, 
    touch controls, and voice assistant support.
    """
    
    sample_title = "Oraimo AirBuds 3 Powerful Bass IPX7 Waterproof TWS True Wireless Earbuds"
    
    extractor = ProductInfoExtractor()
    
    # Test extraction functions
    print("Testing product name extraction...")
    name = extractor._extract_product_name(sample_title, sample_content)
    print(f"  Extracted: {name}")
    
    print("\nTesting price extraction...")
    prices = extractor._extract_prices(sample_content, sample_title)
    print(f"  Extracted prices: {prices}")
    
    print("\nTesting feature extraction...")
    features = extractor._extract_features(sample_content)
    print(f"  Extracted features: {list(features)[:5]}")
    
    print("\nTesting specification extraction...")
    specs = extractor._extract_specifications(sample_content)
    print(f"  Extracted specs: {list(specs)}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    # Run test first
    test_extraction()
    
    # Run main application
    main()