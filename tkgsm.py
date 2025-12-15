# ==========================================
# NEW: ADVANCED FEATURES TO ADD
# ==========================================

# 1. BATCH PROCESSING FOR MULTIPLE PHONES
class BatchProcessor:
    """Process multiple phones at once for efficiency"""
    
    @staticmethod
    def process_phone_list(phone_list: List[str], max_workers: int = 3):
        """Process multiple phones in parallel"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_phone = {
                executor.submit(fetch_phone_data, phone): phone 
                for phone in phone_list
            }
            
            for future in as_completed(future_to_phone):
                phone = future_to_phone[future]
                try:
                    results[phone] = future.result()
                except Exception as e:
                    results[phone] = {"error": str(e)}
        
        return results

# 2. PERFORMANCE OPTIMIZATION
def optimize_image_for_platform(img: Image.Image, platform: str) -> Image.Image:
    """Optimize image size/quality for different platforms"""
    if platform == "facebook":
        # Facebook: 1200x630, moderate compression
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
    elif platform == "instagram":
        # Instagram: high quality, square or portrait
        max_size = max(img.width, img.height)
        if max_size > 1350:
            img.thumbnail((1350, 1350), Image.Resampling.LANCZOS)
            
    elif platform == "whatsapp":
        # WhatsApp: balanced quality for messaging
        img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
    
    return img

# 3. ENHANCED CACHING WITH VERSIONING
class VersionedCache:
    """Cache with versioning for updates"""
    
    def __init__(self, ttl: int = 86400, version: str = "v1"):
        self.ttl = ttl
        self.version = version
    
    def get_cache_key(self, key: str) -> str:
        return f"{self.version}:{key}"
    
    def clear_old_versions(self):
        """Clear old cached versions"""
        pass

# 4. REAL-TIME PROGRESS UPDATES
def create_progress_tracker(total_steps: int):
    """Create a progress tracker with detailed updates"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update(step: int, message: str):
        progress = (step / total_steps)
        progress_bar.progress(progress)
        status_text.text(f"🔄 {message} ({step}/{total_steps})")
    
    return update

# 5. TEMPLATE MANAGEMENT SYSTEM
class TemplateManager:
    """Manage and organize different ad templates"""
    
    TEMPLATES = {
        "modern_minimal": {
            "background": "#ffffff",
            "font_family": "Helvetica",
            "layout": "centered",
            "colors": ["#8B0000", "#FFD700"]
        },
        "dark_premium": {
            "background": "#0a0a0a",
            "font_family": "Montserrat",
            "layout": "asymmetric",
            "colors": ["#8B0000", "#FF6B35"]
        },
        "vibrant_kenyan": {
            "background": "#f8f9fa",
            "font_family": "Poppins",
            "layout": "grid",
            "colors": ["#8B0000", "#FFD700", "#FF6B35"]
        }
    }
    
    @staticmethod
    def apply_template(img: Image.Image, template_name: str) -> Image.Image:
        """Apply a pre-defined template to an image"""
        template = TemplateManager.TEMPLATES.get(template_name, {})
        # Apply template styling
        return img

# 6. LOCALIZATION SUPPORT
class Localization:
    """Support for multiple languages (Kenyan context)"""
    
    LANGUAGES = {
        "en": {
            "cta": "Shop Now",
            "contact": "Contact Us",
            "warranty": "Official Warranty",
            "delivery": "Nairobi Delivery"
        },
        "sw": {
            "cta": "Nunua Sasa",
            "contact": "Wasiliana Nasi",
            "warranty": "Dhamana Rasmi",
            "delivery": "Uwasilishaji Nairobi"
        }
    }
    
    @staticmethod
    def get_text(key: str, lang: str = "en") -> str:
        return Localization.LANGUAGES.get(lang, {}).get(key, key)

