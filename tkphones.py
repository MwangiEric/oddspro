import streamlit as st
import requests
from groq import Groq
import os
import re
from dateutil import parser
from datetime import datetime
import json
from PIL import Image, ImageDraw, ImageFont
import io

# ----------------------------
# CONFIG
# ----------------------------
GROQ_KEY = st.secrets.get("groq_key", "")
client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
MODEL = "llama-3.3-70b-versatile"  # Confirmed Groq model

BRAND_MAROON = "#8B0000"
BRAND_GREEN = "#4CAF50"
LOGO_URL = "https://ik.imagekit.io/ericmwangi/tklogo.png?updatedAt=1764543349107"
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"

st.set_page_config(page_title="📱 Tripple K Phone Specs & Ads", layout="wide")

st.markdown(f"""
<style>
h1, h2, h3 {{ color: {BRAND_MAROON} !important; }}
.stButton>button {{
    background-color: {BRAND_MAROON};
    color: white;
    font-weight: bold;
    border-radius: 8px;
    margin-top: 0.3rem;
}}
.copy-btn {{
    background: {BRAND_GREEN}; color: white; border: none; padding: 8px 16px;
    border-radius: 6px; cursor: pointer; font-size: 1rem; margin-top: 10px;
}}
.post-title {{
    font-weight: bold;
    color: #1e3a8a;
    margin: 1rem 0 0.4rem 0;
}}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# PROMPT BUILDER (structured for parsing)
# ----------------------------
def build_groq_prompt(phone_dict: dict, persona: str, tone: str) -> str:
    features = []
    if "water" in str(phone_dict["raw"]).lower() or "IP" in str(phone_dict["raw"]):
        features.append("water-resistant")
    if "120Hz" in str(phone_dict["raw"]):
        features.append("120Hz display")
    if "5000" in phone_dict["battery"]:
        features.append("5000mAh battery")
    if "50 MP" in phone_dict["main_camera"]:
        features.append("50MP main camera")
    feature_str = ", ".join(features) if features else "great performance"

    return f"""
You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

Phone: {phone_dict['name']}
Key specs: Screen {phone_dict['screen']}, RAM {phone_dict['ram']}, Storage {phone_dict['storage']}, Battery {phone_dict['battery']}, Main Camera {phone_dict['main_camera']}, Selfie Camera {phone_dict['selfie_camera']}
Unique features: {feature_str}
Persona: {persona}
Tone: {tone}

Mention Tripple K value props subtly (e.g., "available with warranty from Tripple K", "pay on delivery in Nairobi").
Do NOT use emojis or markdown. Keep each field as a single line.

Output in this exact format:

TikTok: [single line under 120 chars]
WhatsApp: [single line including phone number]
Facebook: [single line]
Instagram: [single line]
Hashtags: #TrippleK #TrippleKKE #PhoneDealsKE
    """.strip()

# ----------------------------
# SAFE API CALL
# ----------------------------
def safe_api_call(url: str):
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 429:
            return None, "Rate limited (429). Try again later."
        if res.status_code != 200:
            return None, f"Server error: HTTP {res.status_code}"
        return res.json(), None
    except Exception as e:
        return None, f"Network error: {str(e)}"

# ----------------------------
# SPEC PARSING (clean format)
# ----------------------------
def parse_specs(raw):
    # Screen
    display = raw.get("display", {})
    size_part = display.get("size", "N/A").split(",")[0] if display.get("size") else "N/A"
    res_part = display.get("resolution", "N/A")
    screen = f"{size_part}, {res_part}"

    # RAM & Storage
    ram = storage = "N/A"
    for mem in raw.get("memory", []):
        if mem.get("label") == "internal":
            val = mem.get("value", "")
            ram_match = re.search(r"(\d+GB)\s+RAM", val)
            storage_match = re.search(r"(\d+GB)(?!\s+RAM)", val)
            if ram_match: ram = ram_match.group(1)
            if storage_match: storage = storage_match.group(1)

    # Battery
    battery = raw.get("battery", {}).get("battType", "N/A")

    # Camera MP extraction
    def extract_mp(cam_str):
        if not cam_str: return "N/A"
        mp_list = re.findall(r"(\d+)MP", cam_str)
        return "+".join(mp_list) + "MP" if mp_list else "N/A"

    main_cam = extract_mp(raw.get("mainCamera", {}).get("mainModules", ""))
    selfie_cam = extract_mp(raw.get("selfieCamera", {}).get("selfieModules", ""))

    return {
        "name": raw["name"],
        "cover": (raw.get("image") or raw.get("cover", "")).strip(),
        "screen": screen,
        "ram": ram,
        "storage": storage,
        "battery": battery,
        "main_camera": main_cam,
        "selfie_camera": selfie_cam,
        "raw": raw
    }

# ----------------------------
# AD IMAGE GENERATOR
# ----------------------------
def generate_whatsapp_ad_image(phone_data):
    try:
        # Fetch phone image
        phone_img = None
        if phone_data["cover"]:
            try:
                resp = requests.get(phone_data["cover"], timeout=10)
                phone_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            except:
                pass

        width, height = 1080, 1350
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        # Left: Phone image (55% width, full height)
        if phone_img:
            img_w = int(width * 0.55)
            img_h = height
            phone_img = phone_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
            img.paste(phone_img, (0, 0))

        # Right: Text
        text_x = int(width * 0.55) + 40
        y = 100

        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
            spec_font = ImageFont.truetype("DejaVuSans.ttf", 40)
        except:
            title_font = ImageFont.load_default()
            spec_font = ImageFont.load_default()

        # Title
        draw.text((text_x, y), phone_data["name"], fill=BRAND_MAROON, font=title_font)
        y += 110

        specs = [
            f"Screen: {phone_data['screen']}",
            f"RAM: {phone_data['ram']}",
            f"Storage: {phone_data['storage']}",
            f"Battery: {phone_data['battery']}",
            f"Main Camera: {phone_data['main_camera']}",
            f"Selfie Camera: {phone_data['selfie_camera']}"
        ]
        for spec in specs:
            draw.text((text_x, y), spec, fill="#333", font=spec_font)
            y += 70

        y += 30
        draw.text((text_x, y), f"Call {TRIPPLEK_PHONE}", fill=BRAND_GREEN, font=spec_font)
        y += 60
        draw.text((text_x, y), "Warranty • Pay on delivery", fill="#333", font=spec_font)

        # Logo (top-right)
        try:
            logo = Image.open(requests.get(LOGO_URL, stream=True).raw).convert("RGBA")
            logo.thumbnail((200, 200))
            img.paste(logo, (width - 220, 40), logo)
        except:
            pass

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Ad image generation failed: {e}")
        return None

# ----------------------------
# COPY BUTTON
# ----------------------------
def copy_button(text: str, label: str = "Copy"):
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("`", "\\`")
    st.markdown(f"""
    <button class="copy-btn" onclick='navigator.clipboard.writeText("{escaped}")'>{label}</button>
    """, unsafe_allow_html=True)

# ----------------------------
# MAIN APP
# ----------------------------
st.title("📱 Tripple K Phone Specs & Ad Generator")

phone_query = st.text_input("Search a phone (e.g., Tecno Spark 20)", "")

if st.button("Get Phones"):
    if not phone_query.strip():
        st.error("Please enter a phone name")
        st.stop()

    with st.spinner("Searching phones..."):
        url1 = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(phone_query)}"
        results, err = safe_api_call(url1)
        if err and "429" in err:
            st.warning("Using public backup API...")
            url2 = f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(phone_query)}"
            results, err = safe_api_call(url2)
        if err or not results:
            st.error(f"Failed: {err or 'No results'}")
            st.stop()
        st.session_state["search_results"] = results

if "search_results" in st.session_state:
    names = [r["name"] for r in st.session_state["search_results"]]
    selected_name = st.selectbox("Select phone:", names, index=0)
    selected = next(r for r in st.session_state["search_results"] if r["name"] == selected_name)

    with st.spinner("Loading specs..."):
        details, err = safe_api_call(f"https://tkphsp2.vercel.app/gsm/info/{selected['id']}")
        if err and "429" in err:
            st.warning("Using public specs API...")
            search_res, _ = safe_api_call(f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(selected_name)}")
            if search_res and len(search_res) > 0:
                slug = search_res[0]["slug"]
                details, err = safe_api_call(f"https://api-mobilespecs.azharimm.dev/{slug}")
        if err or not details:
            st.error(f"Specs load failed: {err}")
            st.stop()

    clean = parse_specs(details)
    st.session_state["current_phone"] = clean

    tab1, tab2, tab3 = st.tabs(["Phone Details", "Social Media", "Ads"])

    with tab1:
        st.markdown(f'<h1 style="color:{BRAND_MAROON};">{clean["name"]}</h1>', unsafe_allow_html=True)
        launched = clean["launched"]
        announced = launched.get("announced", "N/A")
        status = launched.get("status", "N/A")
        market_duration = time_since_release(status) if "Released" in status else "Not released"
        st.caption(f"Announced: {announced} | {market_duration}")

        col1, col2 = st.columns([1, 1.5])
        with col1:
            if clean["cover"]:
                st.image(clean["cover"], use_container_width=True)
                try:
                    img_data = requests.get(clean["cover"], timeout=10).content
                    st.download_button("Download Image", img_data, f"{clean['name']}.jpg")
                except:
                    st.caption("Image download unavailable")
        with col2:
            spec_lines = [
                f"Screen: {clean['screen']}",
                f"RAM: {clean['ram']}",
                f"Storage: {clean['storage']}",
                f"Battery: {clean['battery']}",
                f"Main Camera: {clean['main_camera']}",
                f"Selfie Camera: {clean['selfie_camera']}"
            ]
            spec_text = "\n".join(spec_lines)
            st.text_area("Parsed Specs", spec_text, height=220, disabled=True)
            copy_button(spec_text, "Copy Specs")

    with tab2:
        if not client:
            st.warning("Groq API key missing. Set `groq_key` in secrets.")
        else:
            persona = st.selectbox("Target Persona", ["All Kenyan buyers", "Budget students", "Tech-savvy professionals", "Camera creators", "Business executives"], index=0)
            tone = st.selectbox("Brand Tone", ["Playful", "Rational", "Luxury", "FOMO"], index=0)
            if st.button("Generate Social Posts"):
                with st.spinner("Generating with Groq..."):
                    prompt = build_groq_prompt(clean, persona, tone)
                    try:
                        chat = client.chat.completions.create(
                            model=MODEL,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.85,
                            max_tokens=550,
                        )
                        ad_copy = chat.choices[0].message.content.strip()
                        st.session_state["social_copy"] = ad_copy
                    except Exception as e:
                        st.session_state["social_copy"] = f"Groq error: {str(e)}"

        if "social_copy" in st.session_state:
            raw = st.session_state["social_copy"]
            if "Groq error" in raw:
                st.error(raw)
            else:
                posts = {"TikTok": "", "WhatsApp": "", "Facebook": "", "Instagram": "", "Hashtags": ""}
                lines = [l.strip() for l in raw.splitlines() if l.strip()]
                for line in lines:
                    if line.startswith("TikTok:"):
                        posts["TikTok"] = line.replace("TikTok:", "").strip()
                    elif line.startswith("WhatsApp:"):
                        posts["WhatsApp"] = line.replace("WhatsApp:", "").strip()
                    elif line.startswith("Facebook:"):
                        posts["Facebook"] = line.replace("Facebook:", "").strip()
                    elif line.startswith("Instagram:"):
                        posts["Instagram"] = line.replace("Instagram:", "").strip()
                    elif line.startswith("Hashtags:"):
                        posts["Hashtags"] = line.replace("Hashtags:", "").strip()

                for plat, text in posts.items():
                    if text:
                        st.markdown(f'<div class="post-title">{plat}</div>', unsafe_allow_html=True)
                        key = plat.lower()
                        if plat == "Hashtags":
                            st.text_input("", text, key=key)
                        else:
                            st.text_area("", text, height=60 if plat == "TikTok" else 90, key=key)
                        copy_button(text, f"Copy {plat}")

    with tab3:
        st.subheader("WhatsApp Ad Image")
        if st.button("Generate Branded Ad"):
            with st.spinner("Creating ad image..."):
                img_buf = generate_whatsapp_ad_image(clean)
                if img_buf:
                    st.image(img_buf, use_container_width=True)
                    st.download_button("Download Ad Image", img_buf, "tripplek_ad.png", "image/png")

st.divider()
st.caption(f"© Tripple K Communications | {TRIPPLEK_URL}")
