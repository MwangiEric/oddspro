#!/usr/bin/env python3
import streamlit as st
import requests
import time
import urllib.parse
import re
from groq import Groq
from bs4 import BeautifulSoup

############################ CONFIG ################################
GROQ_KEY = st.secrets.get("groq_key", "")
if not GROQ_KEY:
    st.error("❌ Add `groq_key` to `.streamlit/secrets.toml`")
    st.stop()

client = Groq(api_key=GROQ_KEY)
SEARX_URL = "https://searxng-587s.onrender.com/search"
MODEL = "llama-3.1-8b-instant"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
LAST_CALL = 0
RATE_LIMIT = 3
####################################################################


def fetch_gsmarena_specs(model: str) -> list[str]:
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        search_url = f"https://www.gsmarena.com/res.php3?sSearchWord={urllib.parse.quote(model)}"
        soup = BeautifulSoup(session.get(search_url, timeout=10).text, "html.parser")
        first_link = soup.select_one("div.makers ul li a")
        if not first_link:
            return []
        device_url = urllib.parse.urljoin("https://www.gsmarena.com/", first_link["href"])
        soup2 = BeautifulSoup(session.get(device_url, timeout=10).text, "html.parser")
        specs = []
        for tr in soup2.select("table.specs tr"):
            tds = tr.find_all("td")
            if len(tds) == 2:
                key = tds[0].get_text(strip=True).rstrip(":")
                val = tds[1].get_text(strip=True)
                if key and val and "no specification" not in val.lower():
                    specs.append(f"{key}: {val}")
        return specs[:8]
    except Exception:
        return []


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

            # Flexible KSh price extraction (avoid GB/MB confusion)
            price_match = re.search(
                r'(?:ksh?|kes|shillings?)\s*[:\-]?\s*(\d{3,}(?:,\d{3})*)(?!\s*(?:gb|mb|gbp|usd|eur))',
                full_text,
                re.IGNORECASE
            )
            price = f"KSh {price_match.group(1)}" if price_match else None

            # Soft Kenya signal
            is_kenya = bool(price) or any(kw in full_text for kw in [
                "kenya", "nairobi", "mombasa", "kisumu", "safaricom", "jumia", "kilimall",
                "sky.garden", "copiashop", "cellulant", ".ke"
            ])

            enriched.append({
                "position": i,
                "title": title[:150],
                "url": url,
                "content": content[:250],
                "price_ksh": price,
                "likely_kenya": is_kenya,
            })
        return enriched[:15]
    except Exception as e:
        st.warning(f"⚠️ SearX error: {str(e)[:60]}")
        return []


def build_groq_context(results: list[dict]) -> str:
    lines = []
    for r in results:
        marker = "[🇰🇪]" if r["likely_kenya"] else "[🌍]"
        price = f" | {r['price_ksh']}" if r["price_ksh"] else ""
        lines.append(f"{marker} {r['title']}{price}\n   URL: {r['url']}\n   Snippet: {r['content']}\n")
    return "\n".join(lines) if lines else "No web results found."


def parse_groq_response(text: str):
    parts = text.split("---PRICE---")
    if len(parts) < 2:
        return "", "", text
    pre, rest = parts[0], parts[1]
    spec_parts = rest.split("---SPECS---", 1)
    if len(spec_parts) < 2:
        return pre.strip(), rest.strip(), ""
    price_block = pre.strip()
    specs_block, marketing_part = spec_parts[0].strip(), spec_parts[1].strip()
    marketing_parts = marketing_part.split("---MARKETING---", 1)
    marketing_block = marketing_parts[-1].strip()
    return price_block, specs_block, marketing_block


def generate_marketing(phone: str, spec_text: str, web_context: str, persona: str, tone: str) -> tuple[str, str, str]:
    prompt = f"""You are a mobile marketing expert for Kenya.

PHONE: {phone}
PERSONA: {persona}
TONE: {tone}

OFFICIAL SPECS:
{spec_text}

WEB RESULTS (prioritize 🇰🇪 entries with KSh prices):
{web_context}

INSTRUCTIONS:
Return exactly THREE sections in order, separated by:
---PRICE---
---SPECS---
---MARKETING---

1. PRICE TABLE:
   - One line per verified offer: "SiteName - KSh X,XXX - https://..."
   - Only include entries with visible KSh prices.
   - Max 6 lines.

2. PHONE SPECS:
   - Up to 6 key specs (battery, camera, RAM, storage, display, OS).
   - Use official specs if available.

3. MARKETING:
   - BANNERS: 2 lines (≤45 chars each)
   - SOCIAL: 3 lines → Tweet (≤280), IG (≤150, emoji OK), FB (≤300)
   - HASHTAGS: 10 space-separated (include #Kenya #PhoneDealsKE)

RULES:
- Never invent prices or URLs.
- Use plain text only. No markdown, no extra headings.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            timeout=40,
            max_tokens=1800,
        )
        raw = completion.choices[0].message.content.strip()
        return parse_groq_response(raw)
    except Exception as e:
        st.error(f"🤖 Groq error: {e}")
        return "", "", ""


############################ STREAMLIT UI ####################################
st.set_page_config(page_title="📱 Kenya Phone Ads", layout="wide")
st.title("📱 Kenya Phone Ad Generator")
st.caption("Get real prices, specs & ready-to-post ads — all Kenya-focused")

phone = st.text_input("🔍 Phone model (e.g., Tecno Spark 20 Pro)", value="Samsung Galaxy A17")
persona = st.selectbox("👤 Buyer Persona", ["Budget students", "Tech-savvy pros", "Camera creators", "Status execs"], index=0)
tone = st.selectbox("🎨 Brand Tone", ["Rational", "Playful", "Luxury", "FOMO"], index=0)

if st.button("🚀 Generate Ads", type="primary"):
    with st.status("🔍 Fetching data...", expanded=True) as status:
        st.write("📱 Getting official specs...")
        specs = fetch_gsmarena_specs(phone)
        spec_text = "\n".join(specs) if specs else "Not available."

        st.write("🌐 Searching global & Kenyan offers...")
        web_results = searx_all_results(phone)
        web_context = build_groq_context(web_results)

        st.write("🧠 Generating marketing assets...")
        price_table, specs_out, marketing = generate_marketing(phone, spec_text, web_context, persona, tone)
        status.update(label="✅ Done!", state="complete", expanded=False)

    # Display
    st.subheader("🛒 Verified Kenyan Prices (KSh)")
    if price_table.strip():
        st.text(price_table)
    else:
        st.caption("No KSh prices detected in search results.")

    st.subheader("📱 Key Specs")
    st.text(specs_out if specs_out.strip() else spec_text)

    st.subheader("📣 Marketing Bundle")
    st.text(marketing if marketing.strip() else "No marketing copy generated.")