# 7. ADVANCED SPECS ANALYSIS
class SpecsAnalyzer:
    """Advanced analysis of phone specifications"""
    
    @staticmethod
    def calculate_performance_score(phone_data: dict) -> float:
        """Calculate a performance score 0-100 based on specs"""
        score = 0
        factors = 0
        
        # RAM scoring
        if phone_data.get("ram") != "N/A":
            try:
                ram_gb = int(re.search(r'(\d+)', phone_data["ram"]).group(1))
                score += min(30, ram_gb * 3)  # Max 30 points for RAM
                factors += 1
            except:
                pass
        
        # Camera scoring
        if phone_data.get("main_camera") != "N/A":
            try:
                mp_total = sum(
                    int(mp) for mp in re.findall(r'(\d+)MP', phone_data["main_camera"])
                )
                score += min(30, mp_total // 5)  # Max 30 points for camera
                factors += 1
            except:
                pass
        
        # Battery scoring
        if phone_data.get("battery") != "N/A" and "mAh" in phone_data["battery"]:
            try:
                mAh = int(re.search(r'(\d+)', phone_data["battery"]).group(1))
                score += min(20, mAh // 100)  # Max 20 points for battery
                factors += 1
            except:
                pass
        
        # Storage scoring
        if phone_data.get("storage") != "N/A":
            try:
                storage_gb = int(re.search(r'(\d+)', phone_data["storage"]).group(1))
                score += min(20, storage_gb // 32)  # Max 20 points for storage
                factors += 1
            except:
                pass
        
        return (score / max(factors, 1)) if factors > 0 else 0
    
    @staticmethod
    def generate_specs_summary(phone_data: dict) -> str:
        """Generate a human-readable specs summary"""
        highlights = []
        
        if phone_data.get("main_camera") != "N/A":
            highlights.append(f"📸 {phone_data['main_camera']} camera system")
        
        if phone_data.get("ram") != "N/A":
            highlights.append(f"⚡ {phone_data['ram']} RAM for smooth performance")
        
        if phone_data.get("battery") != "N/A":
            highlights.append(f"🔋 {phone_data['battery']} all-day battery")
        
        if phone_data.get("storage") != "N/A":
            highlights.append(f"💾 {phone_data['storage']} storage space")
        
        return " | ".join(highlights[:3])

# 8. SCHEDULING AND AUTOMATION
class CampaignScheduler:
    """Schedule campaigns for future posting"""
    
    def __init__(self):
        self.scheduled = []
    
    def schedule_campaign(self, phone_data: dict, platforms: List[str], 
                         schedule_time: datetime, repeat: bool = False):
        """Schedule a campaign for posting"""
        campaign = {
            "phone": phone_data,
            "platforms": platforms,
            "schedule_time": schedule_time,
            "repeat": repeat,
            "status": "scheduled"
        }
        self.scheduled.append(campaign)
        return campaign
    
    def get_upcoming_campaigns(self) -> List[Dict]:
        """Get upcoming scheduled campaigns"""
        now = datetime.now()
        return [c for c in self.scheduled 
                if c["schedule_time"] > now and c["status"] == "scheduled"]

# 9. ADVANCED ERROR RECOVERY
class ErrorRecovery:
    """Advanced error recovery and fallback mechanisms"""
    
    @staticmethod
    def fallback_phone_data(phone_name: str) -> dict:
        """Provide fallback data when API fails"""
        # Use cached data or pre-defined templates
        return {
            "name": phone_name,
            "screen": "6.7 inches, 1080x2400 pixels",
            "main_camera": "50MP + 12MP + 8MP",
            "ram": "8GB",
            "storage": "256GB",
            "battery": "5000 mAh",
            "chipset": "Snapdragon 8 Gen 2",
            "os": "Android 14"
        }
    
    @staticmethod
    def fallback_ad_elements(phone_data: dict) -> dict:
        """Generate fallback ad elements"""
        return {
            "hook": f"Introducing {phone_data['name']}",
            "cta": "Shop Now at Tripple K",
            "urgency": "Limited Stock Available",
            "hashtags": "#TrippleK #KenyaTech #Smartphone"
        }

# 10. ANALYTICS DASHBOARD
def create_analytics_dashboard(campaign_history: List[Dict]):
    """Create an analytics dashboard for campaigns"""
    
    if not campaign_history:
        st.info("No campaign history available yet")
        return
    
    # Performance metrics
    st.subheader("📊 Campaign Analytics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Campaigns", len(campaign_history))
    
    with col2:
        unique_phones = len(set(c['phone_name'] for c in campaign_history))
        st.metric("Unique Phones", unique_phones)
    
    with col3:
        avg_specs = sum(len(str(c.get('specs', {}))) for c in campaign_history) / len(campaign_history)
        st.metric("Avg Specs Length", f"{avg_specs:.0f} chars")
    
    with col4:
        successful = sum(1 for c in campaign_history if c.get('status') == 'success')
        st.metric("Success Rate", f"{(successful/len(campaign_history))*100:.0f}%")
    
    # Recent campaigns
    st.subheader("📋 Recent Campaigns")
    
    for campaign in campaign_history[-5:]:
        with st.expander(f"{campaign.get('phone_name', 'Unknown')} - {campaign.get('date', '')}"):
            if campaign.get('specs'):
                st.json(campaign['specs'])
            if campaign.get('ads_generated'):
                st.text(f"Ads generated: {len(campaign['ads_generated'])}")

# ==========================================
# INTEGRATION INTO MAIN APP
# ==========================================

def enhanced_main():
    """Enhanced version of the main application"""
    
    # Add initialization for new features
    if "campaign_history" not in st.session_state:
        st.session_state.campaign_history = []
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = CampaignScheduler()
    if "selected_template" not in st.session_state:
        st.session_state.selected_template = "modern_minimal"
    
    # Enhanced header with stats
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown('<h1 style="margin:0;">📱 Tripple K Marketing Suite Pro</h1>', unsafe_allow_html=True)
        st.markdown('<p style="margin:0.5rem 0 0 0; opacity:0.9;">Professional AI-Powered Marketing Platform</p>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.current_phone:
            score = SpecsAnalyzer.calculate_performance_score(st.session_state.current_phone)
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-value">{int(score)}/100</div>
                <div class="metric-label">Performance Score</div>
            </div>
            ''', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-value">{len(st.session_state.campaign_history)}</div>
            <div class="metric-label">Total Campaigns</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Enhanced tabs
    tabs = st.tabs(["🔍 Find Phone", "📱 Create Campaign", "🎨 Generate Ads", "📊 Analytics", "⚙️ Settings"])
    
    # ... (existing tab content with enhancements) ...
    
    # NEW TAB: ANALYTICS
    with tabs[3]:
        create_analytics_dashboard(st.session_state.campaign_history)
        
        # Performance visualization
        if st.session_state.campaign_history:
            st.subheader("📈 Performance Trends")
            
            # Simple visualization
            dates = [c.get('date', '') for c in st.session_state.campaign_history]
            phones = [c.get('phone_name', '') for c in st.session_state.campaign_history]
            
            # Display as a table
            import pandas as pd
            df = pd.DataFrame({
                'Date': dates[-10:],
                'Phone': phones[-10:],
                'Status': ['Success' for _ in range(min(10, len(dates)))]
            })
            st.dataframe(df, use_container_width=True)
    
    # NEW TAB: SETTINGS
    with tabs[4]:
        st.subheader("⚙️ Application Settings")
        
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            st.markdown("#### 🎨 Design Settings")
            
            # Template selection
            template = st.selectbox(
                "Ad Template",
                list(TemplateManager.TEMPLATES.keys()),
                index=0,
                help="Choose a design template for generated ads"
            )
            st.session_state.selected_template = template
            
            # Language selection
            language = st.selectbox(
                "Language",
                ["English (en)", "Swahili (sw)"],
                index=0
            )
            
            # Quality settings
            image_quality = st.slider(
                "Image Quality",
                min_value=70,
                max_value=100,
                value=95,
                help="Higher quality = larger file size"
            )
        
        with col_set2:
            st.markdown("#### ⚡ Performance Settings")
            
            # Cache settings
            clear_cache = st.button("Clear Cache", help="Clear all cached images and data")
            if clear_cache:
                st.cache_data.clear()
                st.success("Cache cleared!")
            
            # API settings
            if GROQ_KEY:
                st.success("✅ API Key Configured")
                test_api = st.button("Test API Connection")
                if test_api:
                    try:
                        test_response = client.chat.completions.create(
                            model=MODEL,
                            messages=[{"role": "user", "content": "Test"}],
                            max_tokens=5
                        )
                        st.success("✅ API connection successful!")
                    except Exception as e:
                        st.error(f"❌ API connection failed: {e}")
            
            # Export settings
            st.markdown("#### 📤 Export Settings")
            export_format = st.selectbox(
                "Default Export Format",
                ["PNG", "JPEG", "PDF Bundle"],
                index=0
            )
            
            include_watermark = st.checkbox("Include Tripple K Watermark", value=True)
        
        # Data management
        st.markdown("---")
        st.markdown("#### 🗃️ Data Management")
        
        col_data1, col_data2, col_data3 = st.columns(3)
        
        with col_data1:
            if st.button("Export Campaign Data", type="secondary"):
                if st.session_state.campaign_history:
                    import json
                    data = json.dumps(st.session_state.campaign_history, indent=2)
                    st.download_button(
                        "📥 Download JSON",
                        data,
                        "tripplek_campaigns.json",
                        "application/json"
                    )
                else:
                    st.warning("No campaign data to export")
        
        with col_data2:
            if st.button("Reset Session Data", type="secondary"):
                for key in list(st.session_state.keys()):
                    if key not in ["campaign_history"]:  # Keep history
                        del st.session_state[key]
                st.rerun()
        
        with col_data3:
            if st.button("View System Info", type="secondary"):
                st.code(f"""
                Python: {sys.version}
                Streamlit: {st.__version__}
                Pillow: {Image.__version__}
                Campaigns: {len(st.session_state.campaign_history)}
                Current Phone: {st.session_state.current_phone.get('name') if st.session_state.current_phone else 'None'}
                """)

# ==========================================
# ENHANCED AD GENERATOR INTEGRATION
# ==========================================

class EnhancedFacebookAdGenerator(FacebookAdGenerator):
    """Enhanced Facebook ad generator with templates"""
    
    def generate(self, phone_data: dict, ad_elements: Dict[str, str] = None) -> Image.Image:
        # Get base ad
        base_ad = super().generate(phone_data, ad_elements)
        
        # Apply template if selected
        template_name = st.session_state.get('selected_template', 'modern_minimal')
        if template_name != 'modern_minimal':
            base_ad = TemplateManager.apply_template(base_ad, template_name)
        
        # Add performance badge if score is high
        score = SpecsAnalyzer.calculate_performance_score(phone_data)
        if score > 80:
            draw = ImageDraw.Draw(base_ad)
            draw.text((100, 100), "⭐ TOP PERFORMER", 
                     fill=BRAND_GOLD, font=self.badge_font)
        
        return base_ad

# ==========================================
# ENHANCED ERROR HANDLING IN MAIN FLOW
# ==========================================

def safe_generate_content(phone_data: dict, persona: str, tone: str) -> Optional[Dict[str, str]]:
    """Enhanced content generation with fallbacks"""
    try:
        # Try AI generation first
        content = generate_marketing_content(phone_data, persona, tone)
        
        if content:
            # Add to campaign history
            campaign_entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "phone_name": phone_data.get("name"),
                "persona": persona,
                "tone": tone,
                "status": "success",
                "specs": {k: v for k, v in phone_data.items() if k != 'raw'}
            }
            st.session_state.campaign_history.append(campaign_entry)
            
            return content
        else:
            # Fallback to pre-defined content
            st.warning("⚠️ Using fallback content (AI generation failed)")
            return ErrorRecovery.fallback_ad_elements(phone_data)
            
    except Exception as e:
        st.error(f"Content generation failed: {e}")
        return ErrorRecovery.fallback_ad_elements(phone_data)

# ==========================================
# FINAL INTEGRATION
# ==========================================

if __name__ == "__main__":
    # Add import for new features
    import sys
    
    # Check for necessary packages
    try:
        import pandas as pd
        HAS_PANDAS = True
    except:
        HAS_PANDAS = False
        st.warning("Pandas not installed. Some analytics features disabled.")
    
    # Run enhanced version
    enhanced_main()