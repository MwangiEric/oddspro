#!/usr/bin/env python3
import streamlit as st, requests, pandas as pd, re, datetime as dt, json, time
from typing import List

############################  CONFIG  ################################
SEARX_URL = "https://searxng-587s.onrender.com"
DEFAULT_QUERY = "samsung a17 price kenya"
PAGES = 3
RATE_LIMIT_SEC = 3

# Regex helpers
PRICE_RE = re.compile(r"(KES|KSh|Shs?)\s*([\d,]+\.?\d*)", re.I)
WARRANTY_RE = re.compile(r"\b(WRTY?|warranty|12\s*months|24\s*months|36\s*months)\b", re.I)
COLOR_RE = re.compile(r"\b(Black|White|Blue|Red|Green|Gold|Purple|Pink|Grey|Silver|Yellow|Orange|Brown)\b", re.I)
OOS_RE = re.compile(r"\b(out of stock|sold out|unavailable|not available|0\s*left)\b", re.I)

# Top Kenyan shops
SHOPS = {
    "Any (no filter)": "",
    "Jumia Kenya": "site:jumia.co.ke",
    "Kilimall": "site:kilimall.co.ke",
    "PhonePlace Kenya": "site:phoneplacekenya.co.ke",
    "Masoko": "site:masoko.co.ke",
    "Safaricom Shop": "site:safaricom.co.ke",
}
#####################################################################


@st.cache_data(show_spinner=False)
def pull_raw_results(query: str, time_range: str) -> List[dict]:
    """Return raw SearXNG JSON results (all pages)."""
    raw_all = []
    for p in range(1, PAGES + 1):
        # URL exactly as you showed
        url = (
            f"{SEARX_URL}/search?q={requests.utils.quote(query)}"
            f"&category_general=1&pageno={p}&language=auto&time_range={time_range}"
            f"&safesearch=0&format=json"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        raw_all.extend(resp.json().get("results", []))
    return raw_all


def analyse(raw: List[dict]) -> pd.DataFrame:
    """Extract price, warranty, colour, brand, OOS."""
    rows = []
    for item in raw:
        title = item.get("title", "")
        snippet = item.get("content", "")
        text = title + " " + snippet

                # Price
        price_raw = PRICE_RE.search(text)
        if price_raw:
            digits_only = re.sub(r"[^\d]", "", price_raw.group(2))
            price = int(digits_only) if digits_only else None
        else:
            price = None

price_raw.group(2))) if price_raw and price_raw.group(2).strip() else None

        # Warranty
        warranty = "Yes" if WARRANTY_RE.search(text) else "No"

        # Colour
        colour_match = COLOR_RE.search(text)
        colour = colour_match.group(0) if colour_match else "Not specified"

        # Brand
        brand = (
            re.search(r"\b(Samsung|Apple|iPhone|Xiaomi|Redmi|Oppo|Vivo|TECNO|Infinix|Huawei|Nokia)\b", text, re.I)
        )
        brand = brand.group(0).upper() if brand else "Other"

        # OOS
        oos = bool(OOS_RE.search(text))

        rows.append(
            {
                "title": title,
                "url": item["url"],
                "snippet": snippet[:250],
                "price_KES": price,
                "warranty": warranty,
                "colour": colour,
                "brand": brand,
                "oos": oos,
                "published": item.get("publishedDate") or dt.datetime.utcnow().strftime("%Y-%m-%d"),
            }
        )
    return pd.DataFrame(rows)


############################  UI  ####################################
st.set_page_config(page_title="KE Phone Deals", layout="wide")
st.title("📱 Kenya Phone Price Tracker – Raw → Full Table")
st.info(f"SearXNG instance: {SEARX_URL}")

# Sidebar
with st.sidebar:
    st.subheader("Search")
    query = st.text_input("Query", value=DEFAULT_QUERY)
    shop = st.selectbox("Shop filter", list(SHOPS.keys()))
    time_range = st.selectbox("Recency", ["day", "week", "month"], index=1)
    if st.button("🔄 Scan now"):
        st.cache_data.clear()

