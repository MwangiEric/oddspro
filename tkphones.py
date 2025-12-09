#!/usr/bin/env python3
import streamlit as st, requests, pandas as pd, re, datetime as dt, json, time
from typing import List

############################  CONFIG  ################################
SEARX_URL = "https://searxng-587s.onrender.com/search"
RATE_LIMIT = 3  # seconds
LAST_SEARX = 0

# Regex helpers – **keep raw string, no digit-only**
PRICE_RE = re.compile(r"(KES|KSh|Shs?)\s*([\d,]+\.?\d*)", re.I)   # group(0) = full match
WARRANTY_RE = re.compile(r"\b(WRTY?|warranty|12\s*months|24\s*months|36\s*months)\b", re.I)
COLOR_RE = re.compile(r"\b(Black|White|Blue|Red|Green|Gold|Purple|Pink|Grey|Silver|Yellow|Orange|Brown)\b", re.I)
OOS_RE = re.compile(r"\b(out of stock|sold out|unavailable|not available|0\s*left)\b", re.I)

# Shops
SHOPS = {
    "Any (no filter)": "",
    "Jumia Kenya": "site:jumia.co.ke",
    "Kilimall": "site:kilimall.co.ke",
    "PhonePlace Kenya": "site:phoneplacekenya.co.ke",
    "Masoko": "site:masoko.co.ke",
    "Safaricom Shop": "site:safaricom.co.ke",
}
#####################################################################


# ---------- POLITE SEARX ----------
def searx_json(query: str, time_range: str) -> List[dict]:
    global LAST_SEARX
    elapsed = time.time() - LAST_SEARX
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    LAST_SEARX = time.time()
    raw_all = []
    for p in range(1, 4):  # 3 pages
        params = {
            "q": query,
            "category_general": "1",
            "language": "auto",
            "safesearch": "0",
            "format": "json",
            "pageno": p,
            "time_range": time_range,
        }
        r = requests.get(SEARX_URL, params=params, timeout=25)
        r.raise_for_status()
        raw_all.extend(r.json().get("results", []))
    return raw_all


# ---------- ANALYSE (NO RESTRICTIONS) ----------
def analyse(raw: List[dict]) -> pd.DataFrame:
    rows = []
    for item in raw:
        title = item.get("title", "")
        snippet = item.get("content", "")
        text = title + " " + snippet

        # PRICE: raw string (no computation)
        price_match = PRICE_RE.search(text)
        price_str = price_match.group(0) if price_match else None

        # rest stays same
        warranty = "Yes" if WARRANTY_RE.search(text) else "No"
        color_match = COLOR_RE.search(text)
        color = color_match.group(0) if color_match else "Not specified"
        brand = (
            re.search(r"\b(Samsung|Apple|iPhone|Xiaomi|Redmi|Oppo|Vivo|TECNO|Infinix|Huawei|Nokia)\b", text, re.I)
        )
        brand = brand.group(0).upper() if brand else "Other"
        oos = bool(OOS_RE.search(text))

        rows.append(
            {
                "title": title,
                "url": item["url"],
                "snippet": snippet[:250],
                "price_raw": price_str,  # ← raw string
                "warranty": warranty,
                "color": color,
                "brand": brand,
                "oos": oos,
                "published": item.get("publishedDate") or dt.datetime.utcnow().strftime("%Y-%m-%d"),
            }
        )
    return pd.DataFrame(rows)


############################  UI  ####################################
st.set_page_config(page_title="KE Phone Deals (Relaxed)", layout="wide")
st.title("📱 Kenya Phone Price Tracker – Relaxed Raw View")

with st.sidebar:
    st.subheader("Search any phone")
    query = st.text_input("Phone / keywords", value="samsung a17 price kenya")
    shop = st.selectbox("Shop filter", list(SHOPS.keys()))
    time_range = st.selectbox("Recency", ["day", "week", "month"], index=1)
    if st.button("🔄 Scan now"):
        st.cache_data.clear()

final_query = f"{query} {SHOPS[shop]}".strip()

# 1️⃣ PULL RAW -------------------------------------------------------
with st.spinner("Pulling raw SearXNG (polite)..."):
    raw_results = searx_json(final_query, time_range)

st.success(f"Fetched {len(raw_results)} raw results for: `{final_query}`")

with st.expander("👉 Inspect raw JSON (first 3 items)", expanded=False):
    st.json(raw_results[:3])
    st.download_button(
        label="📥 Download full raw JSON",
        data=json.dumps(raw_results, indent=2, ensure_ascii=False),
        file_name=f"raw_phones_{dt.datetime.utcnow():%Y%m%d_%H%M}.json",
        mime="application/json",
    )

# 2️⃣ ANALYSE --------------------------------------------------------
if raw_results:
    df = analyse(raw_results)
    st.subheader(f"Full table ({len(df)} rows) – NO COMPUTATIONS")

    # Filters (optional)
    with st.expander("🔍 Filters", expanded=True):
        c1, c2, c3 = st.columns(3)
        brand_choice = c1.multiselect("Brands", sorted(df.brand.unique()), default=df.brand.unique())
        color_choice = c2.multiselect("Colour", sorted(df.color.unique()), default=df.color.unique())
        oos_radio = c3.radio("Stock", ["All", "In stock only", "Out of stock only"], index=0)

    df_filt = df[df.brand.isin(brand_choice) & df.color.isin(color_choice)]
    if oos_radio == "In stock only":
        df_filt = df_filt[~df_filt.oos]
    elif oos_radio == "Out of stock only":
        df_filt = df_filt[df_filt.oos]

    # Full table
    st.dataframe(
        df_filt[["title", "price_raw", "brand", "color", "warranty", "oos", "url"]]
        .sort_values("price_raw", na_position="last")
        .reset_index(drop=True),
        use_container_width=True,
        column_config={
            "title": st.column_config.TextColumn("Title", max_chars=120),
            "price_raw": st.column_config.TextColumn("Price (raw)"),
            "brand": st.column_config.TextColumn("Brand"),
            "color": st.column_config.TextColumn("Colour"),
            "warranty": st.column_config.TextColumn("Warranty"),
            "oos": st.column_config.CheckboxColumn("Out-of-stock"),
            "url": st.column_config.LinkColumn("URL"),
        },
    )

    # RAM CSV export
    csv = df_filt.to_csv(index=False)
    st.download_button(
        label="💾 CSV (in-memory)",
        data=csv,
        file_name=f"phones_relaxed_{dt.datetime.utcnow():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )
else:
    st.warning("No results – try a different query or shop.")
