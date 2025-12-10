#!/usr/bin/env python3
"""
Full SearX → Kenya filter → Groq → display
pip install streamlit requests groq pandas
"""

import os, json, re, urllib.parse, streamlit as st, pandas as pd
from datetime import datetime
from typing import List

import requests
from groq import Groq

# ---------- CONFIG ----------
GROQ_KEY = st.secrets.get("groq_key") or os.getenv("GROQ_KEY")
if not GROQ_KEY:
    st.error("🛑  Add groq_key to .streamlit/secrets.toml")
    st.stop()

CLIENT = Groq(api_key=GROQ_KEY, timeout=30)
SEARX_URL = "https://searxng-587s.onrender.com/search"
MODEL = "llama-3.1-8b-instant"


# ---------- FULL SERP ----------
def full_serp_kenya(query: str) -> List[dict]:
    """One call, no paging, keep only URLs with 'ke'."""
    r = requests.get(
        SEARX_URL,
        params={
            "q": f"{query} price kenya .co.ke",
            "category_general": "1",
            "language": "auto",
            "safesearch": "0",
            "format": "json",
        },
        timeout=30,
    )
    r.raise_for_status()
    hits = r.json().get("results", [])
    # filter + trim
    return [
        {"pos": idx + 1, "title": h.get("title", ""), "url": h.get("url", ""), "content": h.get("content", "")[:200]}
        for idx, h in enumerate(hits)
        if "ke" in h.get("url", "").lower()
    ]


# ---------- GROQ ----------
def ai_pack(phone: str, rows: List[dict]) -> dict:
    """Tiny prompt → prices, specs, FB, TT, flyer."""
    serp = "\n".join(f"{r['pos']} | {r['title']} | {r['url']} | {r['content']}" for r in rows)

    prompt = f"""You are a Kenyan phone-marketing assistant for tripplek.co.ke.
Phone: {phone}
Kenyan SERP (use ONLY this data):
{serp}

Return exact block:
CLEAN_NAME: <model>
PRICES:
KSh XX,XXX - site - <url from SERP>
SPECS:
- spec: value (from SERP)
AD_COPY:
FB: 3-4 Kenyan sentences, price, 3-5 hashtags
TT: 1-2 lines, 5-8 hashtags
FLYER:
- Variant 1 (2 lines)
- Variant 2 (2 lines)"""
    try:
        raw = CLIENT.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=900,
        ).choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Groq error: {e}")
        return {}

    def grab(section: str) -> list[str]:
        m = re.search(rf"^{section}:\s*(.*?)(?=^[A-Z_]+:|$)", raw, re.MULTILINE | re.DOTALL)
        return [ln[2:].strip() for ln in m.group(1).splitlines() if ln.startswith("- ")] if m else []

    prices = [ln for ln in raw.splitlines() if ln.startswith("KSh ") and " - " in ln]
    return {
        "clean_name": raw.splitlines()[0].replace("CLEAN_NAME:", "").strip() or phone,
        "prices": prices,
        "specs": grab("SPECS"),
        "fb": raw.split("FB:")[1].split("TT:")[0].strip() if "FB:" in raw else "",
        "tt": raw.split("TT:")[1].split("FLYER:")[0].strip() if "TT:" in raw else "",
        "flyer": grab("FLYER"),
    }


# ---------- UI ----------
st.set_page_config(page_title="TrippleK Ad Builder", layout="wide")
st.title("📱 TrippleK Ad Builder")

with st.form("in"):
    query = st.text_input("Phone / keywords", value="samsung a17")
    submit = st.form_submit_button("Build")

if submit:
    with st.spinner("Scraping + crafting …"):
        rows = full_serp_kenya(query)
        if not rows:
            st.info("No Kenyan results – try different keywords.")
            st.stop()
        out = ai_pack(query, rows)

    st.header(out["clean_name"])

    # ---- PRICES TABLE ----
    if out["prices"]:
        st.subheader("💰 Prices")
        df = pd.DataFrame([p.split(" - ", 2) for p in out["prices"]], columns=["Price", "Site", "URL"])
        st.dataframe(df, width='stretch', hide_index=True)

    # ---- SPECS ----
    if out["specs"]:
        st.subheader("🔍 Specs")
        for s in out["specs"]:
            st.markdown(f"- {s}")

    # ---- AD COPY ----
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📘 Facebook")
        st.code(out["fb"], language=None)
    with col2:
        st.subheader("🎵 TikTok")
        st.code(out["tt"], language=None)

    # ---- FLYER ----
    if out["flyer"]:
        st.subheader("📄 Flyer text")
        for v in out["flyer"][:2]:
            st.code(v, language=None)
