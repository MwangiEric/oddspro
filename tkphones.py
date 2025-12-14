import streamlit as st
import requests
import json
from groq import Groq
import os

# ----------------------------
# Config
# ----------------------------
API_BASE = "https://tkphsp2.vercel.app/gsm"
GROQ_API_KEY = os.getenv("groq_key")  # Note: key name is `groq_key`

st.set_page_config(
    page_title="📱 Tripple K Phone Finder",
    page_icon="📱",
    layout="centered"
)

st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stButton>button {width: 100%; margin-top: 0.5rem;}
        .phone-title {font-size: 2.2rem; font-weight: bold; color: #1e3a8a; margin: 1rem 0;}
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------
# Copy to Clipboard (JS fallback)
# ----------------------------
def copy_to_clipboard(text):
    st.code(text, language=None)
    escaped = text.replace("`", "\\`").replace("\n", "\\n")
    st.markdown(
        f"""
        <button onclick="navigator.clipboard.writeText(`{escaped}`)" 
                style="background:#4CAF50; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; margin-top:8px;">
            📋 Copy to Clipboard
        </button>
        """,
        unsafe_allow_html=True
    )

# ----------------------------
# Generate Social Post via Groq
# ----------------------------
def generate_social_post(phone_name, specs, platform):
    if not GROQ_API_KEY:
        return "[Groq disabled: set `groq_key` in secrets]"

    client = Groq(api_key=GROQ_API_KEY)

    # Format specs in requested order
    display = specs.get("display", {})
    screen = f"{display.get('size', 'N/A')} ({display.get('resolution', 'N/A')})"
    platform_info = specs.get("platform", {})
    ram = platform_info.get("ram", "N/A")
    storage = specs.get("memory", {}).get("card_slot", "N/A")
    # Try internal storage if card_slot isn't descriptive
    internal = specs.get("memory", {}).get("internal", "N/A")
    storage = internal if internal != "N/A" else storage
    battery = specs.get("battery", {}).get("type", "N/A")

    spec_summary = f"Screen: {screen}, RAM: {ram}, Storage: {storage}, Battery: {battery}"

    prompt = f"""
You are a social media manager for "Tripple K Communications", a phone store in Kenya (website: www.tripplek.co.ke).

Create a short, engaging {platform} post for the phone "{phone_name}".

Use this spec summary:
{spec_summary}

Guidelines:
- Include a catchy title or opening line.
- Add 2–4 relevant hashtags (e.g., #TrippleK, #KenyaTech, #NairobiDeals).
- Include a clear call-to-action: "Visit www.tripplek.co.ke or your nearest Tripple K store!"
- Use emojis and a playful but professional Kenyan tone.
- Keep it platform-optimized:
  - WhatsApp: Friendly, message-style, 1–3 lines.
  - TikTok: Punchy, hype, Gen-Z slang, under 200 chars.
  - Facebook: Slightly more detailed, community-focused, 2–4 lines.

Do NOT mention prices unless provided.
    """.strip()

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            max_tokens=150,
            temperature=0.9,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Groq error: {str(e)}"

# ----------------------------
# UI
# ----------------------------
st.title("📱 Tripple K Phone Finder")
st.caption("Find the perfect phone — powered by GSM Arena & Groq AI")

query = st.text_input("🔍 Search a phone (e.g., Tecno Spark 20, Infinix Hot 30)", "")

if query:
    with st.spinner(f"Searching for **{query}**..."):
        try:
            res = requests.get(f"{API_BASE}/search?q={query}", timeout=10)
            res.raise_for_status()
            results = res.json()

            if not results:
                st.warning("No phones found. Try another name!")
                st.stop()

            options = {r["name"]: r for r in results}
            selected_name = st.selectbox("Choose a phone:", options.keys())
            phone = options[selected_name]

            specs_res = requests.get(f"{API_BASE}/info/{phone['id']}", timeout=10)
            specs_res.raise_for_status()
            specs = specs_res.json()

            # --- BIG PHONE NAME ---
            st.markdown(f'<div class="phone-title">{phone["name"]}</div>', unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1.5])

            with col1:
                img_url = phone.get("image")
                if img_url:
                    st.image(img_url, use_container_width=True)
                    try:
                        img_data = requests.get(img_url).content
                        st.download_button(
                            "💾 Download Image",
                            data=img_data,
                            file_name=f"{phone['name'].replace(' ', '_')}.jpg",
                            mime="image/jpeg"
                        )
                    except:
                        st.caption("Image download failed")
                else:
                    st.image("https://via.placeholder.com/200?text=No+Image", use_container_width=True)

            with col2:
                # Ordered specs: Screen → RAM → Storage → Battery → Rest
                display = specs.get("display", {})
                screen = f"{display.get('size', 'N/A')} ({display.get('resolution', 'N/A')})"
                platform_info = specs.get("platform", {})
                ram = platform_info.get("ram", "N/A")
                memory = specs.get("memory", {})
                storage = memory.get("internal", "N/A")
                battery = specs.get("battery", {}).get("type", "N/A")
                chipset = platform_info.get("chipset", "N/A")
                camera = specs.get("camera", {})
                main_cam = camera.get("single") or camera.get("triple") or "N/A"

                spec_lines = [
                    f"🖥️ **Screen**: {screen}",
                    f"🧠 **RAM**: {ram}",
                    f"💾 **Storage**: {storage}",
                    f"🔋 **Battery**: {battery}",
                    f"⚙️ **Chip**: {chipset}",
                    f"📸 **Main Camera**: {main_cam}"
                ]
                spec_text = "\n".join(spec_lines)
                st.markdown(spec_text)
                copy_to_clipboard(spec_text)

            # --- Social Posts ---
            st.divider()
            st.subheader("📣 Generate Social Posts for Tripple K")

            platforms = ["WhatsApp", "TikTok", "Facebook"]
            cols = st.columns(3)
            for idx, platform in enumerate(platforms):
                with cols[idx]:
                    if st.button(f"📱 {platform}"):
                        with st.spinner(f"Generating {platform} post..."):
                            post = generate_social_post(phone["name"], specs, platform)
                            st.info(post)
                            copy_to_clipboard(post)

            # --- Raw JSON ---
            with st.expander("📊 Full Specs (JSON)"):
                st.json(specs)

        except requests.exceptions.RequestException as e:
            st.error(f"❌ API Error: {e}")
        except Exception as e:
            st.exception("Unexpected error")

# ----------------------------
# Footer
# ----------------------------
st.markdown(
    """
    <hr>
    <center>
        <small>
            Powered by <a href="https://www.tripplek.co.ke" target="_blank">Tripple K Communications</a> 🇰🇪
        </small>
    </center>
    """,
    unsafe_allow_html=True
)