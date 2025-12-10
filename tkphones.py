#!/usr/bin/env python3
"""
TrippleK Phone-Ad Builder – bare bones, Kenya-only
pip install streamlit requests groq beautifulsoup4
"""

import os, json, re, time, urllib.parse, streamlit as st
from datetime import datetime
from typing import List

import requests
from groq import Groq
from bs4 import BeautifulSoup

# ---------- CONFIG ----------
GROQ_KEY = st.secrets.get("groq_key") or os.getenv("GROQ_KEY")
if not GROQ_KEY:
    st.error("🛑  Add groq_key to .streamlit/secrets.toml")
    st.stop()

CLIENT = Groq(api_key=GROQ_KEY, timeout=30)
SEARX_URL = "https://searxng-587s.onrender.com/search"
MODEL = "llama-3.1-8b-instant"


# ---------- API ----------
def searx_kenya(query: str) -> List[dict]:
    """One call, keep only URLs with 'ke'."""
    r = requests.get(
        SEARX_URL,
        params={
            "q": f"{query} kenya price",
            "category_general": "1",
            "language": "auto",
            "safesearch": "0",
            "format": "json",
        },
        timeout=25,
    )
    r.raise_for_status()
    hits = r.json().get("results", [])
    return [h for h in hits if "ke" in h.get("url", "").lower()][:10]


def ai_pack(phone: str, kenya_hits: List[dict]) -> dict:
    """Tiny prompt → prices + FB + TT + 2 flyer lines."""
    text = "\n".join(f"{h['title']} {h['content'][:100]}" for h in kenya_hits)

    prompt = f"""You are a Kenyan phone-marketing assistant for tripplek.co.ke.
Phone: {phone}
Text: {text[:800]}

Rules:
- Use ONLY URLs from the text above – do not invent.
- Return the **exact** block below, no chat.

CLEAN_NAME: <model>
PRICES:
KSh XX,XXX - site - <real URL>
FB: 3-4 Kenyan sentences, price, spec hint, same-day Nairobi, 3-5 hashtags
TT: 1-2 punchy lines, 5-8 hashtags
FLYER_TEXT:
- Variant 1 (2 lines)
- Variant 2 (2 lines)
"""
    try:
        resp = CLIENT.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Groq error: {e}")
        return {}

    prices = [ln for ln in raw.splitlines() if ln.startswith("KSh ") and " - " in ln]
    fb  = raw.split("FB:")[1].split("TT:")[0].strip() if "FB:" in raw else ""
    tt  = raw.split("TT:")[1].split("FLYER_TEXT:")[0].strip() if "TT:" in raw else ""
    fly = raw.split("FLYER_TEXT:")[1].strip() if "FLYER_TEXT:" in raw else ""
    clean_name = raw.splitlines()[0].replace("CLEAN_NAME:", "").strip() or phone
    return {"clean_name": clean_name, "prices": prices, "fb": fb, "tt": tt, "flyer_text": [f.strip("- ") for f in fly.split("\n") if f.strip()]}


# ---------- UI ----------
st.set_page_config(page_title="TrippleK Ad Builder", layout="wide")
st.title("📱 TrippleK Ad Builder")

with st.form("in"):
    phone  = st.text_input("Phone / keywords", value="samsung a17")
    submit = st.form_submit_button("Generate")

if submit:
    with st.spinner("Building..."):
        hits = searx_kenya(phone)
        pack = ai_pack(phone, hits)

    if not pack["prices"]:
        st.info("No Kenyan prices found – try different keywords.")
        st.stop()

    st.subheader(pack["clean_name"])
    st.markdown("**Prices**")
    for p in pack["prices"]:
        st.markdown(f"- {p}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Facebook**")
        st.code(pack["fb"], language=None)
    with col2:
        st.markdown("**TikTok**")
        st.code(pack["tt"], language=None)

    if pack["flyer_text"]:
        st.markdown("**Flyer text**")
        for v in pack["flyer_text"][:2]:
            st.code(v, language=None)
