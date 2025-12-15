import streamlit as st
import io, requests, math, tempfile, base64, json, time, os, traceback
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip
from rembg import remove

# --- GLOBAL CONFIGURATION ---
st.set_page_config(page_title="TikTok AdGen Pro", layout="wide", page_icon="🎬")

# --- TIKTOK-OPTIMIZED CONSTANTS ---
WIDTH, HEIGHT = 1080, 1920
FPS = 30
DURATION = 15
LOGO_URL = "https://ik.imagekit.io/ericmwangi/smlogo.png?updatedAt=1763071173037"

# --- TRENDING MUSIC TRACKS ---
MUSIC_TRACKS = {
    "Energetic Viral": "https://archive.org/download/Bensound_-_Jazzy_Frenchy/Bensound_-_Jazzy_Frenchy.mp3",
    "Chill Luxury": "https://archive.org/download/bensound-adaytoremember/bensound-adaytoremember.mp3",
    "Modern Beats": "https://archive.org/download/bensound-sweet/bensound-sweet.mp3",
}

# --- HASHTAGS ---
TRENDING_HASHTAGS = {
    "furniture": "#FurnitureTikTok #HomeDecor #InteriorDesign #HomeInspo #FurnitureDesign #ModernHome #LuxuryFurniture",
    "diy": "#DIYHome #HomeHacks #DIYProject #HomeImprovement #RoomMakeover #BudgetFriendly #DIYDecor",
}

# --- AUTH ---
if "groq_key" not in st.secrets:
    st.error("🚨 Missing Secret: Add `groq_key` to your .streamlit/secrets.toml")
    st.stop()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {st.secrets['groq_key']}",
    "Content-Type": "application/json"
}

# --- IMAGE PROCESSING ---
@st.cache_data(show_spinner=False)
def process_image_pro(input_image_bytes):
    """Enhanced background removal with quality optimization."""
    try:
        output_bytes = remove(input_image_bytes)
        clean_img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        
        # Enhancements
        clean_img = ImageEnhance.Contrast(clean_img).enhance(1.2)
        clean_img = ImageEnhance.Sharpness(clean_img).enhance(1.8)
        clean_img = ImageEnhance.Color(clean_img).enhance(1.15)
        return clean_img
    except Exception as e:
        st.error(f"Image processing error: {e}")
        return None

# --- FONTS ---
def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

# --- ANIMATION EASING ---
def ease_out_elastic(t):
    c4 = (2 * math.pi) / 3
    if t <= 0: return 0
    if t >= 1: return 1
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

# --- TEMPLATES ---
BRAND_PRIMARY = "#4C3B30"
BRAND_ACCENT = "#D2A544"

TEMPLATES = {
    "Viral Zoom": {
        "bg_grad": ["#1a1a1a", "#2d2d2d"],
        "accent": "#FFD700",
        "price_bg": "#FF4444",
        "price_text": "#FFFFFF",
    },
    "Luxury Glam": {
        "bg_grad": [BRAND_PRIMARY, "#2a201b"],
        "accent": BRAND_ACCENT,
        "price_bg": BRAND_ACCENT,
        "price_text": "#000000",
    },
    "Modern Pop": {
        "bg_grad": ["#FF6B6B", "#4ECDC4"],
        "accent": "#FFFFFF",
        "price_bg": "#FFE66D",
        "price_text": "#000000",
    },
}

# --- GROQ AI ---
def ask_groq(payload, timeout=20):
    try:
        r = requests.post(GROQ_URL, json=payload, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content.strip()
        return None
    except requests.exceptions.Timeout:
        st.warning("⚠️ Groq API timeout. Using fallback.")
        return None
    except Exception as e:
        st.warning(f"⚠️ Groq API error: {str(e)[:150]}")
        return None

def generate_tiktok_hook(product_name):
    """Generate a 3-5 word TikTok hook."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Generate ONLY a 3-5 word viral TikTok hook. No quotes, no explanation."},
            {"role": "user", "content": f"Product: {product_name}"}
        ],
        "temperature": 0.9,
        "max_tokens": 15
    }
    
    result = ask_groq(payload, timeout=10)
    if result:
        result = result.strip('"').strip("'").strip()
        return result if len(result.split()) <= 6 else "Transform Your Space"
    return "Transform Your Space"

def generate_tiktok_caption(product_name, price, hook):
    """Generate complete TikTok caption."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Write a 2-sentence engaging TikTok caption. No hashtags."},
            {"role": "user", "content": f"Product: {product_name}, Price: {price}, Hook: {hook}"}
        ],
        "temperature": 0.8,
        "max_tokens": 80
    }
    
    caption = ask_groq(payload, timeout=10)
    if not caption:
        caption = f"Elevate your space with the {product_name}. Premium quality at {price}. DM to order! 💫"
    
    hashtags = TRENDING_HASHTAGS["furniture"]
    return f"{caption}\n\n{hashtags}\n\n#SMInteriors"

