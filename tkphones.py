"""
Tripple K Marketing Suite - Professional AI-Powered Marketing Platform
Streamlined workflow with consistent branding and AI-generated elements.
"""

# ==========================================
# IMPORTS
# ==========================================
import streamlit as st
import requests
import re
import json
import time
import base64
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from io import BytesIO
from functools import wraps
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# Optional imports
try:
    import rembg
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# ==========================================
# CONFIGURATION & SETTINGS
# ==========================================

class Config:
    """Application configuration and constants"""
    
    # Brand Identity
    BRAND_NAME = "Tripple K Communications"
    BRAND_COLORS = {
        "maroon": "#8B0000",
        "gold": "#FFD700",
        "accent": "#FF6B35",
        "white": "#FFFFFF",
        "black": "#333333",
        "light_bg": "#F8F9FA",
        "dark_bg": "#1a1a1a"
    }
    
    # Contact Information
    CONTACT = {
        "phone": "+254700123456",
        "whatsapp": "+254700123456",
        "url": "https://www.tripplek.co.ke",
        "location": "CBD Opposite MKU Towers"
    }
    
    # Assets
    ASSETS = {
        "logo_url": "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107",
        "facebook_icon": "https://ik.imagekit.io/ericmwangi/facebook.png",
        "tiktok_icon": "https://ik.imagekit.io/ericmwangi/tiktok.png",
        "call_icon": "https://ik.imagekit.io/ericmwangi/call.png?updatedAt=1765804033399",
        "whatsapp_icon": "https://ik.imagekit.io/ericmwangi/whatsapp.png?updatedAt=1765797099945"
    }
    
    # API Configuration
    API_BASE = "https://tkphsp2.vercel.app"
    ENDPOINTS = {
        "search": "/gsm/search",
        "images": "/gsm/images",
        "info": "/gsm/info"
    }
    
    # Platform Information
    PLATFORMS = {
        "facebook": {"name": "Tripple K Communication", "icon": "facebook"},
        "tiktok": {"name": "Tripple K", "icon": "tiktok"},
        "whatsapp": {"name": "WhatsApp", "icon": "whatsapp"},
        "instagram": {"name": "Instagram", "icon": "tiktok"}  # Using tiktok icon as placeholder
    }
    
    # AI Configuration
    AI_CONFIG = {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.8,
        "max_tokens": 600
    }
    
    # App Settings
    APP = {
        "title": "Tripple K Phone Marketing Suite",
        "layout": "wide",
        "page_icon": "📱"
    }
    
    # Default Values
    DEFAULTS = {
        "price": "99,999",
        "badges": ["new_arrival", "official_warranty"],
        "cta": "SHOP NOW & GET FREE DELIVERY"
    }

# ==========================================
# CACHE & GLOBAL STATE MANAGEMENT
# ==========================================

