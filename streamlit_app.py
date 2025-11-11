import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import os

st.title("Jumia Flash Sales Scraper")

# Target URL and proxy
target_url = "https://www.jumia.co.ke/phones-tablets/flash-sales/"
proxy_url = f"https://cors.ericmwangi13.workers.dev/?url={urllib.parse.quote(target_url, safe=':/?#')}"

# Options
scrape_method = st.radio("Scrape Method", ["Selenium (Dynamic Content)", "Requests (Static via Proxy)"])
debug_mode = st.checkbox("Enable Debug Mode (Show Raw HTML)")
max_scrolls = st.slider("Max Page Scrolls (Selenium Only)", 1, 10, 3)

# Placeholder for progress
progress_bar = st.progress(0)
status_text = st.empty()
csv_placeholder = st.empty()

if st.button("Scrape Flash Sales"):
    products = []
    try:
        status_text.write("Starting scrape...")

        if scrape_method == "Selenium (Dynamic Content)":
            try:
                # Set up Selenium with ChromeDriver
                progress_bar.progress(10)
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                options.add_argument("--disable-gpu")
                options.binary_location = os.environ.get("CHROMIUM_PATH", "")  # For cloud envs

                # Use webdriver-manager to get compatible ChromeDriver
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )

                # Load page
                status_text.write("Loading page with Selenium...")
                driver.get(target_url)
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article.prd._fb.col.c-prd")))
                progress_bar.progress(30)

                # Simulate scrolling
                status_text.write("Scrolling to load more products...")
                for i in range(max_scrolls):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    progress_bar.progress(30 + (i + 1) * (50 // max_scrolls))

                # Parse page
                soup = BeautifulSoup(driver.page_source, "html.parser")
                driver.quit()
                progress_bar.progress(80)

            except Exception as e:
                status_text.error(f"Selenium failed: {e}")
                st.warning("Falling back to Requests (proxy) method...")
                scrape_method = "Requests (Static via Proxy)"

        if scrape_method == "Requests (Static via Proxy)":
            # Use Requests with proxy
            status_text.write("Fetching via proxy...")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(proxy_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            progress_bar.progress(50)

        # Debug: Show raw HTML
        if debug_mode:
            st.write("### Raw HTML Preview (First 2000 chars):")
            st.code(soup.prettify()[:2000], language="html")

        # Find product listings
        listings = soup.find_all("article", class_="prd _fb col c-prd") or \
                   soup.find_all("div", class_="-phs -pvxs row _no-g _4cl-3cm-shs")
        status_text.write(f"Found {len(listings)} listings. Extracting details...")
        progress_bar.progress(90)

        # Extract details
        for listing in listings:
            title_elem = listing.find("h3", class_="name") or listing.find("a", class_="name")
            price_elem = listing.find("div", class_="prc") or listing.find("span", class_="p24_price")
            desc_elem = listing.find("p", class_="dscr") or \
                        listing.find("span", class_="p24_excerpt") or \
                        listing.find("div", class_="s-prc-w") or \
                        listing.find("div", class_="bdg _dsct _sm") or \
                        listing.find("div", class_="info")  # Added for potential description

            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            description = desc_elem.get_text(strip=True) if desc_elem else "N/A"

            if title != "N/A":
                products.append({
                    "Title": title,
                    "Price": price,
                    "Description": description
                })

        # Display results
        if products:
            st.success(f"### Scraped {len(products)} Products:")
            for i, product in enumerate(products, 1):
                with st.expander(f"Product {i}: {product['Title'][:50]}..."):
                    st.write(f"**Title:** {product['Title']}")
                    st.write(f"**Price:** {product['Price']}")
                    st.write(f"**Description:** {product['Description']}")
            df = pd.DataFrame(products)
            csv = df.to_csv(index=False).encode('utf-8')
            csv_placeholder.download_button(
                label="Download as CSV",
                data=csv,
                file_name="jumia_flash_sales.csv",
                mime="text/csv"
            )
        else:
            st.warning("No products found. Try Selenium or check selectors in Debug Mode.")

        st.info(f"Debug: Found {len(listings)} potential listings.")
        progress_bar.progress(100)
        status_text.write("Scrape complete!")

    except Exception as e:
        status_text.error(f"Error: {e}")
        progress_bar.progress(0)