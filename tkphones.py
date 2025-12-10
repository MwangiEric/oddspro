#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from groq import Groq

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
PEXELS_KEY = st.secrets.get("pexels_api_key", "")
if not GROQ_KEY or not PEXELS_KEY:
    st.error("❌ Add `groq_key` and `pexels_api_key` to `.streamlit/secrets.toml`")
    st.stop()

client = Groq(api_key=GROQ_KEY)
PEXELS_HEADERS = {"Authorization": PEXELS_KEY}
SEARX_URL = "https://searxng-587s.onrender.com/search"
MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
LAST_CALL = 0
RATE_LIMIT = 3
DEFAULT_PERSONA = "All Kenyan buyers"
DEFAULT_TONE = "Rational"
####################################################################


def searx_all_results(phone: str) -> list[dict]:
    global LAST_CALL
    wait = RATE_LIMIT - (time.time() - LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    LAST_CALL = time.time()

    query = f"{phone} price Kenya"
    try:
        r = requests.get(
            SEARX_URL,
            params={
                "q": query,
                "format": "json",
                "language": "en",
                "safesearch": "0",
            },
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        raw = r.json().get("results", [])
        enriched = []
        for i, res in enumerate(raw, 1):
            title = res.get("title", "")
            content = res.get("content", "")
            url = res.get("url", "")
            full_text = f"{title} {content} {url}".lower()
            price_match = re.search(
                r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)(?!\s*(?:gb|mb|gbp|usd|eur))',
                full_text,
                re.IGNORECASE
            )
            price = f"KSh {price_match.group(1)}" if price_match else None
            enriched.append({
                "position": i,
                "title": title[:180],
                "url": url,
                "content": content[:300],
                "price_ksh": price,
            })
        return enriched[:25]
    except Exception as e:
        st.warning(f"⚠️ SearX error: {str(e)[:60]}")
        return []


def build_groq_context(results: list[dict]) -> str:
    lines = []
    for r in results:
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        lines.append(f"Title: {r['title']}{price}\nURL: {r['url']}\nSnippet: {r['content']}\n---")
    return "\n".join(lines) if lines else "No results found."


def search_pexels_images(query: str, per_page: int = 6) -> list[dict]:
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers=PEXELS_HEADERS,
            params={"query": query, "per_page": per_page, "orientation": "landscape"},
            timeout=10,
        )
        if resp.status_code == 200:
            return [{"url": photo["src"]["large"], "alt": photo["alt"] or query} for photo in resp.json().get("photos", [])]
    except Exception as e:
        st.warning(f"🖼️ Pexels fetch failed: {str(e)[:50]}")
    return []


def parse_groq_response(raw: str):
    sections = ["---PRICE---", "---SPECS---", "---INSIGHTS---", "---VISUALS---", "---COPY---"]
    parts = [raw]
    for sep in sections[1:]:
        new_parts = []
        for p in parts:
            new_parts.extend(p.split(sep, 1))
        parts = new_parts
    # Ensure we have 5 parts
    while len(parts) < 5:
        parts.append("")
    return (
        parts[0].strip(),  # before PRICE
        parts[1].strip(),  # SPECS
        parts[2].strip(),  # INSIGHTS
        parts[3].strip(),  # VISUALS
        parts[4].strip(),  # COPY
    )


