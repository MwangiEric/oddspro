#!/usr/bin/env python3
# ::: TRIPLE K PHONE AD GENERATOR – CHRISTMAS Edition :::
# Two-prompt architecture: live-data vs brand-only
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

# ---------- CONFIG ----------
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("❌ Add `groq_key` to `.streamlit/secrets.toml`")
    st.stop()

from groq import Groq
client = Groq(api_key=GROQ_KEY)

MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RATE_LIMIT = 3
LAST_CALL = 0

BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
TRIPPLEK_PHONE = "+254700123456"

NOW = datetime.now()
IS_CHRISTMAS = (NOW.month == 12 and NOW.day >= 1) or (NOW.month == 1 and NOW.day <= 10)
XMAS_HOOK = "🎄 Christmas Special! Gift-ready with warranty & fast delivery." if IS_CHRISTMAS else ""

SEARX_INSTANCES = [
    "https://searx.be/search",
    "https://search.ononoki.org/search",
    "https://searxng.site/search",
    "https://northboot.xyz/search",
]
# ----------------------------


@st.cache_resource
def wake_searx():
    for url in SEARX_INSTANCES:
        try:
            requests.get(url, params={"q": "test", "format": "json"}, timeout=8)
            return url
        except:
            continue
    return SEARX_INSTANCES[0]


