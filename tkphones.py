import streamlit as st
import requests
from groq import Groq
import os
import re
from dateutil import parser
from datetime import datetime

# ----------------------------
# CONFIG
# ----------------------------
GROQ_KEY = st.secrets.get("groq_key", "")
if GROQ_KEY:
    client = Groq(api_key=GROQ_KEY)
    MODEL = "llama3-1b-8192"  # Llama 3.2 1B
else:
    client = None
    MODEL = None

BRAND_MAROON = "#8B0000"
TRIPPLEK_PHONE = "+254700123456"
TRIPPLEK_URL = "https://www.tripplek.co.ke"

st.set_page_config(page_title="📱 Tripple K Phone Specs & Ads", layout="centered")

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
    background: #4CAF50; color: white; border: none; padding: 6px 12px;
    border-radius: 4px; cursor: pointer; font-size: 0.9rem;
}}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# SAFE API CALLS
# ----------------------------
def safe_api_call(url: str):
    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"
        # Check if response is JSON
        try:
            return res.json(), None
        except ValueError:
            return None, "Invalid JSON (possibly HTML error page)"
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"

def fetch_search_results(query: str):
    url = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(query)}"
    data, err = safe_api_call(url)
    if err:
        return None, f"Search failed: {err}"
    if not isinstance(data, list):
        return None, "Unexpected API response format"
    return data, None

def fetch_phone_details(phone_id: str):
    url = f"https://tkphsp2.vercel.app/gsm/info/{phone_id}"
    data, err = safe_api_call(url)
    if err:
        return None, f"Detail fetch failed: {err}"
    return data, None

# ----------------------------
# HELPERS
# ----------------------------
def time_since_release(status: str) -> str:
    try:
        clean = status.replace("Released ", "").strip()
        date = parser.parse(clean)
        delta = datetime.now() - date
        days = delta.days
        if days < 0:
            return "Not yet released"
        elif days < 7:
            return f"{days} day{'s' if days != 1 else ''} in market"
        elif days < 30:
            return f"{days // 7} week{'s' if days // 7 != 1 else ''} in market"
        elif days < 365:
            return f"{days // 30} month{'s' if days // 30 != 1 else ''} in market"
        else:
            return f"{days // 365} year{'s' if days // 365 != 1 else ''} in market"
    except:
        return "Unknown"

def parse_specs(raw):
    ram = storage = "N/A"
    for mem in raw.get("memory", []):
        if mem.get("label") == "internal":
            val = mem.get("value", "")
            ram_match = re.search(r"(\d+GB)\s+RAM", val)
            if ram_match:
                ram = ram_match.group(1)
            storage_match = re.search(r"(\d+GB)(?!\s+RAM)", val)
            if storage_match:
                storage = storage_match.group(1)

    return {
        "name": raw["name"],
        "cover": raw.get("image", "").strip() or raw.get("cover", "").strip(),
        "screen": f"{raw['display']['size']} ({raw['display']['resolution']})",
        "ram": ram,
        "storage": storage,
        "battery": raw["battery"]["battType"],
        "chipset": raw["platform"]["chipset"],
        "camera": raw["mainCamera"]["mainModules"],
        "os": raw["platform"]["os"],
        "launched": raw.get("launced", {}),
        "raw": raw
    }

def copy_button(text: str, label: str = "📋 Copy"):
    escaped = text.replace("`", "\\`").replace("\n", "\\n").replace('"', '\\"')
    st.markdown(f"""
    <button class="copy-btn" onclick='navigator.clipboard.writeText("{escaped}")'>{label}</button>
    """, unsafe_allow_html=True)

# ----------------------------
# GROQ
# ----------------------------
def generate_social_post(phone_dict, persona: str, tone: str):
    name = phone_data["name"]
    specs = phone_data["raw"]
    prompt = f"""
You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

PHONE: {name}
PERSONA: {persona}
TONE: {tone}

FULL SPECS:
{specs}

TRIPPLE K VALUE PROPS (must mention at least 2):
- Accredited distributor → 100% genuine phones
- Official manufacturer warranty
- Pay on delivery
- Fast Nairobi delivery
- Call {TRIPPLEK_PHONE} or visit {TRIPPLEK_URL}

Generate platform-specific posts in this exact format:

TikTok: [1 fun line <120 chars]
WhatsApp: [2-3 lines. Include phone number, warranty, delivery]
Facebook: [3-4 engaging sentences]
Instagram: [2-3 stylish lines]
Hashtags: #TrippleK #TrippleKKE #PhoneDealsKE
    """
    try:
        chat = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=550,
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        return f"Groq error: {str(e)}"