def generate_marketing(phone: str, web_context: str, persona: str, tone: str) -> tuple:
    prompt = f"""You are a senior mobile marketing strategist for Kenya.

PHONE: {phone}
TARGET: {persona}
TONE: {tone}

WEB RESULTS:
{web_context}

INSTRUCTIONS — Return EXACTLY these 5 sections, separated by:
---PRICE---
---SPECS---
---INSIGHTS---
---VISUALS---
---COPY---

1. PRICE:
   - For EVERY result with a visible KSh price, output:
     "Retailer - KSh X,XXX - https://..."
   - Extract retailer name from domain (e.g., jumia.co.ke → Jumia)
   - NO LIMIT — list all verified prices.

2. SPECS:
   - Infer up to 6 key specs from web results.

3. INSIGHTS:
   - Selling Points, Tactics, Competitive Edge, Market Gap.

4. VISUALS:
   - Describe 2 image ad concepts for Kenya:
     • Concept 1: Scene, colors, text idea, mood
     • Concept 2: Scene, colors, text idea, mood
   - Include local context: Nairobi, students, M-Pesa, etc.

5. COPY:
   - BANNERS: 2 lines (≤40 chars)
   - SOCIAL: Tweet, IG, FB (platform-optimized)
   - HASHTAGS: 10 tags including #Kenya #PhoneDealsKE

RULES: Plain text only. No markdown.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            timeout=50,
            max_tokens=2200,
        )
        raw = completion.choices[0].message.content.strip()
        return parse_groq_response(raw)
    except Exception as e:
        st.error(f"🤖 Groq error: {e}")
        return "", "", "", "", ""


############################ STREAMLIT UI ####################################
st.set_page_config(page_title="📱 Kenya Phone Ads Pro + Images", layout="wide")
st.title("📱 Kenya Phone Ads Pro")
st.caption("Prices • Specs • Insights • Social Copy • Visual Concepts + Pexels Images")

phone = st.text_input("🔍 Phone model (e.g., Tecno Spark 20)", value="Samsung Galaxy A17")
persona = st.selectbox("👤 Buyer Persona", 
                      ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Status execs"], 
                      index=0)
tone = st.selectbox("🎨 Brand Tone", 
                   ["Rational", "Playful", "Luxury", "FOMO"], 
                   index=0)

if st.button("🚀 Generate Full Marketing Kit + Visuals", type="primary"):
    with st.status("🔍 Researching & generating...", expanded=True) as status:
        st.write("🌐 Fetching Kenyan offers...")
        web_results = searx_all_results(phone)
        web_context = build_groq_context(web_results)

        st.write("🧠 Generating strategy & visuals...")
        price_block, specs_block, insights_block, visuals_block, copy_block = generate_marketing(
            phone, web_context, persona, tone
        )

        # Extract keywords for Pexels
        visual_query = f"Kenyan {persona.lower()} using smartphone"
        if "student" in persona.lower():
            visual_query = "Kenyan university student smartphone"
        elif "camera" in persona.lower():
            visual_query = "Kenyan photographer smartphone camera"
        else:
            visual_query = "young Kenyan person using phone Nairobi"

        st.write("🖼️ Fetching Pexels images...")
        pexels_images = search_pexels_images(visual_query, per_page=6)
        status.update(label="✅ Done! Full kit ready.", state="complete", expanded=False)

    # ------- PRICE TABLE -------
    st.subheader("🛒 All Verified Kenyan Prices")
    price_lines = [line.strip() for line in price_block.splitlines() if line.strip()]
    if price_lines:
        rows = []
        for line in price_lines:
            parts = line.split(" - ")
            if len(parts) >= 3:
                retailer = parts[0]
                price = parts[1]
                url = " - ".join(parts[2:])
                rows.append({"Retailer": retailer, "Price (KSh)": price, "Link": url})
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No KSh prices found.")

    # ------- SPECS -------
    st.subheader("📱 Key Specs")
    st.text(specs_block or "Not extracted.")

    # ------- INSIGHTS -------
    st.subheader("📈 Strategic Insights")
    st.text(insights_block or "None generated.")

    # ------- VISUAL CONCEPTS + IMAGES -------
    st.subheader("🎨 Visual Ad Concepts (from AI) + Pexels Images")
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.markdown("**🖼️ AI Visual Brief**")
        st.text(visuals_block or "No concepts generated.")
    with c2:
        st.markdown("**📸 Pexels Image Suggestions**")
        if pexels_images:
            cols = st.columns(2)
            for i, img in enumerate(pexels_images[:4]):
                with cols[i % 2]:
                    st.image(img["url"], use_container_width=True, caption=f"Image {i+1}")
        else:
            st.caption("No images found on Pexels.")

    # ------- COPY -------
    st.subheader("📣 Ready-to-Post Copy")
    lines = [l.strip() for l in copy_block.splitlines() if l.strip()]
    banners = []
    social = {"Tweet": "", "IG": "", "FB": ""}
    hashtags = ""
    in_social = False
    for line in lines:
        if line.startswith("BANNERS:"):
            continue
        elif not in_social and not any(x in line for x in ["IG:", "FB:", "#"]):
            if not banners or len(banners) < 2:
                banners.append(line)
        elif "IG:" in line:
            social["IG"] = line.replace("IG:", "").strip()
            in_social = True
        elif "FB:" in line:
            social["FB"] = line.replace("FB:", "").strip()
        elif line.startswith("Tweet") or (in_social == False and "KSh" in line and len(line) < 250):
            social["Tweet"] = line
            in_social = True
        elif line.startswith("#"):
            hashtags = line

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**🖼️ Banner Text**")
        for b in banners[:2]:
            st.code(b, language="plaintext")
    with c4:
        st.markdown("**📲 Social Posts**")
        st.text_area("Twitter (X)", social["Tweet"], height=80)
        st.text_area("Instagram", social["IG"], height=80)
        st.text_area("Facebook", social["FB"], height=80)
        st.text_input("Hashtags", hashtags)