class CacheManager:
    """Manages caching of images, fonts, and other assets"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cache()
        return cls._instance
    
    def _init_cache(self):
        """Initialize cache dictionaries"""
        self.images = {}
        self.fonts = {}
        self.icons = {}
        self.logo = None
    
    def get_image(self, url: str) -> Optional[Image.Image]:
        """Get image from cache or download"""
        if url in self.images:
            return self.images[url].copy()
        return None
    
    def set_image(self, url: str, image: Image.Image):
        """Store image in cache"""
        self.images[url] = image.copy()
    
    def get_font(self, platform: str, font_type: str) -> Optional[ImageFont.FreeTypeFont]:
        """Get font from cache"""
        key = f"{platform}_{font_type}"
        return self.fonts.get(key)
    
    def set_font(self, platform: str, font_type: str, font: ImageFont.FreeTypeFont):
        """Store font in cache"""
        key = f"{platform}_{font_type}"
        self.fonts[key] = font
    
    def clear(self):
        """Clear all caches"""
        self.images.clear()
        self.fonts.clear()
        self.icons.clear()
        self.logo = None

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

class Utils:
    """Collection of utility functions"""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def download_image(url: str) -> Optional[Image.Image]:
        """Download and cache image"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                return img
        except Exception as e:
            print(f"Download error for {url}: {str(e)}")
        return None
    
    @staticmethod
    def format_price(price_str: str) -> str:
        """Format price string with commas"""
        if not price_str:
            return "99,999"
        
        clean_price = re.sub(r'[^\d]', '', price_str)
        try:
            if clean_price:
                num = int(clean_price)
                return f"{num:,}"
        except:
            pass
        return "99,999"
    
    @staticmethod
    def retry_on_error(max_retries=3, delay=1):
        """Decorator for retrying functions on error"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise e
                        time.sleep(delay)
                return None
            return wrapper
        return decorator
    
    @staticmethod
    def copy_to_clipboard(text: str):
        """Copy text to clipboard using JavaScript"""
        js_code = f"""
        <script>
        navigator.clipboard.writeText(`{text}`).then(() => {{
            console.log('Copied to clipboard');
        }});
        </script>
        """
        st.components.v1.html(js_code, height=0)

# ==========================================
# PHONE DATA MANAGEMENT
# ==========================================

class PhoneManager:
    """Manages phone data fetching and processing"""
    
    def __init__(self):
        self.config = Config
        self.cache = CacheManager()
    
    @Utils.retry_on_error(max_retries=2)
    def search_phones(self, query: str) -> List[Dict[str, Any]]:
        """Search for phones in database"""
        try:
            url = f"{self.config.API_BASE}{self.config.ENDPOINTS['search']}"
            params = {"q": query}
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, params=params, timeout=10, headers=headers)
            
            if response.status_code == 200:
                results = response.json()
                return results or []
        except Exception as e:
            print(f"Search error: {e}")
        return []
    
    @Utils.retry_on_error(max_retries=2)
    def get_phone_details(self, phone_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed phone information"""
        try:
            url = f"{self.config.API_BASE}{self.config.ENDPOINTS['info']}/{phone_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, timeout=15, headers=headers)
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting phone details: {e}")
        return None
    
    @Utils.retry_on_error(max_retries=2)
    def get_phone_images(self, phone_id: str) -> List[str]:
        """Get phone images from API"""
        try:
            url = f"{self.config.API_BASE}{self.config.ENDPOINTS['images']}/{phone_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, timeout=15, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                images = []
                
                if isinstance(data, dict) and "images" in data:
                    images = data["images"]
                elif isinstance(data, list):
                    images = data
                
                # Filter valid image URLs
                valid_images = [img for img in images if isinstance(img, str) and img.startswith('http')]
                return valid_images[:8]
        except Exception as e:
            print(f"Error getting images for {phone_id}: {e}")
        return []
    
    def parse_specs(self, detailed_data: dict, search_data: dict) -> Dict[str, Any]:
        """Parse phone specifications from API response"""
        if not detailed_data:
            return self._parse_basic_specs(search_data)
        
        name = detailed_data.get("name", search_data.get("name", "Unknown Phone"))
        phone_id = search_data.get("id", "")
        image_url = search_data.get("image", "")
        
        # Extract all specs
        specs = self._extract_all_specs(detailed_data)
        
        return {
            "name": name,
            "id": phone_id,
            "image_url": image_url,
            "specs": specs,
            "detailed_data": detailed_data,
        }
    
    def _parse_basic_specs(self, phone_data: dict) -> Dict[str, Any]:
        """Parse basic specs from search result"""
        return {
            "name": phone_data.get("name", "Unknown Phone"),
            "id": phone_data.get("id", ""),
            "image_url": phone_data.get("image", ""),
            "specs": {
                "screen": "Check details",
                "camera": "Check details",
                "ram": "Check details",
                "storage": "Check details",
                "chipset": "Check details",
                "battery": "Check details",
            },
        }
    
    def _extract_all_specs(self, detailed_data: dict) -> Dict[str, str]:
        """Extract all specifications from detailed data"""
        specs = {
            "screen": "N/A",
            "camera": "N/A",
            "ram": "N/A",
            "storage": "N/A",
            "chipset": "N/A",
            "battery": "N/A",
        }
        
        # Screen size extraction
        display = detailed_data.get("display", {})
        screen_size = display.get("size", "")
        if screen_size:
            match = re.search(r'(\d+\.?\d*)\s*inches', screen_size, re.IGNORECASE)
            if match:
                specs["screen"] = f"{match.group(1)} inches"
        
        # Camera extraction
        main_camera = detailed_data.get("mainCamera", {})
        camera_specs = main_camera.get("modules", "")
        if camera_specs:
            mp_matches = re.findall(r'(\d+\.?\d*)\s*MP', camera_specs, re.IGNORECASE)
            if mp_matches:
                specs["camera"] = " + ".join(mp_matches[:2])
        
        # RAM and storage extraction
        memory_info = detailed_data.get("memory", {})
        if isinstance(memory_info, dict):
            internal = memory_info.get("internal", "")
            if internal:
                # Extract RAM
                ram_match = re.search(r'(\d+)\s*GB\s*RAM', internal, re.IGNORECASE)
                if ram_match:
                    specs["ram"] = f"{ram_match.group(1)}GB"
                
                # Extract storage
                storage_match = re.search(r'(\d+)\s*GB\s*(?:ROM|storage)', internal, re.IGNORECASE)
                if storage_match:
                    specs["storage"] = f"{storage_match.group(1)}GB"
        
        # Chipset
        platform = detailed_data.get("platform", {})
        chipset = platform.get("chipset", "")
        if chipset:
            specs["chipset"] = chipset
        
        # Battery
        battery_info = detailed_data.get("battery", {})
        battery = battery_info.get("type", battery_info.get("battType", ""))
        if battery:
            specs["battery"] = battery
        
        return specs

# ==========================================
# AI CONTENT GENERATION
# ==========================================