def generate_content_ideas(content_type, keyword):
    """Generate viral content ideas."""
    prompts = {
        "DIY Tips": f"List 5 viral DIY home decor hacks about '{keyword}'. Use emoji.",
        "Furniture Care": f"List 5 furniture care tips for '{keyword}'. Use emoji.",
        "Design Trends": f"List 5 interior design trends about '{keyword}'. Use emoji.",
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a TikTok content expert. Be concise and creative."},
            {"role": "user", "content": prompts.get(content_type, prompts["DIY Tips"])}
        ],
        "temperature": 0.9,
        "max_tokens": 400
    }
    
    result = ask_groq(payload)
    return result if result else "*No ideas generated. Try again.*"

# --- RENDERING ---
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))

def draw_text_outline(draw, text, pos, font, fill, outline, width=3):
    x, y = pos
    for dx in range(-width, width+1):
        for dy in range(-width, width+1):
            if dx != 0 or dy != 0:
                draw.text((x+dx, y+dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)

def create_tiktok_frame(t, product_img, template_name, texts):
    """Create a single frame optimized for TikTok."""
    try:
        T = TEMPLATES.get(template_name, TEMPLATES["Viral Zoom"])
        canvas = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(canvas)
        
        # Gradient background
        c1 = hex_to_rgb(T["bg_grad"][0])
        c2 = hex_to_rgb(T["bg_grad"][1])
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
        
        # Convert to RGBA for compositing
        canvas = canvas.convert("RGBA")
        
        # Product animation
        product_scale = 1.0
        if t < 2.0:
            product_scale = 0.5 + 0.5 * ease_out_elastic(min(1.0, t / 2.0))
        elif t > 12.0:
            product_scale = 1.0 + 0.2 * ease_in_out_cubic(min(1.0, (t - 12.0) / 3.0))
        
        float_offset = int(math.sin(t * 1.5) * 20)
        
        # Resize product
        product_h = int(HEIGHT * 0.45 * product_scale)
        product_w = int(product_img.width * (product_h / max(product_img.height, 1)))
        
        if product_w > 10 and product_h > 10:
            p_resized = product_img.resize((product_w, product_h), Image.LANCZOS)
            
            prod_x = (WIDTH - product_w) // 2
            prod_y = int(HEIGHT * 0.35) + float_offset
            
            # Paste product
            canvas.paste(p_resized, (prod_x, prod_y), p_resized)
        
        # Convert back to RGB for drawing
        canvas_rgb = canvas.convert("RGB")
        draw = ImageDraw.Draw(canvas_rgb)
        
        # Hook text
        if t > 0.5:
            hook_alpha = min(1.0, (t - 0.5) / 0.5)
            hook_offset = int(50 * (1 - ease_out_elastic(hook_alpha)))
            
            hook_font = get_font(80)
            hook_text = texts.get("hook", "Amazing Deal!")
            
            bbox = draw.textbbox((0, 0), hook_text, font=hook_font)
            text_width = bbox[2] - bbox[0]
            hook_x = (WIDTH - text_width) // 2
            hook_y = 150 - hook_offset
            
            draw_text_outline(draw, hook_text, (hook_x, hook_y), 
                            hook_font, T["accent"], (0, 0, 0), 4)
        
        # Price badge
        if t > 3.0:
            price_scale = ease_out_elastic(min(1.0, (t - 3.0) / 0.8))
            if price_scale > 0.1:
                badge_w = int(500 * price_scale)
                badge_h = int(120 * price_scale)
                badge_x = (WIDTH - badge_w) // 2
                badge_y = int(HEIGHT * 0.73)
                
                price_color = hex_to_rgb(T["price_bg"])
                draw.rounded_rectangle(
                    [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                    radius=25, 
                    fill=price_color
                )
                
                price_font = get_font(60)
                price_text = texts.get("price", "Ksh 49,900")
                p_bbox = draw.textbbox((0, 0), price_text, font=price_font)
                p_width = p_bbox[2] - p_bbox[0]
                p_x = badge_x + (badge_w - p_width) // 2
                p_y = badge_y + 25
                
                draw.text((p_x, p_y), price_text, font=price_font, fill=T["price_text"])
        
        # CTA
        if t > 10.0:
            cta_font = get_font(45)
            cta_text = f"📱 {texts.get('contact', '0710895737')}"
            
            c_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
            c_width = c_bbox[2] - c_bbox[0]
            cta_x = (WIDTH - c_width) // 2
            cta_y = int(HEIGHT * 0.88)
            
            draw_text_outline(draw, cta_text, (cta_x, cta_y),
                            cta_font, "#FFFFFF", (0, 0, 0), 3)
        
        # Logo
        if t > 0:
            try:
                logo_resp = requests.get(LOGO_URL, stream=True, timeout=5)
                logo = Image.open(logo_resp.raw).convert("RGBA")
                logo = logo.resize((160, 90), Image.LANCZOS)
                
                # Convert canvas_rgb back to RGBA for logo composite
                canvas_rgba = canvas_rgb.convert("RGBA")
                canvas_rgba.paste(logo, (50, 50), logo)
                canvas_rgb = canvas_rgba.convert("RGB")
            except:
                pass
        
        return np.array(canvas_rgb)
    
    except Exception as e:
        st.error(f"Frame render error at t={t:.2f}: {e}")
        # Return black frame as fallback
        return np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

# --- STREAMLIT UI ---
st.title("🎬 TikTok AdGen Pro")
st.caption("Create viral furniture ads optimized for TikTok & Instagram Reels")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📸 Product Setup")
    uploaded_file = st.file_uploader("Upload Product Image", type=["jpg", "png", "jpeg"])
    product_name = st.text_input("Product Name", "Walden Media Console")
    price = st.text_input("Price", "Ksh 49,900")
    contact = st.text_input("Contact", "0710895737")
    
    st.subheader("🎨 Style & Music")
    template = st.selectbox("Template Style", list(TEMPLATES.keys()))
    music = st.selectbox("Background Track", list(MUSIC_TRACKS.keys()))
    
    generate_btn = st.button("🚀 Generate TikTok Ad", type="primary")

with col2:
    st.subheader("💡 Content Idea Generator")
    content_type = st.selectbox("Content Type", 
                                ["DIY Tips", "Furniture Care", "Design Trends"])
    keyword = st.text_input("Focus Keyword", "Mid-Century Console")
    
    if st.button("✨ Generate Ideas"):
        with st.spinner("Generating ideas..."):
            ideas = generate_content_ideas(content_type, keyword)
            st.markdown("### 🎯 Content Ideas")
            st.markdown(ideas)

# --- VIDEO GENERATION ---
if generate_btn:
    if not uploaded_file:
        st.error("⚠️ Please upload a product image first!")
    else:
        try:
            progress_placeholder = st.empty()
            
            # Step 1: Process image
            progress_placeholder.info("🎨 Step 1/4: Processing image...")
            raw_img = Image.open(uploaded_file).convert("RGBA")
            
            img_byte_arr = io.BytesIO()
            raw_img.save(img_byte_arr, format="PNG")
            img_bytes = img_byte_arr.getvalue()
            
            processed_img = process_image_pro(img_bytes)
            
            if processed_img is None:
                st.error("Failed to process image. Please try another image.")
                st.stop()
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.image(raw_img, caption="Original", width=300)
            with col_b:
                st.image(processed_img, caption="Processed", width=300)
            
            # Step 2: Generate hook
            progress_placeholder.info("🧠 Step 2/4: Generating hook...")
            hook = generate_tiktok_hook(product_name)
            st.success(f"**Hook:** {hook}")
            
            # Step 3: Generate caption
            full_caption = generate_tiktok_caption(product_name, price, hook)
            with st.expander("📝 TikTok Caption"):
                st.text_area("Copy this:", full_caption, height=120)
            
            # Step 4: Render video
            progress_placeholder.info("🎬 Step 3/4: Rendering frames...")
            
            texts = {
                "hook": hook,
                "price": price,
                "contact": contact
            }
            
            frames = []
            total_frames = FPS * DURATION
            render_progress = st.progress(0)
            
            for i in range(total_frames):
                frame = create_tiktok_frame(i / FPS, processed_img, template, texts)
                frames.append(frame)
                
                if i % 15 == 0:
                    render_progress.progress((i + 1) / total_frames)
            
            render_progress.progress(1.0)
            
            # Step 5: Create video
            progress_placeholder.info("🎵 Step 4/4: Adding audio...")
            
            clip = ImageSequenceClip(frames, fps=FPS)
            
            # Try to add audio
            audio_path = None
            final_clip = clip
            
            try:
                audio_response = requests.get(MUSIC_TRACKS[music], timeout=20)
                audio_response.raise_for_status()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
                    tf.write(audio_response.content)
                    audio_path = tf.name
                
                audio_clip = AudioFileClip(audio_path)
                audio_duration = min(DURATION, audio_clip.duration)
                audio_clip = audio_clip.subclip(0, audio_duration)
                
                # Fade out
                try:
                    audio_clip = audio_clip.audio_fadeout(1.5)
                except:
                    pass
                
                final_clip = clip.set_audio(audio_clip)
                
            except Exception as e:
                st.warning(f"⚠️ Using silent video (audio error: {str(e)[:100]})")
            
            # Render final video
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as vf:
                output_path = vf.name
            
            try:
                final_clip.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=FPS,
                    preset="ultrafast",
                    logger=None,
                    verbose=False
                )
                
                progress_placeholder.success("✅ Video Ready!")
                st.video(output_path)
                
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Video",
                        f,
                        file_name=f"{product_name.replace(' ', '_')}_tiktok.mp4",
                        mime="video/mp4"
                    )
                
                st.info("📱 **Upload Tips:** Post 6-9 PM, engage in first hour, use trending sounds")
                
            except Exception as e:
                st.error(f"Video rendering failed: {e}")
                st.code(traceback.format_exc())
            
            finally:
                # Cleanup
                try:
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                    if audio_path and os.path.exists(audio_path):
                        os.unlink(audio_path)
                except:
                    pass
        
        except Exception as e:
            st.error(f"❌ Generation failed: {e}")
            st.code(traceback.format_exc())

st.markdown("---")
st.caption("Made with ❤️ for SM Interiors")