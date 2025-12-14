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
}}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# HELPERS
# ----------------------------
def time_since_release(release_str: str) -> str:
    try:
        # Parse "2025, February 03"
        clean = release_str.replace("Released ", "").strip()
        date = parser.parse(clean)
        delta = datetime.now() - date
        days = delta.days
        if days < 0:
            return "Not yet released"
        elif days < 7:
            return f"{days} day{'s' if days != 1 else ''} in market"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} in market"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''} in market"
        else:
            years = days // 365
            return f"{years} year{'s' if years != 1 else ''} in market"
    except:
        return "Unknown release date"

def fetch_phone_specs(query: str):
    try:
        search_res = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={query}", timeout=10)
        search_res.raise_for_status()
        results = search_res.json()
        if not results:
            return None, "No results found", []
        return results, None, results
    except Exception as e:
        return None, f"Search failed: {str(e)}", []

def get_full_specs(phone_id: str):
    try:
        detail_res = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{phone_id}", timeout=10)
        detail_res.raise_for_status()
        return detail_res.json()
    except Exception as e:
        st.error(f"Detail fetch error: {e}")
        return None

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
        "cover": raw.get("image", "").strip(),
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

# ----------------------------
# GROQ PROMPT
# ----------------------------
def generate_social_post(phone_data: dict, persona: str, tone: str):
    name = phone_data["name"]
    specs = phone_data["raw"]
    prompt = f"""
You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

PHONE: {name}
PERSONA: {persona}
TONE: {tone}

FULL SPECS:
{specs}

TRIPPLE K VALUE PROPS (mention at least 2):
- Accredited distributor → 100% genuine phones
- Official manufacturer warranty
- Pay on delivery
- Fast Nairobi delivery
- Call {TRIPPLEK_PHONE} or visit {TRIPPLEK_URL}

TASK: Generate playful, platform-optimized social posts for Kenya.

OUTPUT FORMAT:

TikTok: [1 fun line <120 chars]
WhatsApp: [2-3 lines with phone number, warranty, delivery]
Facebook: [3-4 engaging sentences]
Instagram: [2-3 lifestyle-focused lines]
Hashtags: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only.
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
st.caption("Powered by GSM Arena + Groq AI | www.tripplek.co.ke")

phone_query = st.text_input("🔍 Search a phone (e.g., Tecno Spark 20)", "")

if st.button("Get Phones"):
    if not phone_query:
        st.error("Enter a phone name")
    else:
        results, err, raw_results = fetch_phone_specs(phone_query)
        if err:
            st.error(err)
        else:
            st.session_state["search_results"] = results
            st.session_state["raw_search"] = raw_results

# Show selection dropdown if results exist
if "search_results" in st.session_state:
    names = [r["name"] for r in st.session_state["search_results"]]
    selected_name = st.selectbox("Choose phone:", names, index=0)
    selected = next(r for r in st.session_state["search_results"] if r["name"] == selected_name)

    # Fetch full specs
    full_specs = get_full_specs(selected["id"])
    if not full_specs:
        st.stop()

    # Parse and save
    clean = parse_specs(full_specs)
    st.session_state["current_phone"] = clean

    # Display
    st.markdown(f'<h1 style="color:{BRAND_MAROON};">{clean["name"]}</h1>', unsafe_allow_html=True)

    # Launch info
    launched = clean["launched"]
    announced = launched.get("announced", "N/A")
    status = launched.get("status", "N/A")
    market_duration = time_since_release(status) if "Released" in status else "Not released"
    st.caption(f"Announced: {announced} | {market_duration}")

    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.image(clean["cover"], use_container_width=True)
        img_data = requests.get(clean["cover"]).content
        st.download_button("💾 Download Image", img_data, f"{clean['name']}.jpg")
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

    with st.expander("📊 Full Specs (JSON)"):
        st.json(clean["raw"])

    # --- Groq Section ---
    st.divider()
    st.subheader("📣 Generate Social Posts")

    persona = st.selectbox(
        "🎯 Target Persona",
        [
            "All Kenyan buyers",
            "Budget students",
            "Tech-savvy professionals",
            "Camera creators",
            "Business executives"
        ],
        index=0
    )
    tone = st.selectbox(
        "🎨 Brand Tone",
        ["Playful", "Rational", "Luxury", "FOMO"],
        index=0
    )

    if client and st.button("✨ Generate with Groq (Llama 3.2 1B)"):
        with st.spinner("Generating..."):
            ad_copy = generate_social_post(clean, persona, tone)
            st.text_area("Posts", ad_copy, height=300)

st.divider()
st.caption(f"© Tripple K Communications | {TRIPPLEK_URL}")