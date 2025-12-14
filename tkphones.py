import streamlit as st
import requests
from groq import Groq
import os
import re
from dateutil import parser
from datetime import datetime
import json

# ----------------------------
# CONFIG
# ----------------------------
GROQ_KEY = st.secrets.get("groq_key", "")
client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
# WARNING: "llama-3.1-8b-instant" is NOT a valid Groq model.
# Use one of: "llama3-8b-8192", "llama3-70b-8192", "llama3-1b-8192"
MODEL = "llama-3.1-8b-instant"  # ✅ Valid Groq model

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
    margin-top: 5px;
}}
.error-box {{
    background: #ffebee; color: #c62828; padding: 12px; border-radius: 6px;
    border-left: 4px solid #c62828;
}}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# PROMPT BUILDER
# ----------------------------
def build_groq_prompt(phone_dict: dict, persona: str, tone: str) -> str:
    return f"""
You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

PHONE: {phone_dict['name']}
PERSONA: {persona}
TONE: {tone}

FULL SPECS:
{json.dumps(phone_dict['raw'], indent=2)}

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
    """.strip()

# ----------------------------
# SAFE API CALL
# ----------------------------
def safe_api_call(url: str):
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 429:
            return None, "⚠️ Rate limited (429): Too many requests. Try again later."
        if res.status_code != 200:
            return None, f"❌ Server error: HTTP {res.status_code}"
        return res.json(), None
    except requests.exceptions.Timeout:
        return None, "⏱️ Request timed out"
    except requests.exceptions.RequestException as e:
        return None, f"🌐 Network error: {str(e)}"
    except ValueError:
        return None, "📄 Invalid response (not JSON – possibly blocked)"

# ----------------------------
# HELPERS
# ----------------------------
def time_since_release(status: str) -> str:
    try:
        clean = status.replace("Released ", "").strip()
        date = parser.parse(clean)
        days = (datetime.now() - date).days
        if days < 0: return "Not released"
        if days < 7: return f"{days} day{'s' if days != 1 else ''} in market"
        if days < 30: return f"{days//7} week{'s' if days//7 != 1 else ''} in market"
        if days < 365: return f"{days//30} month{'s' if days//30 != 1 else ''} in market"
        return f"{days//365} year{'s' if days//365 != 1 else ''} in market"
    except:
        return "Unknown"

def parse_specs(raw):
    ram = storage = "N/A"
    for mem in raw.get("memory", []):
        if mem.get("label") == "internal":
            val = mem.get("value", "")
            ram_match = re.search(r"(\d+GB)\s+RAM", val)
            storage_match = re.search(r"(\d+GB)(?!\s+RAM)", val)
            if ram_match: ram = ram_match.group(1)
            if storage_match: storage = storage_match.group(1)
    return {
        "name": raw["name"],
        "cover": (raw.get("image") or raw.get("cover", "")).strip(),
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
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("`", "\\`")
    st.markdown(f"""
    <button class="copy-btn" onclick='navigator.clipboard.writeText("{escaped}")'>{label}</button>
    """, unsafe_allow_html=True)

# ----------------------------
# MAIN APP
# ----------------------------
st.title("📱 Tripple K Phone Specs & Ad Generator")
st.caption("Get specs → Generate & copy social posts for Tripple K")

phone_query = st.text_input("🔍 Search a phone (e.g., Tecno Spark 20)", "")

if st.button("Get Phones"):
    if not phone_query.strip():
        st.error("❌ Please enter a phone name")
        st.stop()

    with st.spinner("🔍 Searching phones..."):
        # Primary: your Vercel (raffyxyz)
        url1 = f"https://tkphsp2.vercel.app/gsm/search?q={requests.utils.quote(phone_query)}"
        results, err = safe_api_call(url1)
        
        # Fallback: azharimm v2
        if err and "429" in err:
            st.warning("⚠️ Your Vercel API is rate-limited (429). Using public backup...")
            url2 = f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(phone_query)}"
            results, err = safe_api_call(url2)

        if err or not results:
            st.error(f"❌ Failed to fetch phone: {err or 'No results'}")
            st.stop()
        else:
            st.session_state["search_results"] = results

