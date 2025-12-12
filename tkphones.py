#!/usr/bin/env python3
import streamlit as st
import requests
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("Add groq_key to .streamlit/secrets.toml")
    st.stop()

from groq import Groq

client = Groq(api_key=GROQ_KEY)

SEARX_INSTANCE = "https://searxng-587s.onrender.com/search"  # Primary instance
BACKUP_INSTANCES = [  # Backup instances
    "https://searx.be/search",
    "https://search.ononoki.org/search",
    "https://searxng.site/search",
]

MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RATE_LIMIT = 3
LAST_CALL = 0

BRAND_GREEN = "#4CAF50"
BRAND_MAROON = "#8B0000"
BACKGROUND_LIGHT = "#F9FAF8"
TRIPPLEK_PHONE = "+254700123456"

now = datetime.now()
is_christmas = (now.month == 12 and now.day >= 1) or (now.month == 1 and now.day <= 10)
CHRISTMAS_HOOK = "Perfect Christmas gift with warranty & fast delivery!" if is_christmas else ""
####################################################################


def inject_brand_css():
    st.markdown(f"""
    <style>
    .stButton>button {{
        background-color: {BRAND_MAROON};
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.5rem 1rem;
    }}
    .stButton>button:hover {{
        background-color: #5a0000;
    }}
    h1, h2, h3 {{
        color: {BRAND_MAROON} !important;
    }}
    .dataframe thead th {{
        background-color: {BRAND_GREEN};
        color: white !important;
    }}
    .main {{
        background-color: {BACKGROUND_LIGHT};
    }}
    .recommended-price {{
        background-color: #E8F5E9 !important;
        font-weight: bold;
    }}
    @media (max-width: 768px) {{
        .stTextArea textarea, .stCodeBlock {{
            font-size: 14px !important;
            white-space: pre-wrap;
            word-break: break-word;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def warm_up_searx(url):
    """Ping SearXNG instance on startup"""
    try:
        r = requests.get(url, params={"q": "test", "format": "json"}, timeout=8)
        return url if r.status_code == 200 else None
    except:
        return None


def extract_retailer(url: str) -> str:
    if not url:
        return "unknown"
    domain = urlparse(url).netloc.lower()
    domain = re.sub(r"^(www|m|mobile|shop)\.", "", domain)
    return domain.split(".")[0]


def extract_slug_from_url(url: str) -> str:
    clean = url.split("?", 1)[0].split("#", 1)[0]
    parts = [p for p in clean.split("/") if p]
    return parts[-1].lower() if parts else ""


def predict_image_url(phone: str, url: str) -> str:
    """Use Groq to predict likely product image URL"""
    slug = extract_slug_from_url(url)
    prompt = f"""Product: {phone}
URL: {url}
Slug: {slug}

Most Kenyan e-commerce sites use WooCommerce. Predict the direct image URL.
Common patterns:
/wp-content/uploads/2024/12/{slug}.jpg
/wp-content/uploads/2024/12/{slug}-1024x1024.jpg

Return only the full image URL or "unknown"."""

    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100,
            timeout=8
        )
        pred = comp.choices[0].message.content.strip()
        return pred if pred != "unknown" and pred.startswith("http") else ""
    except:
        return ""


def validate_image(url: str) -> bool:
    try:
        r = requests.head(url, timeout=3, headers=HEADERS)
        return r.status_code == 200 and "image" in r.headers.get("content-type", "").lower()
    except:
        return False


def fetch_kenyan_prices(phone: str) -> list[dict]:
    global LAST_CALL

    # Try primary instance first
    st.write(f"🌐 Trying primary SearXNG instance: {SEARX_INSTANCE}")
    wait = RATE_LIMIT - (time.time() - LAST_CALL)
    if wait > 0:
        time.sleep(wait)
    LAST_CALL = time.time()

    try:
        r = requests.get(
            SEARX_INSTANCE,
            params={
                "q": f'"{phone}" price Kenya',
                "format": "json",
                "language": "en",
                "safesearch": "0"
            },
            headers=HEADERS,
            timeout=25
        )

        if r.status_code == 200:
            results = r.json().get("results", [])[:60]

            enriched = []
            for res in results:
                title = res.get("title", "")
                content = res.get("content", "")
                url = res.get("url", "")
                # Filter for Kenyan URLs
                if url and ".ke" in url.lower():
                    full_text = f"{title} {content} {url}".lower()

                    price_match = re.search(
                        r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)',
                        full_text,
                        re.IGNORECASE
                    )
                    price = f"KSh {price_match.group(1)}" if price_match else None

                    stock = "In stock"
                    if any(w in full_text for w in ["out of stock", "sold out", "unavailable"]):
                        stock = "Out of stock"
                    elif any(w in full_text for w in ["limited stock", "few left", "hurry"]):
                        stock = "Limited stock"

                    enriched.append({
                        "title": title[:180],
                        "url": url,
                        "content": content[:300],
                        "price_ksh": price,
                        "stock": stock
                    })

            if enriched:
                st.success(f"✅ Successfully fetched results from {SEARX_INSTANCE}")
                return enriched
            else:
                st.warning(f"⚠️ No Kenyan results found from {SEARX_INSTANCE}")
        else:
            st.warning(f"⚠️ SearX request failed with status code: {r.status_code}")

    except Exception as e:
        st.warning(f"⚠️ Error with primary SearX instance: {str(e)[:60]}")

    # Try backup instances if primary fails
    st.sidebar.warning(f"Trying backup search engine...")
    for instance in BACKUP_INSTANCES:
        st.write(f"🌐 Trying backup SearXNG instance: {instance}")
        wait = RATE_LIMIT - (time.time() - LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        LAST_CALL = time.time()

        try:
            r = requests.get(
                instance,
                params={
                    "q": f'"{phone}" price Kenya',
                    "format": "json",
                    "language": "en",
                    "safesearch": "0"
                },
                headers=HEADERS,
                timeout=25
            )

            if r.status_code == 200:
                results = r.json().get("results", [])[:60]

                enriched = []
                for res in results:
                    title = res.get("title", "")
                    content = res.get("content", "")
                    url = res.get("url", "")
                    # Filter for Kenyan URLs
                    if url and ".ke" in url.lower():
                        full_text = f"{title} {content} {url}".lower()

                        price_match = re.search(
                            r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)',
                            full_text,
                            re.IGNORECASE
                        )
                        price = f"KSh {price_match.group(1)}" if price_match else None

                        stock = "In stock"
                        if any(w in full_text for w in ["out of stock", "sold out", "unavailable"]):
                            stock = "Out of stock"
                        elif any(w in full_text for w in ["limited stock", "few left", "hurry"]):
                            stock = "Limited stock"

                        enriched.append({
                            "title": title[:180],
                            "url": url,
                            "content": content[:300],
                            "price_ksh": price,
                            "stock": stock
                        })

                if enriched:
                    st.success(f"✅ Successfully fetched results from {instance}")
                    return enriched
                else:
                    st.warning(f"⚠️ No Kenyan results found from {instance}")
            else:
                st.warning(f"⚠️ SearX request failed with status code: {r.status_code}")

        except Exception as e:
            st.sidebar.warning(f"Trying backup search engine...")
            continue

    return []


def generate_with_data(phone: str, results: list[dict], persona: str, tone: str) -> dict:
    context_lines = []
    for r in results:
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        context_lines.append(
            f"Title: {r['title']}{price}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {r['content']}\n"
            f"Stock: {r['stock']}\n---"
        )
    web_context = "\n".join(context_lines) if context_lines else "No data"

    prompt = f"""You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

TRIPPLE K VALUE PROPS (mention in copy):
* Accredited distributor
* Official warranty
* Pay on delivery
* Nairobi delivery

{f"SEASONAL: {CHRISTMAS_HOOK}" if CHRISTMAS_HOOK else ""}

PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

MARKET DATA:
{web_context}

OUTPUT 4 SECTIONS:

---PRICE---
List: "Retailer - KSh X,XXX - URL" for each result with price

---SPECS---
5-10 key specs from data

---INSIGHTS---
3-5 bullet points on market trends, what makes this phone compelling

---COPY---
BANNERS: 2 lines, max 40 chars, include "Tripple K"
TIKTOK: 1 fun line <100 chars, use emoji for Playful tone
IG: 2-3 sentences highlighting benefits
FB: Similar to IG
WHATSAPP: Include {TRIPPLEK_PHONE}, mention warranty, pay on delivery, {CHRISTMAS_HOOK if CHRISTMAS_HOOK else ""}
HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only. Use real data."""

    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=2400,
            timeout=50
        )

        raw = comp.choices[0].message.content.strip()

        parts = raw.split("---PRICE---")
        if len(parts) < 2:
            return {"error": "Invalid format"}

        rest = parts[1]
        price_block = rest.split("---SPECS---")[0].strip() if "---SPECS---" in rest else ""

        rest = rest.split("---SPECS---", 1)[1] if "---SPECS---" in rest else ""
        specs_block = rest.split("---INSIGHTS---")[0].strip() if "---INSIGHTS---" in rest else ""

        rest = rest.split("---INSIGHTS---", 1)[1] if "---INSIGHTS---" in rest else ""
        insights_block = rest.split("---COPY---")[0].strip() if "---COPY---" in rest else ""

        copy_block = rest.split("---COPY---", 1)[1].strip() if "---COPY---" in rest else ""

        return {
            "prices": price_block,
            "specs": specs_block,
            "insights": insights_block,
            "copy": copy_block
        }

    except Exception as e:
        return {"error": str(e)}


def generate_without_data(phone: str, persona: str, tone: str) -> dict:
    prompt = f"""You are the marketing AI for Tripple K Communications (www.tripplek.co.ke).

Create marketing copy for:
PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

TRIPPLE K VALUE PROPS:
* Accredited distributor
* Official warranty
* Pay on delivery
* Nairobi delivery

{f"SEASONAL: {CHRISTMAS_HOOK}" if CHRISTMAS_HOOK else ""}

DO NOT invent prices or fake specs. Focus on benefits and trust.

OUTPUT:
---SPECS---
General expected specs for this phone model (if known)

---COPY---
BANNERS: 2 lines, max 40 chars
TIKTOK: 1 line <100 chars
IG: 2-3 sentences
FB: Similar to IG
WHATSAPP: Include {TRIPPLEK_PHONE}, warranty, delivery, {CHRISTMAS_HOOK if CHRISTMAS_HOOK else ""}
HASHTAGS: #TrippleK #TrippleKKE #PhoneDealsKE

Plain text only."""

    try:
        comp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )

        raw = comp.choices[0].message.content.strip()

        specs_block = ""
        copy_block = raw

        if "---SPECS---" in raw:
            parts = raw.split("---SPECS---", 1)[1]
            specs_block = parts.split("---COPY---")[0].strip() if "---COPY---" in parts else ""
            copy_block = parts.split("---COPY---", 1)[1].strip() if "---COPY---" in parts else ""

        return {
            "prices": "",
            "specs": specs_block,
            "insights": "",
            "copy": copy_block
        }

    except Exception as e:
        return {"error": str(e)}


############################ STREAMLIT UI ####################################
inject_brand_css()

# Sidebar
with st.sidebar:
    st.title("Settings")
    use_web_data = st.toggle("Use live web data", value=True, help="Search Kenyan retailers for real prices")

    persona = st.selectbox("Target Audience",
                           ["All Kenyan buyers", "Budget students", "Tech-savvy pros", "Camera creators",
                            "Business execs"],
                           index=0)

    tone = st.selectbox("Brand Tone",
                        ["Playful", "Rational", "Luxury", "FOMO"],
                        index=0)

    st.divider()