# ----------------------------
# UI
# ----------------------------
st.title("📱 Tripple K Phone Specs & Ad Generator")
st.caption("Get specs → Generate & copy social posts for Tripple K")

phone_query = st.text_input("🔍 Search a phone (e.g., Tecno Spark 20)", "")

if st.button("Get Phones"):
    if not phone_query.strip():
        st.error("Enter a phone name")
    else:
        results, err = fetch_search_results(phone_query)
        if err:
            st.error(err)
        else:
            st.session_state["search_results"] = results

if "search_results" in st.session_state:
    names = [r["name"] for r in st.session_state["search_results"]]
    selected_name = st.selectbox("Select phone:", names, index=0)
    selected = next(r for r in st.session_state["search_results"] if r["name"] == selected_name)

    details, err = fetch_phone_details(selected["id"])
    if err:
        st.error(err)
        st.stop()

    clean = parse_specs(details)
    st.session_state["current_phone"] = clean

    # BIG TITLE + LAUNCH INFO
    st.markdown(f'<h1 style="color:{BRAND_MAROON};">{clean["name"]}</h1>', unsafe_allow_html=True)
    launched = clean["launched"]
    announced = launched.get("announced", "N/A")
    status = launched.get("status", "N/A")
    market_duration = time_since_release(status) if "Released" in status else "Not released"
    st.caption(f"Announced: {announced} | {market_duration}")

    # IMAGE + SPECS
    col1, col2 = st.columns([1, 1.5])
    with col1:
        img_url = clean["cover"]
        if img_url:
            st.image(img_url, use_container_width=True)
            try:
                img_data = requests.get(img_url, timeout=10).content
                st.download_button("💾 Download Image", img_data, f"{clean['name']}.jpg")
            except:
                st.caption("Image download unavailable")
    with col2:
        spec_lines = [
            f"🖥️ **Screen**: {clean['screen']}",
            f"🧠 **RAM**: {clean['ram']}",
            f"💾 **Storage**: {clean['storage']}",
            f"🔋 **Battery**: {clean['battery']}",
            f"⚙️ **Chip**: {clean['chipset']}",
            f"📸 **Camera**: {clean['camera']}",
            f"🪟 **OS**: {clean['os']}"
        ]
        spec_text = "\n".join(spec_lines)
        st.markdown(spec_text)
        st.code(spec_text, language="text")

    # GROQ SECTION
    if client:
        st.divider()
        st.subheader("📣 Generate Social Posts")

        persona = st.selectbox(
            "🎯 Target Persona",
            ["All Kenyan buyers", "Budget students", "Tech-savvy professionals", "Camera creators", "Business executives"],
            index=0
        )
        tone = st.selectbox("🎨 Brand Tone", ["Playful", "Rational", "Luxury", "FOMO"], index=0)

        if st.button("✨ Generate with Groq"):
            with st.spinner("Generating..."):
                raw_copy = generate_social_post(clean, persona, tone)
                st.session_state["social_copy"] = raw_copy

    # DISPLAY SOCIAL POSTS WITH COPY BUTTONS
    if "social_copy" in st.session_state:
        st.divider()
        st.subheader("📤 Copy to Social Media")
        raw = st.session_state["social_copy"]
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        posts = {"TikTok": "", "WhatsApp": "", "Facebook": "", "Instagram": "", "Hashtags": ""}
        current = None
        for line in lines:
            if line.startswith("TikTok:"):
                current = "TikTok"
                posts[current] = line.replace("TikTok:", "").strip()
            elif line.startswith("WhatsApp:"):
                current = "WhatsApp"
                posts[current] = line.replace("WhatsApp:", "").strip()
            elif line.startswith("Facebook:"):
                current = "Facebook"
                posts[current] = line.replace("Facebook:", "").strip()
            elif line.startswith("Instagram:"):
                current = "Instagram"
                posts[current] = line.replace("Instagram:", "").strip()
            elif line.startswith("Hashtags:"):
                current = "Hashtags"
                posts[current] = line.replace("Hashtags:", "").strip()
            elif current:
                posts[current] += " " + line

        for plat, text in posts.items():
            if text:
                st.text_area(f"{plat}", text, height=80, key=f"ta_{plat}")
                copy_button(text, f"📋 Copy {plat}")

# FOOTER
st.divider()
st.caption(f"© Tripple K Communications | {TRIPPLEK_URL}")