import streamlit as st
import requests
from groq import Groq
import os
import re

# ----------------------------
# CONFIG
# ----------------------------
GROQ_KEY = st.secrets.get("groq_key", "")
if GROQ_KEY:
    client = Groq(api_key=GROQ_KEY)
else:
    client = None

# Branding
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
# GSM API FETCHER
# ----------------------------
def fetch_phone_specs(query: str):
    try:
        # Search
        search_res = requests.get(f"https://tkphsp2.vercel.app/gsm/search?q={query}", timeout=10)
        search_res.raise_for_status()
        results = search_res.json()
        if not results:
            return None, "No results found"

        phone = results[0]
        # Get full specs
        detail_res = requests.get(f"https://tkphsp2.vercel.app/gsm/info/{phone['id']}", timeout=10)
        detail_res.raise_for_status()
        specs = detail_res.json()

        # Parse RAM & Storage from memory array
        ram = "N/A"
        storage = "N/A"
        for mem in specs.get("memory", []):
            if mem.get("label") == "internal":
                val = mem.get("value", "")
                # Extract RAM (e.g., "4GB RAM")
                ram_match = re.search(r"(\d+GB)\s+RAM", val)
                if ram_match:
                    ram = ram_match.group(1)
                # Extract storage (e.g., "64GB")
                storage_match = re.search(r"(\d+GB)(?!\s+RAM)", val)
                if storage_match:
                    storage = storage_match.group(1)

        clean = {
            "name": phone["name"],
            "cover": phone["image"].strip(),
            "screen": f"{specs['display']['size']} ({specs['display']['resolution']})",
            "ram": ram,
            "storage": storage,
            "battery": specs["battery"]["battType"],
            "chipset": specs["platform"]["chipset"],
            "camera": specs["mainCamera"]["mainModules"],
            "os": specs["platform"]["os"],
            "raw": specs  # full data for Groq
        }
        return clean, None
    except Exception as e:
        return None, f"Fetch failed: {str(e)}"

# ----------------------------
# GROQ PROMPT (ENHANCED)
# ----------------------------
def generate_social_post(phone_data: dict):
    specs = phone_data["raw"]
    name = phone_data["name"]
    
    prompt = f"""
You are the official marketing AI for Tripple K Communications (www.tripplek.co.ke), Kenya’s trusted phone store.

PHONE: {name}

FULL SPECS:
{specs}

TRIPPLE K VALUE PROPS (must mention at least 2):
- Accredited distributor → 100% genuine phones
- Official manufacturer warranty
- Pay on delivery (no upfront payment)
- Fast Nairobi delivery
- Visit www.tripplek.co.ke or call {TRIPPLEK_PHONE}

TASK: Generate platform-specific social posts.

RULES:
- Use a PLAYFUL, energetic Kenyan tone (emojis ok!)
- Highlight key specs naturally (screen, battery, camera, etc.)
- Include clear CTA and value props
- Hashtags: #TrippleK #TrippleKKE #PhoneDealsKE

OUTPUT FORMAT:

TikTok: [1 fun line <120 chars]
WhatsApp: [2-3 lines. Include phone number, warranty, pay on delivery]
Facebook: [3-4 sentences. Community-focused, highlight trust]
Instagram: [2-3 stylish lines. Focus on design & lifestyle]
Hashtags: #TrippleK ...

Plain text only. No markdown.
    """.strip()

    try:
        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=500,
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        return f"Groq error: {str(e)}"

# ----------------------------
# UI
# ----------------------------
st.title("📱 Tripple K Phone Specs & Ad Generator")
st.caption("Get specs → Generate social posts for Tripple K")

phone_query = st.text_input("Enter phone model (e.g., Tecno Spark 20, iPhone 16)", "")

if st.button("🔍 Get Phone Specs"):
    if not phone_query:
        st.error("Please enter a phone name")
    else:
        with st.spinner("Fetching specs..."):
            data, err = fetch_phone_specs(phone_query)
            if err:
                st.error(err)
            else:
                st.session_state["phone"] = data

# Show phone if fetched
if "phone" in st.session_state:
    p = st.session_state["phone"]
    
    # BIG TITLE
    st.markdown(f'<h1 style="color:{BRAND_MAROON};">{p["name"]}</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.image(p["cover"], use_container_width=True)
        img_bytes = requests.get(p["cover"]).content
        st.download_button("💾 Download Image", img_bytes, f"{p['name']}.jpg")
    
    with col2:
        spec_lines = [
            f"🖥️ **Screen**: {p['screen']}",
            f"🧠 **RAM**: {p['ram']}",
            f"💾 **Storage**: {p['storage']}",
            f"🔋 **Battery**: {p['battery']}",
            f"⚙️ **Chip**: {p['chipset']}",
            f"📸 **Camera**: {p['camera']}",
            f"🪟 **OS**: {p['os']}"
        ]
        spec_text = "\n".join(spec_lines)
        st.markdown(spec_text)
        st.code(spec_text, language="text")

    # Full specs expander
    with st.expander("📊 Full Phone Specs (JSON)"):
        st.json(p["raw"])

    # Groq button
    if client and st.button("📣 Generate Tripple K Social Posts"):
        with st.spinner("Generating with Groq AI..."):
            ad_copy = generate_social_post(p)
            st.subheader("Your Ready-to-Use Ads")
            st.text_area("All Posts", ad_copy, height=300)

# Footer
st.divider()
st.caption(f"Powered by Tripple K Communications | {TRIPPLEK_URL}")