# Rate-limit guard
if "last_call" not in st.session_state:
    st.session_state.last_call = 0
elapsed = time.time() - st.session_state.last_call
if elapsed < RATE_LIMIT_SEC:
    st.warning(f"Rate-limit active – wait {RATE_LIMIT_SEC - elapsed:.0f} s")
    st.stop()

# Build final query
site_filter = SHOPS[shop]
final_query = f"{query} {site_filter}".strip()

# 1️⃣ PULL RAW -------------------------------------------------------
with st.spinner("Pulling raw SearXNG ..."):
    raw_results = pull_raw_results(final_query, time_range)
    st.session_state.last_call = time.time()

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
    st.subheader(f"Full analysed table ({len(df)} rows)")

    # Filters
    with st.expander("🔍 Filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        min_price, max_price = c1.slider("Price (KES)", 5_000, 200_000, (5_000, 200_000))
        brand_choice = c2.multiselect("Brands", sorted(df.brand.unique()), default=df.brand.unique())
        colour_choice = c3.multiselect("Colour", sorted(df.colour.unique()), default=df.colour.unique())
        warranty_choice = c4.multiselect("Warranty", sorted(df.warranty.unique()), default=df.warranty.unique())
        oos_radio = st.radio("Stock", ["All", "In stock only", "Out of stock only"], index=0)

    # Apply filters
    df_filt = df.dropna(subset=["price_KES"])
    df_filt = df_filt[(df_filt.price_KES >= min_price) & (df_filt.price_KES <= max_price)]
    df_filt = df_filt[df_filt.brand.isin(brand_choice)]
    df_filt = df_filt[df_filt.colour.isin(colour_choice)]
    df_filt = df_filt[df_filt.warranty.isin(warranty_choice)]
    if oos_radio == "In stock only":
        df_filt = df_filt[~df_filt.oos]
    elif oos_radio == "Out of stock only":
        df_filt = df_filt[df_filt.oos]

    # KPI
    c1, c2, c3, c4, c5 = st.columns(5)
    k1, k2, k3, k4, k5 = (
        len(df_filt),
        df_filt.price_KES.min() if len(df_filt) else "-",
        df_filt.price_KES.median() if len(df_filt) else "-",
        df_filt.oos.sum() if len(df_filt) else "-",
        (df_filt.warranty == "Yes").sum() if len(df_filt) else "-",
    )
    c1.metric("Listings", k1)
    c2.metric("Cheapest", f"KES {k2:,.0f}" if k2 != "-" else "-")
    c3.metric("Median", f"KES {k3:,.0f}" if k3 != "-" else "-")
    c4.metric("Out-of-stock", k4)
    c5.metric("With warranty", k5)

    # Full table
    df_display = df_filt.copy()
    df_display["📊"] = df_display.oos.apply(lambda x: "🟥" if x else "")
    st.dataframe(
        df_display[["📊", "title", "price_KES", "brand", "colour", "warranty", "url"]]
        .sort_values("price_KES", na_position="last")
        .reset_index(drop=True),
        use_container_width=True,
        column_config={
            "title": st.column_config.TextColumn("Title", max_chars=120),
            "price_KES": st.column_config.NumberColumn("Price (KES)", format="%d"),
            "brand": st.column_config.TextColumn("Brand"),
            "colour": st.column_config.TextColumn("Colour"),
            "warranty": st.column_config.TextColumn("Warranty"),
            "url": st.column_config.LinkColumn("URL"),
        },
    )

    # RAM-only CSV export
    csv = df_filt.to_csv(index=False)
    st.download_button(
        label="💾 CSV (in-memory)",
        data=csv,
        file_name=f"phones_{dt.datetime.utcnow():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )
else:
    st.warning("No results – try a different query or shop.")