# Phone selection
if "search_results" in st.session_state:
    names = [r["name"] for r in st.session_state["search_results"]]
    selected_name = st.selectbox("Select phone:", names, index=0)
    selected = next(r for r in st.session_state["search_results"] if r["name"] == selected_name)

    with st.spinner("📱 Loading full specs..."):
        details, err = safe_api_call(f"https://tkphsp2.vercel.app/gsm/info/{selected['id']}")
        if err and "429" in err:
            st.warning("⚠️ Falling back to public specs API (429 rate limit)...")
            # Fallback to azharimm v2 detail
            search_res, _ = safe_api_call(f"https://api-mobilespecs.azharimm.dev/v2/search?query={requests.utils.quote(selected_name)}")
            if search_res and len(search_res) > 0:
                slug = search_res[0]["slug"]
                details, err = safe_api_call(f"https://api-mobilespecs.azharimm.dev/{slug}")
        if err or not details:
            st.error(f"❌ Could not load specs: {err}")
            st.stop()

    clean = parse_specs(details)
    st.session_state["current_phone"] = clean
    cover_url = clean["cover"]

    st.markdown(f'<h1 style="color:{BRAND_MAROON};">{clean["name"]}</h1>', unsafe_allow_html=True)
    launched = clean["launched"]
    announced = launched.get("announced", "N/A")
    status = launched.get("status", "N/A")
    market_duration = time_since_release(status) if "Released" in status else "Not released"
    st.caption(f"Announced: {announced} | {market_duration}")

    col1, col2 = st.columns([1, 1.5])
    with col1:
        if cover_url:
            st.image(cover_url, use_container_width=True)
            try:
                img_data = requests.get(cover_url, timeout=10).content
                st.download_button("💾 Download Image", img_data, f"{clean['name']}.jpg")
            except:
                st.caption("⚠️ Image download failed")
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

    # Groq generation
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
            # ✅ phone_data is now defined in this scope
            phone_data = clean
            with st.spinner("🧠 Generating with Groq (Llama 3 8B)..."):
                prompt = build_groq_prompt(phone_data, persona, tone)
                try:
                    chat = client.chat.completions.create(
                        model=MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.85,
                        max_tokens=550,
                        timeout=30
                    )
                    ad_copy = chat.choices[0].message.content.strip()
                    st.session_state["social_copy"] = ad_copy
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg:
                        st.session_state["social_copy"] = "❌ Groq rate limit (429): Too many requests. Wait 1 minute."
                    else:
                        st.session_state["social_copy"] = f"❌ Groq error: {error_msg}"

    # Display output
    if "social_copy" in st.session_state:
        st.divider()
        st.subheader("📤 Copy to Social Media")
        raw = st.session_state["social_copy"]
        if raw.startswith("❌"):
            st.markdown(f'<div class="error-box">{raw}</div>', unsafe_allow_html=True)
        else:
            posts = {"TikTok": "", "WhatsApp": "", "Facebook": "", "Instagram": "", "Hashtags": ""}
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            current = None
            for line in lines:
                if line.startswith("TikTok:"):
                    current, posts["TikTok"] = "TikTok", line.replace("TikTok:", "").strip()
                elif line.startswith("WhatsApp:"):
                    current, posts["WhatsApp"] = "WhatsApp", line.replace("WhatsApp:", "").strip()
                elif line.startswith("Facebook:"):
                    current, posts["Facebook"] = "Facebook", line.replace("Facebook:", "").strip()
                elif line.startswith("Instagram:"):
                    current, posts["Instagram"] = "Instagram", line.replace("Instagram:", "").strip()
                elif line.startswith("Hashtags:"):
                    current, posts["Hashtags"] = "Hashtags", line.replace("Hashtags:", "").strip()
                elif current:
                    posts[current] += " " + line

            for plat, text in posts.items():
                if text:
                    st.text_area(f"{plat}", text, height=80, key=f"ta_{plat}")
                    copy_button(text, f"📋 Copy {plat}")

st.divider()
st.caption(f"© Tripple K Communications | {TRIPPLEK_URL}")