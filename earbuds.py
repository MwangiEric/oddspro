import streamlit as st
import requests
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO

# ============================================================================
# CONFIGURATION
# ============================================================================
API_URL = "https://moon-shine.vercel.app"
DEFAULT_JERSEY = "https://i.imgur.com/8fS73O4.png"  # Fallback blank template

st.set_page_config(page_title="Moonshine Jersey Studio", layout="wide")

# Initialize session state for picking and storing assets
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_design_url" not in st.session_state:
    st.session_state.selected_design_url = None

def get_pil_image(url):
    """Utility to fetch and convert online images to PIL RGBA."""
    try:
        resp = requests.get(url, timeout=10)
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        st.error(f"Error fetching image: {e}")
        return None

# ============================================================================
# APP LAYOUT
# ============================================================================
st.sidebar.title("🎨 Moonshine Studio")
st.sidebar.info("Jersey & Streetwear Customizer v3.2.0")

tab1, tab2 = st.tabs(["🔍 1. Pick Style", "👕 2. Jersey Canvas"])

# ----------------------------------------------------------------------------
# TAB 1: ASSET DISCOVERY (Thumbnail Picks)
# ----------------------------------------------------------------------------
with tab1:
    st.header("Search Graffiti & Calligraphy")
    c1, c2 = st.columns([3, 1])
    
    with c1:
        query = st.text_input("Design Theme", "Calligraphy graffiti tag")
    with c2:
        category = st.selectbox("Category", ["graffiti", "typography", "all", "vectors"])

    if st.button("🔎 Find Styles", type="primary", use_container_width=True):
        with st.spinner("Searching moon-shine.vercel.app..."):
            # Using your API parameters
            params = {"q": query, "c": category, "e": "png", "w": 600, "h": 600, "limit": 20}
            try:
                resp = requests.get(f"{API_URL}/api/search", params=params)
                st.session_state.search_results = resp.json().get("assets", [])
            except:
                st.error("API is currently offline.")

    # Showing thumbnails for the user to pick
    if st.session_state.search_results:
        st.divider()
        cols = st.columns(4)
        for idx, asset in enumerate(st.session_state.search_results):
            with cols[idx % 4]:
                # Show thumbnail
                st.image(asset.get("thumb", asset["img"]), use_container_width=True)
                # Selection logic: Store the high-res URL when clicked
                if st.button("Select Design", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.selected_design_url = asset["img"]
                    st.toast("🔥 High-res style loaded to canvas!")

# ----------------------------------------------------------------------------
# TAB 2: JERSEY CANVAS (PIL Drawing)
# ----------------------------------------------------------------------------
with tab2:
    if not st.session_state.selected_design_url:
        st.warning("⚠️ Please select a style from Step 1 first.")
    else:
        col_ctrl, col_view = st.columns([1, 2])
        
        with col_ctrl:
            st.subheader("Jersey Setup")
            jersey_club = st.selectbox("Premier League Base", [
                "Arsenal 25/26 home jersey", 
                "Chelsea 25/26 home kit", 
                "Man City sky blue jersey", 
                "Liverpool red football kit",
                "Man United red kit mockup"
            ])
            
            st.divider()
            name = st.text_input("Player Name", "MOONSHINE")
            num = st.text_input("Number", "26")
            p_color = st.color_picker("Print Color", "#FFD700")

            # Canvas Controls
            scale = st.slider("Design Scale", 0.1, 1.0, 0.45)
            y_pos = st.slider("Chest Position", 100, 1000, 380)
            
            render_btn = st.button("🎯 Render Final Print", type="primary", use_container_width=True)

        with col_view:
            if render_btn:
                with st.spinner("Baking High-Res Jersey..."):
                    # 1. Fetch Jersey Base from API
                    j_resp = requests.get(f"{API_URL}/api/search", params={"q": jersey_club, "limit": 1})
                    j_assets = j_resp.json().get("assets")
                    j_url = j_assets[0]["img"] if j_assets else DEFAULT_JERSEY
                    
                    # 2. Open Layers
                    canvas = get_pil_image(j_url).resize((1200, 1500))
                    design = get_pil_image(st.session_state.selected_design_url)
                    
                    # 3. Scale and Draw Design
                    dw = int(canvas.width * scale)
                    dh = int(dw * (design.height / design.width))
                    design = design.resize((dw, dh), Image.Resampling.LANCZOS)
                    
                    # Composite layers
                    canvas.alpha_composite(design, ((canvas.width - dw)//2, y_pos))
                    
                    # 4. Add Custom Text
                    draw = ImageDraw.Draw(canvas)
                    try:
                        # Draw Name (Top)
                        draw.text((600, y_pos - 80), name, fill=p_color, anchor="mm")
                        # Draw Number (Bottom)
                        draw.text((600, y_pos + dh + 70), num, fill=p_color, anchor="mm")
                    except:
                        pass # Fallback if text drawing fails

                    st.image(canvas, caption=f"Custom {jersey_club} Preview", use_container_width=True)
                    
                    # 5. Export
                    buf = BytesIO()
                    canvas.save(buf, format="PNG")
                    st.download_button("📥 Download Design", buf.getvalue(), "jersey_final.png", "image/png", use_container_width=True)