def inject_css():
    st.markdown(
        f"""
    <style>
    .stButton>button{{background-color:{BRAND_MAROON};color:white;border:none;border-radius:8px;font-weight:bold;padding:0.5rem 1rem;}}
    .stButton>button:hover{{background-color:#5a0000;color:white;}}
    h1,h2,h3,h4{{color:{BRAND_MAROON} !important;}}
    .dataframe thead th{{background-color:{BRAND_GREEN};color:white !important;}}
    .main{{background-color:#F9FAF8;}}
    footer{{visibility:hidden;}}
    @media (max-width: 768px){{
        .stTextArea>div>div>textarea,.stCodeBlock{{font-size:14px !important;overflow-x:auto;white-space:pre-wrap;word-break:break-word;}}
        [data-testid="column"]{{width:100% !important;margin-bottom:1rem;}}
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def extract_retailer(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    return domain.split(".")[0]


def searx_fetch(phone: str) -> list[dict]:
    global LAST_CALL
    query = f'"{phone}" price Kenya'
    for attempt in range(1, 4):
        wait = RATE_LIMIT - (time.time() - LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        LAST_CALL = time.time()

        for base in SEARX_INSTANCES:
            try:
                r = requests.get(
                    base,
                    params={"q": query, "format": "json", "language": "en", "safesearch": "0"},
                    headers=HEADERS,
                    timeout=20,
                )
                if r.status_code == 200 and "results" in r.json():
                    raw = r.json()["results"]
                    # Kenya filter
                    filtered = []
                    for res in raw:
                        url = res.get("url", "")
                        if url and ".ke" in url.lower():
                            title = res.get("title", "")
                            content = res.get("content", "")
                            full_text = f"{title} {content} {url}".lower()
                            price_match = re.search(
                                r"(?:ksh?|kes|shillings?)\s*[:-]?\s*(\d{3,}(?:,\d{3})*)",
                                full_text,
                                re.I,
                            )
                            price = f"KSh {price_match.group(1)}" if price_match else None
                            stock = "✅ In stock"
                            txt = title + " " + content
                            if any(w in txt.lower() for w in ["out of stock", "sold out", "unavailable"]):
                                stock = "❌ Out of stock"
                            elif any(w in txt.lower() for w in ["limited stock", "few left", "hurry"]):
                                stock = "⚠️ Limited stock"
                            filtered.append(
                                {
                                    "title": title[:180],
                                    "url": url,
                                    "content": content[:300],
                                    "price_ksh": price,
                                    "stock": stock,
                                }
                            )
                    return filtered[:60]
            except:
                continue
        st.warning(f"⚠️ Server is starting... (attempt {attempt}/3). Retrying in 5s.")
        time.sleep(5)
    st.error("❌ All SearXNG instances failed or no .ke results.")
    return []


def build_context(results: list) -> str:
    lines = []
    for r in results:
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        lines.append(f"Title: {r['title']}{price}\nURL: {r['url']}\nSnippet: {r['content']}\nStock: {r['stock']}\n---")
    return "\n".join(lines) if lines else "No results found."


def parse_llm(raw: str) -> tuple:
    parts = raw.split("---PRICE---")
    if len(parts) < 2:
        return ("", "", "", raw)
    _, rest = parts[0], parts[1]
    spec_parts = rest.split("---SPECS---", 1)
    if len(spec_parts) < 2:
        return ("", "", "", rest.strip())
    price_block, rest2 = spec_parts[0].strip(), spec_parts[1].strip()
    insight_parts = rest2.split("---INSIGHTS---", 1)
    if len(insight_parts) < 2:
        return (price_block, rest2, "", "")
    specs_block, rest3 = insight_parts[0].strip(), insight_parts[1].strip()
    copy_parts = rest3.split("---COPY---", 1)
    insights_block = copy_parts[0].strip()
    copy_block = copy_parts[1].strip() if len(copy_parts) > 1 else ""
    return (price_block, specs_block, insights_block, copy_block)


# ---------- TWO PROMPTS ----------
def prompt_with_data(phone: str, ctx: str, persona: str, tone: str) -> tuple:
    xmas = "🎄 Christmas Special! Gift-ready with warranty & fast delivery." if IS_CHRISTMAS else ""
    prompt = f"""You are Tripple K Communications marketing AI.

VALUE PROPS (mention 1-2):
- Accredited distributor
- Full manufacturer warranty
- Pay on delivery
- Fast Nairobi delivery
{xmas}

INPUT:
PHONE: {phone}
PERSONA: {persona}
TONE: {tone}
DATA:
{ctx}

RETURN:
---PRICE---
---SPECS---
---INSIGHTS---
---COPY---

1. PRICE: "Retailer - KSh X,XXX - URL" from data only.
2. SPECS: real specs from snippets.
3. INSIGHTS: short lines, no competitor names.
4. COPY:
   - BANNERS: ≤40 chars
   - TIKTOK: <100 chars, fun, emojis if Playful
   - IG/FB: benefit-driven
   - WHATSAPP: include phone {TRIPPLEK_PHONE}, warranty, pay on delivery
   - HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only.
"""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            timeout=50,
            max_tokens=2400,
        )
        return parse_llm(comp.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"🤖 Groq error: {e}")
        return "", "", "", ""


def prompt_without_data(phone: str, persona: str, tone: str) -> tuple:
    xmas = "🎄 Perfect Christmas gift!" if IS_CHRISTMAS else ""
    prompt = f"""You are Tripple K Communications.

VALUE PROPS:
- Accredited distributor
- Full manufacturer warranty
- Pay on delivery
- Fast Nairobi delivery
{xmas}

PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

TASK: Create marketing copy **without inventing prices or specs**.

RETURN ONLY:
---COPY---
- BANNERS: ≤40 chars
- TIKTOK: <100 chars, fun, emojis if Playful
- IG/FB: short posts
- WHATSAPP: include phone {TRIPPLEK_PHONE}, warranty, pay on delivery
- HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only.
"""
    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            timeout=30,
            max_tokens=800,
        )
        return parse_llm(comp.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"🤖 Groq fallback error: {e}")
        return "", "", "", ""


# ---------- UI ----------
inject_css()
st.title("📱 Tripple K Phone Ad Generator")
st.caption("Flyer-ready kits for Tripple K Communications | www.tripplek.co.ke")

phone = st.text_input("🔍 Phone model (e.g., Xiaomi Poco X6 Pro)", value="Xiaomi Poco X6 Pro")
persona = st.selectbox("👤 Buyer Persona", ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators", "Status execs"], index=0)
tone = st.selectbox("🎨 Brand Tone", ["Playful", "Rational", "Luxury", "FOMO"], index=0)

if st.button("🚀 Generate Tripple K Marketing Kit", type="primary"):
    fetch_date = datetime.now().strftime("%d %b %Y at %H:%M EAT")

    with st.status("🔍 Fetching live Kenyan market data...", expanded=True) as status:
        results = searx_fetch(phone)
        searx_ok = len(results) > 0

        # Raw preview before AI
        if searx_ok:
            with st.expander("👀 Preview raw Kenyan results (before AI)"):
                df_raw = pd.DataFrame(results)
                st.dataframe(df_raw, use_container_width=True)
                st.metric("Kenyan results", len(results))

        # Two-prompt logic
        if searx_ok:
            ctx = build_context(results)
            price_block, specs_block, insights_block, copy_block = prompt_with_data(phone, ctx, persona, tone)
        else:
            price_block = specs_block = insights_block = ""
            price_block, specs_block, insights_block, copy_block = prompt_without_data(phone, persona, tone)

        status.update(label="✅ Kit ready!", state="complete", expanded=False)

    # ---------- OUTPUT ----------
    st.markdown(f"## {phone}")
    if IS_CHRISTMAS:
        st.info(XMAS_HOOK)

    # Price table only if data
    if searx_ok and price_block.strip():
        st.subheader("🛒 Verified Kenyan Prices")
        rows = []
        for line in price_block.splitlines():
            if not line.strip():
                continue
            parts = line.split(" - ")
            if len(parts) >= 3:
                price_str = parts[1]
                url = " - ".join(parts[2:])
                rows.append(
                    {
                        "Price (KSh)": price_str,
                        "Retailer": extract_retailer(url),
                        "Stock": results[len(rows)].get("stock", "✅ In stock"),
                        "Link": url,
                    }
                )
        rows.sort(key=lambda r: int(re.sub(r"[^\d]", "", r["Price (KSh)"]) or 0), reverse=True)
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Specs & insights only if data
    if searx_ok and specs_block.strip():
        st.subheader("📱 Key Specs")
        st.text(specs_block)

    if searx_ok and insights_block.strip():
        with st.expander("📈 Market Insights"):
            for line in insights_block.splitlines():
                if line.strip():
                    st.markdown(f"- {line.strip()}")

    # Copy section (always show if generated)
    if copy_block.strip():
        st.subheader("📣 Ready-to-Use Copy")
        lines = [l.strip() for l in copy_block.splitlines() if l.strip()]
        banners, social, hashtags = [], {"TikTok": "", "IG": "", "FB": "", "WhatsApp": ""}, ""
        mode = None
        for line in lines:
            if line.startswith("BANNERS:"):
                mode = "banner"
            elif line.startswith("TikTok:"):
                social["TikTok"] = line.replace("TikTok:", "").strip()
                mode = "tiktok"
            elif line.startswith("IG:"):
                social["IG"] = line.replace("IG:", "").strip()
                mode = "ig"
            elif line.startswith("FB:"):
                social["FB"] = line.replace("FB:", "").strip()
                mode = "fb"
            elif line.startswith("WHATSAPP:"):
                social["WhatsApp"] = line.replace("WHATSAPP:", "").strip()
                mode = "whatsapp"
            elif line.startswith("#"):
                hashtags = line
                break
            elif mode == "banner" and len(banners) < 2:
                banners.append(line)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🖼️ Banner Text**")
            for b in banners:
                st.code(b, language="text")
        with c2:
            st.markdown("**📲 Social Posts**")
            st.text_area("TikTok", social["TikTok"], height=60)
            st.text_area("Instagram", social["IG"], height=70)
            st.text_area("Facebook", social["FB"], height=70)
            st.text_area("WhatsApp", social["WhatsApp"], height=100)
            st.text_input("Hashtags", hashtags.strip())

    st.divider()
    st.caption(f"Generated for **Tripple K Communications** | [www.tripplek.co.ke](https://www.tripplek.co.ke) | {fetch_date} EAT")