class AIContentGenerator:
    """Generates AI-powered marketing content"""
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or st.secrets.get("groq_key", "")
        if self.api_key:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
    
    def generate_marketing_package(self, phone_data: dict, price: str) -> Dict[str, Any]:
        """Generate complete marketing package including badges, hooks, and posts"""
        if not self.client:
            return self._generate_fallback_content(phone_data, price)
        
        try:
            # Prepare AI prompt
            prompt = self._create_ai_prompt(phone_data, price)
            
            # Call AI
            response = self.client.chat.completions.create(
                model=Config.AI_CONFIG["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=Config.AI_CONFIG["temperature"],
                max_tokens=Config.AI_CONFIG["max_tokens"]
            )
            
            if response.choices:
                # Parse AI response
                content_text = response.choices[0].message.content.strip()
                return self._parse_ai_response(content_text, phone_data, price)
        
        except Exception as e:
            print(f"AI Generation Error: {e}")
        
        return self._generate_fallback_content(phone_data, price)
    
    def _create_ai_prompt(self, phone_data: dict, price: str) -> str:
        """Create structured prompt for AI"""
        specs = phone_data.get("specs", {})
        formatted_price = Utils.format_price(price)
        
        prompt = f"""
        Create a complete marketing package for {phone_data['name']} for Tripple K Communications.
        
        PHONE DETAILS:
        Name: {phone_data['name']}
        Price: KES {formatted_price}
        Screen: {specs.get('screen', 'N/A')}
        Camera: {specs.get('camera', 'N/A')}
        RAM: {specs.get('ram', 'N/A')}
        Storage: {specs.get('storage', 'N/A')}
        Processor: {specs.get('chipset', 'N/A')}
        Battery: {specs.get('battery', 'N/A')}
        
        BRAND INFO:
        Name: {Config.BRAND_NAME}
        Location: {Config.CONTACT['location']}
        Phone: {Config.CONTACT['phone']}
        Website: {Config.CONTACT['url']}
        
        REQUIREMENTS:
        1. Generate 3 creative badges using our brand colors (Maroon: {Config.BRAND_COLORS['maroon']}, Gold: {Config.BRAND_COLORS['gold']}, Accent: {Config.BRAND_COLORS['accent']})
        2. Create compelling hooks for different platforms
        3. Write engaging social media posts
        4. Provide a strong call-to-action
        
        Return ONLY a JSON object with this exact structure:
        {{
          "badges": [
            {{"text": "Badge 1", "color": "#8B0000", "icon": "🔥"}},
            {{"text": "Badge 2", "color": "#FFD700", "icon": "⚡"}},
            {{"text": "Badge 3", "color": "#FF6B35", "icon": "🎯"}}
          ],
          "hooks": {{
            "main": "Main catchy headline",
            "facebook": "Facebook-specific hook",
            "instagram": "Instagram-specific hook",
            "whatsapp": "WhatsApp-specific hook"
          }},
          "cta": "Strong call-to-action text",
          "description": "2-3 sentence product description",
          "hashtags": "#TrippleK #PhoneDeals #Tech",
          "social_posts": {{
            "whatsapp": "Full WhatsApp post text...",
            "facebook": "Full Facebook post text...",
            "instagram": "Full Instagram post text..."
          }}
        }}
        """
        return prompt
    
    def _parse_ai_response(self, content_text: str, phone_data: dict, price: str) -> Dict[str, Any]:
        """Parse AI response and ensure structure"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
            if json_match:
                content = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in AI response")
            
            # Validate and complete structure
            content = self._validate_content_structure(content, phone_data, price)
            return content
            
        except Exception as e:
            print(f"AI Response parsing error: {e}")
            return self._generate_fallback_content(phone_data, price)
    
    def _validate_content_structure(self, content: dict, phone_data: dict, price: str) -> dict:
        """Ensure content has all required fields"""
        formatted_price = Utils.format_price(price)
        
        # Default structure
        default = {
            "badges": [
                {"text": "NEW ARRIVAL", "color": Config.BRAND_COLORS["accent"], "icon": "🆕"},
                {"text": "OFFICIAL WARRANTY", "color": Config.BRAND_COLORS["maroon"], "icon": "✅"},
                {"text": "FREE DELIVERY", "color": Config.BRAND_COLORS["gold"], "icon": "🚚"}
            ],
            "hooks": {
                "main": f"🚀 {phone_data['name']} - NOW AVAILABLE!",
                "facebook": f"{phone_data['name']} - Premium Quality at Tripple K",
                "instagram": f"🔥 {phone_data['name']} JUST DROPPED!",
                "whatsapp": f"📱 {phone_data['name']} Available Now!"
            },
            "cta": "SHOP NOW & GET FREE DELIVERY",
            "description": f"Experience the amazing {phone_data['name']} at {Config.BRAND_NAME}! Premium quality with official warranty.",
            "hashtags": f"#{Config.BRAND_NAME.replace(' ', '')} #PhoneDeals #Smartphones #TechKenya",
            "social_posts": {
                "whatsapp": f"📱 *{phone_data['name']}*\n\nAvailable at {Config.BRAND_NAME}!\n💰 KES {formatted_price}\n📍 {Config.CONTACT['location']}\n📞 {Config.CONTACT['phone']}",
                "facebook": f"{phone_data['name']}\n\nNow available at {Config.BRAND_NAME}! Premium features at amazing prices.\n\n📍 {Config.CONTACT['location']}\n📞 {Config.CONTACT['phone']}",
                "instagram": f"🔥 {phone_data['name']}\n💸 KES {formatted_price}\n📍 {Config.CONTACT['location']}\n📞 {Config.CONTACT['phone']}"
            }
        }
        
        # Merge AI content with defaults
        for key in default:
            if key not in content or not content[key]:
                content[key] = default[key]
            elif key == "badges":
                # Ensure badges have proper structure
                for i, badge in enumerate(content[key]):
                    if not isinstance(badge, dict):
                        content[key][i] = default["badges"][i] if i < len(default["badges"]) else default["badges"][0]
                    else:
                        # Validate badge structure
                        if "color" not in badge or not badge["color"]:
                            # Assign color based on position
                            color_keys = ["maroon", "gold", "accent"]
                            if i < len(color_keys):
                                badge["color"] = Config.BRAND_COLORS[color_keys[i]]
                            else:
                                badge["color"] = Config.BRAND_COLORS["maroon"]
        
        return content
    
    def _generate_fallback_content(self, phone_data: dict, price: str) -> Dict[str, Any]:
        """Generate fallback content when AI is unavailable"""
        formatted_price = Utils.format_price(price)
        
        return {
            "badges": [
                {"text": "NEW ARRIVAL", "color": Config.BRAND_COLORS["accent"], "icon": "🆕"},
                {"text": "OFFICIAL WARRANTY", "color": Config.BRAND_COLORS["maroon"], "icon": "✅"},
                {"text": "FREE DELIVERY", "color": Config.BRAND_COLORS["gold"], "icon": "🚚"}
            ],
            "hooks": {
                "main": f"🚀 {phone_data['name']} - NOW AVAILABLE!",
                "facebook": f"{phone_data['name']} - Premium Quality at Tripple K",
                "instagram": f"🔥 {phone_data['name']} JUST DROPPED!",
                "whatsapp": f"📱 {phone_data['name']} Available Now!"
            },
            "cta": "SHOP NOW & GET FREE DELIVERY",
            "description": f"Experience the amazing {phone_data['name']} at {Config.BRAND_NAME}! Premium quality with official warranty.",
            "hashtags": f"#{Config.BRAND_NAME.replace(' ', '')} #PhoneDeals #Smartphones #TechKenya",
            "social_posts": {
                "whatsapp": f"📱 *{phone_data['name']}*\n\nAvailable at {Config.BRAND_NAME}!\n💰 KES {formatted_price}\n📍 {Config.CONTACT['location']}\n📞 {Config.CONTACT['phone']}",
                "facebook": f"{phone_data['name']}\n\nNow available at {Config.BRAND_NAME}! Premium features at amazing prices.\n\n📍 {Config.CONTACT['location']}\n📞 {Config.CONTACT['phone']}",
                "instagram": f"🔥 {phone_data['name']}\n💸 KES {formatted_price}\n📍 {Config.CONTACT['location']}\n📞 {Config.CONTACT['phone']}"
            }
        }

# ==========================================
# AD GENERATION & LAYOUTS
# ==========================================

class AdLayouts:
    """Defines ad layouts for different platforms"""
    
    LAYOUTS = {
        "facebook": {
            "size": (1200, 1200),
            "background": Config.BRAND_COLORS["maroon"],
            "regions": {
                "logo": {"x": 40, "y": 30, "width": 200, "height": 70},
                "badges": {"x": 300, "y": 40, "width": 860, "height": 50},
                "hook": {"x": 50, "y": 120, "width": 1100, "height": 80},
                "phone": {"x": 100, "y": 220, "width": 450, "height": 500},
                "content": {"x": 600, "y": 220, "width": 500, "height": 450},
                "price": {"x": 600, "y": 690, "width": 500, "height": 70},
                "cta": {"x": 600, "y": 780, "width": 180, "height": 60},
                "contact": {"x": 800, "y": 780, "width": 300, "height": 60},
                "footer": {"x": 50, "y": 880, "width": 1100, "height": 280},
            }
        },
        "instagram": {
            "size": (1080, 1350),
            "background": Config.BRAND_COLORS["maroon"],
            "regions": {
                "logo": {"x": 440, "y": 30, "width": 200, "height": 70},
                "badges": {"x": 100, "y": 120, "width": 880, "height": 50},
                "hook": {"x": 100, "y": 190, "width": 880, "height": 70},
                "phone": {"x": 140, "y": 280, "width": 800, "height": 500},
                "content": {"x": 100, "y": 800, "width": 880, "height": 300},
                "price": {"x": 100, "y": 1120, "width": 880, "height": 70},
                "cta": {"x": 100, "y": 1210, "width": 150, "height": 60},
                "contact": {"x": 270, "y": 1210, "width": 200, "height": 60},
                "footer": {"x": 100, "y": 1290, "width": 880, "height": 40},
            }
        },
        "whatsapp": {
            "size": (1080, 1920),
            "background": Config.BRAND_COLORS["white"],
            "regions": {
                "logo": {"x": 40, "y": 30, "width": 200, "height": 70},
                "badges": {"x": 300, "y": 40, "width": 740, "height": 50},
                "hook": {"x": 50, "y": 120, "width": 980, "height": 80},
                "phone": {"x": 140, "y": 220, "width": 800, "height": 700},
                "content": {"x": 100, "y": 940, "width": 880, "height": 400},
                "price": {"x": 100, "y": 1360, "width": 880, "height": 80},
                "cta": {"x": 100, "y": 1460, "width": 400, "height": 70},
                "contact": {"x": 520, "y": 1460, "width": 460, "height": 70},
                "footer": {"x": 100, "y": 1550, "width": 880, "height": 320},
            }
        }
    }

class AdGenerator:
    """Generates visual ads for different platforms"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.layout = AdLayouts.LAYOUTS[platform]
        self.width, self.height = self.layout["size"]
        self.cache = CacheManager()
        self.utils = Utils()
        self._load_fonts()
    
    def _load_fonts(self):
        """Load and cache fonts"""
        font_paths = [
            "assets/fonts/poppins.ttf",
            "poppins.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        font_path = None
        for path in font_paths:
            try:
                ImageFont.truetype(path, 12)
                font_path = path
                break
            except:
                continue
        
        if font_path is None:
            default = ImageFont.load_default()
            fonts = {
                "title": default,
                "subtitle": default,
                "body": default,
                "small": default,
                "price": default,
                "hook": default
            }
        else:
            try:
                fonts = {
                    "title": ImageFont.truetype(font_path, 44 if self.platform == "facebook" else 36),
                    "subtitle": ImageFont.truetype(font_path, 30 if self.platform == "facebook" else 26),
                    "body": ImageFont.truetype(font_path, 24 if self.platform == "facebook" else 20),
                    "small": ImageFont.truetype(font_path, 18 if self.platform == "facebook" else 16),
                    "price": ImageFont.truetype(font_path, 42 if self.platform == "facebook" else 36),
                    "hook": ImageFont.truetype(font_path, 48 if self.platform == "facebook" else 38)
                }
            except:
                default = ImageFont.load_default()
                fonts = {
                    "title": default,
                    "subtitle": default,
                    "body": default,
                    "small": default,
                    "price": default,
                    "hook": default
                }
        
        self.fonts = fonts
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def generate(self, phone_data: dict, image_url: str, content: dict, price: str) -> Image.Image:
        """Generate complete ad image"""
        # Create base image
        img = self._create_base_image()
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Draw all components
        self._draw_logo(img)
        self._draw_badges(img, draw, content.get("badges", []))
        self._draw_hook(img, draw, content.get("hooks", {}).get(self.platform, ""))
        self._draw_phone_image(img, image_url)
        self._draw_content(img, draw, phone_data)
        self._draw_price(img, draw, price)
        self._draw_cta(img, draw, content.get("cta", ""))
        self._draw_contact_info(img, draw)
        self._draw_footer(img, draw, content.get("hashtags", ""))
        
        return img
    
    def _create_base_image(self) -> Image.Image:
        """Create base image with gradient background"""
        base_color = self._hex_to_rgb(self.layout["background"])
        img = Image.new('RGB', (self.width, self.height), base_color)
        
        if self.platform in ["facebook", "instagram"]:
            draw = ImageDraw.Draw(img)
            for y in range(self.height):
                factor = 0.7 + 0.3 * (y / self.height)
                color = tuple(int(c * factor) for c in base_color)
                draw.line([(0, y), (self.width, y)], fill=color)
        
        return img
    
    def _draw_logo(self, img: Image.Image):
        """Draw brand logo"""
        region = self.layout["regions"]["logo"]
        
        # Get or download logo
        if self.cache.logo is None:
            logo_img = Utils.download_image(Config.ASSETS["logo_url"])
            if logo_img:
                # Process logo
                if logo_img.mode != 'RGBA':
                    logo_img = logo_img.convert('RGBA')
                logo_img = logo_img.resize((200, 70), Image.Resampling.LANCZOS)
                self.cache.logo = logo_img
        
        if self.cache.logo:
            logo_img = self.cache.logo
            x = region["x"] + (region["width"] - logo_img.width) // 2
            y = region["y"] + (region["height"] - logo_img.height) // 2
            img.paste(logo_img, (x, y), logo_img)
    
    def _draw_badges(self, img: Image.Image, draw: ImageDraw.ImageDraw, badges: List[dict]):
        """Draw AI-generated badges"""
        if not badges:
            return
        
        region = self.layout["regions"]["badges"]
        x, y = region["x"], region["y"]
        max_width = region["width"]
        
        # Calculate positions
        badge_widths = []
        badge_height = 45
        badge_spacing = 15
        
        for badge in badges[:3]:  # Max 3 badges
            text = f"{badge.get('icon', '')} {badge.get('text', '')}"
            bbox = draw.textbbox((0, 0), text, font=self.fonts["small"])
            text_width = bbox[2] - bbox[0] + 25
            badge_widths.append(text_width)
        
        # Center badges
        total_width = sum(badge_widths) + (len(badge_widths) - 1) * badge_spacing
        current_x = x + (max_width - total_width) // 2
        
        # Draw each badge
        for i, badge in enumerate(badges[:3]):
            text = f"{badge.get('icon', '')} {badge.get('text', '')}"
            text_width = badge_widths[i]
            color = self._hex_to_rgb(badge.get("color", Config.BRAND_COLORS["maroon"]))
            
            # Draw badge background
            draw.rounded_rectangle(
                [current_x, y, current_x + text_width, y + badge_height],
                radius=badge_height // 2,
                fill=color
            )
            
            # Draw badge text
            bbox = draw.textbbox((0, 0), text, font=self.fonts["small"])
            text_y = y + (badge_height - (bbox[3] - bbox[1])) // 2
            draw.text(
                (current_x + 12, text_y),
                text,
                fill=Config.BRAND_COLORS["white"],
                font=self.fonts["small"]
            )
            
            current_x += text_width + badge_spacing
    
    def _draw_hook(self, img: Image.Image, draw: ImageDraw.ImageDraw, hook: str):
        """Draw the main hook/headline"""
        if not hook:
            return
        
        region = self.layout["regions"]["hook"]
        x, y = region["x"], region["y"]
        max_width = region["width"]
        
        # Hook color
        hook_color = Config.BRAND_COLORS["gold"] if self.platform in ["facebook", "instagram"] else Config.BRAND_COLORS["maroon"]
        
        # Wrap text
        words = hook.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=self.fonts["hook"])
            if bbox[2] - bbox[0] <= max_width - 40:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw hook lines
        for i, line in enumerate(lines[:2]):  # Max 2 lines
            line_y = y + i * (self.fonts["hook"].size + 10)
            draw.text((x, line_y), line, fill=hook_color, font=self.fonts["hook"])
    
    def _draw_phone_image(self, img: Image.Image, image_url: str):
        """Draw phone image with proper styling"""
        if not image_url:
            return
        
        region = self.layout["regions"]["phone"]
        phone_img = Utils.download_image(image_url)
        
        if phone_img:
            # Resize maintaining aspect ratio
            original_width, original_height = phone_img.size
            target_width, target_height = region["width"], region["height"]
            
            width_ratio = target_width / original_width
            height_ratio = target_height / original_height
            scale = min(width_ratio, height_ratio) * 0.85
            
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            phone_img = phone_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGBA for transparency
            if phone_img.mode != 'RGBA':
                phone_img = phone_img.convert('RGBA')
            
            # Center image
            x = region["x"] + (region["width"] - new_width) // 2
            y = region["y"] + (region["height"] - new_height) // 2
            
            # Create white background with subtle shadow
            bg = Image.new('RGBA', (new_width + 20, new_height + 20), (255, 255, 255, 255))
            img.paste(bg, (x - 10, y - 10), bg)
            
            # Paste phone image
            img.paste(phone_img, (x, y), phone_img)
    
    def _draw_content(self, img: Image.Image, draw: ImageDraw.ImageDraw, phone_data: dict):
        """Draw phone specifications"""
        region = self.layout["regions"]["content"]
        x, y = region["x"], region["y"]
        max_width = region["width"]
        
        text_color = Config.BRAND_COLORS["white"] if self.platform in ["facebook", "instagram"] else Config.BRAND_COLORS["black"]
        accent_color = Config.BRAND_COLORS["gold"]
        
        # Phone name
        phone_name = phone_data["name"]
        bbox = draw.textbbox((0, 0), phone_name, font=self.fonts["subtitle"])
        if bbox[2] - bbox[0] > max_width:
            # Truncate if too long
            phone_name = phone_name[:30] + "..."
        
        draw.text((x, y), phone_name, fill=text_color, font=self.fonts["subtitle"])
        y += self.fonts["subtitle"].size + 20
        
        # Key specs
        specs = [
            ("🖥️", "Screen", phone_data["specs"].get("screen", "N/A")),
            ("📸", "Camera", phone_data["specs"].get("camera", "N/A")),
            ("🚀", "Processor", phone_data["specs"].get("chipset", "N/A")),
            ("⚡", "RAM", phone_data["specs"].get("ram", "N/A")),
            ("💾", "Storage", phone_data["specs"].get("storage", "N/A")),
            ("🔋", "Battery", phone_data["specs"].get("battery", "N/A")),
        ]
        
        for icon, label, value in specs[:4]:  # Show max 4 specs
            if value != "N/A" and value != "Check details":
                spec_text = f"{label}: {value}"
                draw.text((x, y), icon, fill=accent_color, font=self.fonts["body"])
                draw.text((x + 40, y), spec_text, fill=text_color, font=self.fonts["body"])
                y += self.fonts["body"].size + 15
    
    def _draw_price(self, img: Image.Image, draw: ImageDraw.ImageDraw, price: str):
        """Draw price prominently"""
        region = self.layout["regions"]["price"]
        x, y = region["x"], region["y"]
        width, height = region["width"], region["height"]
        
        formatted_price = Utils.format_price(price)
        price_text = f"KES {formatted_price}"
        
        # Calculate text size
        bbox = draw.textbbox((0, 0), price_text, font=self.fonts["price"])
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Create price badge
        badge_x = x + (width - text_width - 40) // 2
        badge_y = y + (height - 50) // 2
        
        # Background
        price_bg = Config.BRAND_COLORS["gold"] if self.platform in ["facebook", "instagram"] else Config.BRAND_COLORS["maroon"]
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + text_width + 40, badge_y + 50],
            radius=25,
            fill=self._hex_to_rgb(price_bg)
        )
        
        # Text
        text_color = Config.BRAND_COLORS["maroon"] if self.platform in ["facebook", "instagram"] else Config.BRAND_COLORS["white"]
        draw.text(
            (badge_x + 20, badge_y + (50 - text_height) // 2),
            price_text,
            fill=text_color,
            font=self.fonts["price"]
        )
    
    def _draw_cta(self, img: Image.Image, draw: ImageDraw.ImageDraw, cta: str):
        """Draw call-to-action button"""
        region = self.layout["regions"]["cta"]
        x, y = region["x"], region["y"]
        width, height = region["width"], region["height"]
        
        button_text = cta or "SHOP NOW"
        
        # Button background
        for by in range(height):
            factor = 0.9 + 0.2 * (by / height)
            r = int(255 * factor)
            g = int(215 * factor)
            b = int(0 * factor)
            draw.rectangle(
                [x, y + by, x + width, y + by + 1],
                fill=(r, g, b)
            )
        
        # Button text
        bbox = draw.textbbox((0, 0), button_text, font=self.fonts["subtitle"])
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2
        
        draw.text(
            (text_x, text_y),
            button_text,
            fill=self._hex_to_rgb(Config.BRAND_COLORS["maroon"]),
            font=self.fonts["subtitle"]
        )
    
    def _draw_contact_info(self, img: Image.Image, draw: ImageDraw.ImageDraw):
        """Draw contact information"""
        region = self.layout["regions"]["contact"]
        x, y = region["x"], region["y"]
        
        text_color = Config.BRAND_COLORS["maroon"]
        
        # Draw contact info
        contact_text = f"📞 {Config.CONTACT['phone']}  •  💬 {Config.CONTACT['whatsapp']}"
        draw.text((x, y + 15), contact_text, fill=text_color, font=self.fonts["small"])
    
    def _draw_footer(self, img: Image.Image, draw: ImageDraw.ImageDraw, hashtags: str):
        """Draw footer with location and hashtags"""
        region = self.layout["regions"]["footer"]
        x, y = region["x"], region["y"]
        width = region["width"]
        
        text_color = Config.BRAND_COLORS["white"] if self.platform in ["facebook", "instagram"] else Config.BRAND_COLORS["black"]
        accent_color = Config.BRAND_COLORS["gold"] if self.platform in ["facebook", "instagram"] else Config.BRAND_COLORS["maroon"]
        
        # Location
        location_text = f"📍 {Config.CONTACT['location']}"
        bbox = draw.textbbox((0, 0), location_text, font=self.fonts["small"])
        location_width = bbox[2] - bbox[0]
        draw.text((x, y), location_text, fill=text_color, font=self.fonts["small"])
        
        # Website
        website_text = f"🌐 {Config.CONTACT['url']}"
        draw.text((x + location_width + 40, y), website_text, fill=text_color, font=self.fonts["small"])
        
        # Hashtags
        if hashtags:
            hashtag_y = y + region["height"] - 25
            hashtag_lines = hashtags.split('\n')
            for line in hashtag_lines[:1]:  # Max 1 line
                if line.strip():
                    draw.text((x, hashtag_y), line.strip(), fill=accent_color, font=self.fonts["small"])

# ==========================================
# STREAMLIT UI COMPONENTS
# ==========================================

class UIComponents:
    """Reusable UI components for Streamlit"""
    
    @staticmethod
    def setup_page():
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title=Config.APP["title"],
            layout=Config.APP["layout"],
            page_icon=Config.APP["page_icon"]
        )
        
        # Apply custom CSS
        UIComponents._apply_styles()
    
    @staticmethod
    def _apply_styles():
        """Apply custom CSS styles"""
        st.markdown(f"""
        <style>
        * {{
            font-family: 'Poppins', sans-serif;
        }}
        
        .main {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
        }}
        
        .header-box {{
            background: linear-gradient(135deg, {Config.BRAND_COLORS['maroon']} 0%, #6b0000 100%);
            padding: 2.5rem;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin-bottom: 2.5rem;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            border: 3px solid {Config.BRAND_COLORS['gold']};
        }}
        
        .specs-container {{
            background: white;
            border-radius: 15px;
            padding: 1.8rem;
            box-shadow: 0 6px 20px rgba(0,0,0,0.08);
            margin: 1.2rem 0;
            border: 2px solid #e0e0e0;
        }}
        
        .spec-item {{
            display: flex;
            align-items: center;
            padding: 1rem;
            margin: 0.6rem 0;
            border-radius: 10px;
            border-left: 5px solid {Config.BRAND_COLORS['maroon']};
            background: linear-gradient(90deg, #f8f9fa 0%, white 100%);
        }}
        
        .price-display {{
            background: linear-gradient(135deg, {Config.BRAND_COLORS['gold']} 0%, #ffc400 100%);
            color: {Config.BRAND_COLORS['maroon']};
            padding: 1rem 1.5rem;
            border-radius: 12px;
            font-weight: 900;
            font-size: 1.4rem;
            text-align: center;
            margin: 0.8rem 0;
            box-shadow: 0 6px 18px rgba(255, 215, 0, 0.2);
        }}
        
        .social-post {{
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin: 1.5rem 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            border-left: 6px solid {Config.BRAND_COLORS['maroon']};
        }}
        
        .stButton>button {{
            background: linear-gradient(135deg, {Config.BRAND_COLORS['maroon']} 0%, #9a0000 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 12px;
            font-weight: 700;
            transition: all 0.3s;
            box-shadow: 0 6px 18px rgba(139, 0, 0, 0.25);
        }}
        
        .stButton>button:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(139, 0, 0, 0.4);
        }}
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_header():
        """Render application header"""
        st.markdown('<div class="header-box">', unsafe_allow_html=True)
        st.markdown('<h1 style="margin:0; font-size: 2.8rem;">📱 Tripple K Phone Marketing Suite</h1>', unsafe_allow_html=True)
        st.markdown('<p style="margin:0.5rem 0 0 0; opacity:0.9; font-size: 1.2rem;">AI-Powered Professional Marketing Platform</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def render_phone_specs(phone_data: dict):
        """Render phone specifications in a nice format"""
        st.markdown('<div class="specs-container">', unsafe_allow_html=True)
        st.markdown("### 📋 Key Specifications")
        
        display_specs = [
            ("🖥️ Screen", phone_data["specs"].get('screen', 'N/A')),
            ("📸 Camera", phone_data["specs"].get('camera', 'N/A')),
            ("🚀 Processor", phone_data["specs"].get('chipset', 'N/A')),
            ("⚡ RAM", phone_data["specs"].get('ram', 'N/A')),
            ("💾 Storage", phone_data["specs"].get('storage', 'N/A')),
            ("🔋 Battery", phone_data["specs"].get('battery', 'N/A')),
        ]
        
        for label, value in display_specs:
            if value != "N/A" and value != "Check details":
                st.markdown(f'''
                <div class="spec-item">
                    <span style="font-weight: 800; color: {Config.BRAND_COLORS['maroon']}; min-width: 120px;">{label}:</span>
                    <span style="color: #333; font-weight: 500;">{value}</span>
                </div>
                ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def render_price_display(price: str):
        """Render price in a prominent display"""
        formatted_price = Utils.format_price(price)
        st.markdown(f'<div class="price-display">KES {formatted_price}</div>', unsafe_allow_html=True)
    
    @staticmethod
    def render_social_post(platform: str, content: str):
        """Render a social media post in a styled box"""
        platform_icons = {
            "whatsapp": "💬",
            "facebook": "👤",
            "instagram": "📸",
            "tiktok": "🎵"
        }
        
        icon = platform_icons.get(platform, "📱")
        st.markdown('<div class="social-post">', unsafe_allow_html=True)
        st.markdown(f'### {icon} {platform.capitalize()} Post')
        st.code(content, language=None)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MAIN APPLICATION
# ==========================================

class MarketingSuiteApp:
    """Main application class"""
    
    def __init__(self):
        self.phone_manager = PhoneManager()
        self.ai_generator = AIContentGenerator()
        self.ui = UIComponents()
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize Streamlit session state"""
        if "current_phone" not in st.session_state:
            st.session_state.current_phone = None
        if "phone_images" not in st.session_state:
            st.session_state.phone_images = []
        if "selected_image_index" not in st.session_state:
            st.session_state.selected_image_index = 0
        if "phone_price" not in st.session_state:
            st.session_state.phone_price = Config.DEFAULTS["price"]
        if "marketing_content" not in st.session_state:
            st.session_state.marketing_content = None
        if "search_results" not in st.session_state:
            st.session_state.search_results = []
    
    def run(self):
        """Run the main application"""
        # Setup page
        self.ui.setup_page()
        self.ui.render_header()
        
        # Simple workflow: Find Phone -> Generate Marketing
        tabs = st.tabs(["🔍 Find Phone", "🚀 Generate Marketing"])
        
        with tabs[0]:
            self._render_find_phone_tab()
        
        with tabs[1]:
            self._render_generate_marketing_tab()
        
        # Footer
        self._render_footer()
    
    def _render_find_phone_tab(self):
        """Render phone search and selection tab"""
        st.markdown("### 🔍 Find Your Phone")
        
        # Search input
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("", placeholder="Search phone (e.g., iPhone 14, Samsung S23)")
        with col2:
            if st.button("🔍 Search", type="primary", use_container_width=True):
                if query:
                    self._handle_phone_search(query)
                else:
                    st.warning("Please enter a search term")
        
        # Display search results
        if st.session_state.search_results:
            self._display_search_results()
        
        # Display selected phone details
        if st.session_state.current_phone:
            self._display_phone_details()
    
    def _handle_phone_search(self, query: str):
        """Handle phone search"""
        with st.spinner("Searching..."):
            results = self.phone_manager.search_phones(query)
            if results:
                st.session_state.search_results = results
                st.success(f"Found {len(results)} phones")
                st.rerun()
            else:
                st.error("No phones found. Try a different search term.")
    
    def _display_search_results(self):
        """Display phone search results"""
        st.markdown("### 📱 Select a Phone")
        
        results = st.session_state.search_results
        phone_names = [phone.get("name", "Unknown Phone") for phone in results]
        
        selected_phone_name = st.selectbox(
            "Choose a phone:",
            options=phone_names,
            key="phone_selector"
        )
        
        selected_idx = next((i for i, phone in enumerate(results) if phone.get("name") == selected_phone_name), -1)
        
        if selected_idx != -1:
            if st.button("📥 Load Phone Details", type="secondary"):
                self._load_phone_details(results[selected_idx])
    
    def _load_phone_details(self, phone_data: dict):
        """Load detailed phone information"""
        with st.spinner("Loading phone details..."):
            phone_id = phone_data.get("id", "")
            
            # Get detailed info
            detailed_info = self.phone_manager.get_phone_details(phone_id)
            
            if detailed_info:
                # Parse specs
                phone_info = self.phone_manager.parse_specs(detailed_info, phone_data)
                st.session_state.current_phone = phone_info
                
                # Get images
                image_id = phone_id.replace("-", "-pictures-") if "-" in phone_id else phone_id
                images = self.phone_manager.get_phone_images(image_id)
                
                # Add main image
                if phone_data.get("image") and phone_data.get("image") not in images:
                    images.insert(0, phone_data.get("image"))
                
                st.session_state.phone_images = images
                st.session_state.selected_image_index = 0
                st.session_state.marketing_content = None  # Clear previous content
                
                st.success(f"✅ {phone_info['name']} loaded successfully!")
                st.rerun()
            else:
                st.error("Could not load phone details")
    
    def _display_phone_details(self):
        """Display selected phone details"""
        phone_data = st.session_state.current_phone
        
        st.markdown(f"## 📱 {phone_data['name']}")
        
        col_img, col_specs = st.columns([1, 1])
        
        with col_img:
            st.markdown("### 📸 Phone Images")
            images = st.session_state.phone_images
            
            if images:
                # Show selected image
                selected_idx = st.session_state.selected_image_index
                if selected_idx < len(images):
                    img = Utils.download_image(images[selected_idx])
                    if img:
                        st.image(img, use_container_width=True)
                
                # Image selector
                if len(images) > 1:
                    st.selectbox(
                        "Select image:",
                        options=[f"Image {i+1}" for i in range(len(images))],
                        index=selected_idx,
                        key="image_selector",
                        on_change=lambda: self._update_image_index()
                    )
            else:
                st.info("No images available")
        
        with col_specs:
            # Display specs
            self.ui.render_phone_specs(phone_data)
            
            # Price input
            st.markdown("### 💰 Set Price")
            price = st.text_input(
                "Enter price:",
                value=st.session_state.phone_price,
                placeholder="e.g., 45,999",
                key="price_input"
            )
            
            if st.button("💾 Save Price", type="primary"):
                if price:
                    st.session_state.phone_price = price
                    st.success(f"Price set to KES {Utils.format_price(price)}")
                    st.rerun()
                else:
                    st.warning("Please enter a valid price")
            
            # Show current price
            if st.session_state.phone_price:
                self.ui.render_price_display(st.session_state.phone_price)
    
    def _update_image_index(self):
        """Update selected image index"""
        selected_label = st.session_state.image_selector
        if selected_label and "Image " in selected_label:
            idx = int(selected_label.split(" ")[1]) - 1
            st.session_state.selected_image_index = idx
    
    def _render_generate_marketing_tab(self):
        """Render marketing generation tab"""
        if not st.session_state.current_phone:
            st.info("👈 First select a phone from the Find Phone tab")
            return
        
        phone_data = st.session_state.current_phone
        
        st.markdown(f"### 🚀 Generate Marketing for {phone_data['name']}")
        
        # Price confirmation
        formatted_price = Utils.format_price(st.session_state.phone_price)
        st.markdown(f"**Price:** KES {formatted_price}")
        
        # Image selection for ads
        images = st.session_state.phone_images
        selected_image = None
        
        if images:
            selected_idx = st.session_state.selected_image_index
            if selected_idx < len(images):
                selected_image = images[selected_idx]
                st.markdown(f"**Using Image {selected_idx + 1} for ads**")
        
        # Generate button
        if st.button("✨ Generate Complete Marketing Package", type="primary", use_container_width=True):
            self._generate_marketing_package(phone_data, selected_image)
        
        # Display generated content
        if st.session_state.marketing_content:
            self._display_marketing_results(phone_data, selected_image)
    
    def _generate_marketing_package(self, phone_data: dict, image_url: str):
        """Generate complete marketing package"""
        with st.spinner("🤖 Generating AI-powered marketing content..."):
            # Generate AI content
            content = self.ai_generator.generate_marketing_package(
                phone_data, 
                st.session_state.phone_price
            )
            
            if content:
                st.session_state.marketing_content = content
                st.balloons()
                st.success("✅ Marketing package generated successfully!")
                st.rerun()
    
    def _display_marketing_results(self, phone_data: dict, image_url: str):
        """Display generated marketing content"""
        content = st.session_state.marketing_content
        
        # Show AI-generated badges
        st.markdown("### 🏷️ AI-Generated Badges")
        cols = st.columns(3)
        for i, badge in enumerate(content.get("badges", [])[:3]):
            with cols[i]:
                badge_color = badge.get("color", Config.BRAND_COLORS["maroon"])
                st.markdown(f'<div style="background-color: {badge_color}; color: white; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold;">{badge.get("icon", "")} {badge.get("text", "")}</div>', unsafe_allow_html=True)
        
        # Show hooks
        st.markdown("### 🎯 Hooks")
        hooks = content.get("hooks", {})
        for platform, hook in hooks.items():
            st.markdown(f"**{platform.capitalize()}:** {hook}")
        
        # Social Media Posts
        st.markdown("### 📱 Social Media Posts")
        
        social_posts = content.get("social_posts", {})
        for platform, post in social_posts.items():
            self.ui.render_social_post(platform, post)
            
            # Copy and download buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"📋 Copy {platform.capitalize()} Post", key=f"copy_{platform}"):
                    Utils.copy_to_clipboard(post)
            with col2:
                st.download_button(
                    label=f"📥 Download {platform.capitalize()}",
                    data=post,
                    file_name=f"{phone_data['name'].replace(' ', '_')}_{platform}_post.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        # Generate Visual Ads
        st.markdown("### 🎨 Visual Ads")
        
        platforms = ["facebook", "instagram", "whatsapp"]
        for platform in platforms:
            st.markdown(f"#### {platform.capitalize()} Ad")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"Generate {platform.capitalize()} Ad", key=f"gen_{platform}"):
                    with st.spinner(f"Creating {platform} ad..."):
                        self._generate_ad(platform, phone_data, image_url, content)
            
            # Display generated ad if exists
            ad_key = f"{platform}_ad"
            if ad_key in st.session_state:
                st.image(st.session_state[ad_key], use_container_width=True)
                
                # Download button for ad
                buf = BytesIO()
                st.session_state[ad_key].save(buf, format='PNG', quality=95)
                safe_name = phone_data['name'].replace(' ', '_')
                filename = f"tripplek_{safe_name}_{platform}_ad.png"
                
                st.download_button(
                    label=f"📥 Download {platform.capitalize()} Ad",
                    data=buf.getvalue(),
                    file_name=filename,
                    mime="image/png",
                    use_container_width=True
                )
    
    def _generate_ad(self, platform: str, phone_data: dict, image_url: str, content: dict):
        """Generate visual ad for platform"""
        try:
            generator = AdGenerator(platform)
            ad_image = generator.generate(
                phone_data=phone_data,
                image_url=image_url,
                content=content,
                price=st.session_state.phone_price
            )
            
            # Store in session state
            st.session_state[f"{platform}_ad"] = ad_image
            st.rerun()
            
        except Exception as e:
            st.error(f"Error generating ad: {str(e)}")
    
    def _render_footer(self):
        """Render application footer"""
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; color: {Config.BRAND_COLORS['maroon']}; padding: 1.5rem;">
            <h4>{Config.BRAND_NAME}</h4>
            <p>📞 {Config.CONTACT['phone']} | 💬 {Config.CONTACT['whatsapp']} | 🌐 {Config.CONTACT['url']}</p>
            <p>📍 {Config.CONTACT['location']}</p>
            <p style="font-size: 0.9em; color: #666;">Marketing Suite v7.0 | AI-Powered Platform</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

def main():
    """Main entry point"""
    app = MarketingSuiteApp()
    app.run()

if __name__ == "__main__":
    main()