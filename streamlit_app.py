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
from transformers import pipeline
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("Jumia Flash Sales AI Agent")

# Target base URL
base_url = "https://www.jumia.co.ke/phones-tablets/flash-sales/"

# Initialize free Hugging Face model for text processing
classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased")

# UI Options
query = st.text_input("Enter query (e.g., 'phones under 15000' or 'Tecno')", value="flash sales")
scrape_method = st.radio("Scrape Method", ["Requests (Static via Proxy)", "Selenium (Dynamic Content)"])
debug_mode = st.checkbox("Enable Debug Mode (Show Raw HTML)")
max_pages = st.slider("Max Pages to Scrape (Requests Only)", 1, 10, 5)
max_scrolls = st.slider("Max Page Scrolls (Selenium Only)", 1, 5, 3)
max_retries = st.slider("Max Retries on Failure", 1, 3, 2)

# Placeholder for progress
progress_bar = st.progress(0)
status_text = st.empty()
csv_placeholder = st.empty()

# Function to parse price (e.g., "KSh 11,500" -> 11500)
def parse_price(price_str):
    try:
        return float(re.sub(r"[^\d.]", "", price_str))
    except:
        return float("inf")

# AI Filter: Filter products based on query
def filter_products(products, query):
    if not products:
        return []
    if "under" in query.lower():
        try:
            max_price = float(re.search(r"under\s*(\d+)", query, re.IGNORECASE).group(1))
        except:
            max_price = float("inf")
    else:
        max_price = float("inf")
    
    keywords = [word.lower() for word in query.split() if word.lower() not in ["under", "phones"]]
    
    filtered = []
    for product in products:
        title = product["title"].lower()
        price = parse_price(product["price"])
        relevance = classifier(title)[0]["score"] if keywords else 1.0
        if price <= max_price and (not keywords or any(k in title for k in keywords)) and relevance > 0.5:
            filtered.append(product)
    
    return filtered

# Scraper Function
def scrape_jumia(method, max_pages, max_scrolls, max_retries):
    all_products = []
    for attempt in range(max_retries):
        try:
            status_text.write(f"Attempt {attempt + 1}/{max_retries}...")
            progress_bar.progress(10 + attempt * 10)
            
            if method == "Selenium (Dynamic Content)":
                logger.info("Starting Selenium scrape")
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
                
                driver.get(base_url)
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article.prd._fb.col.c-prd")))
                progress_bar.progress(30)
                
                for i in range(max_scrolls):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    progress_bar.progress(30 + (i + 1) * (50 // max_scrolls))
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                driver.quit()
                listings = soup.find_all("article", class_="prd _fb col c-prd")
                
            else:
                logger.info("Starting proxy scrape with pagination")
                listings = []
                for page in range(1, max_pages + 1):
                    page_param = f"?page={page}" if page > 1 else ""
                    target_page_url = base_url + page_param
                    proxy_page_url = f"https://cors.ericmwangi13.workers.dev/?url={urllib.parse.quote(target_page_url, safe=':/?#')}"
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    response = requests.get(proxy_page_url, headers=headers, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, "html.parser")
                    
                    if debug_mode:
                        st.write(f"### Raw HTML Preview for Page {page} (First 2000 chars):")
                        st.code(soup.prettify()[:2000], language="html")
                    
                    page_listings = soup.find_all("article", class_="prd _fb col c-prd")
                    listings.extend(page_listings)
                    status_text.write(f"Page {page}: Found {len(page_listings)} listings")
                    progress_bar.progress(50 + (page / max_pages) * 40)
                    
                    if not page_listings:  # Stop if no more listings
                        break
            
            # Extract from all listings
            products = []
            for listing in listings:
                title_elem = listing.find("h3", class_="name") or listing.find("a", class_="name")
                price_elem = listing.find("div", class_="prc") or listing.find("span", class_="p24_price")
                desc_elem = listing.find("div", class_="bdg _dsct _sm") or \
                            listing.find("p", class_="dscr") or \
                            listing.find("div", class_="s-prc-w") or \
                            listing.find("div", class_="info") or \
                            listing.find("div", class_="tag _dsct")  # Added for discounts
                
                title = title_elem.get_text(strip=True) if title_elem else "N/A"
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                description = desc_elem.get_text(strip=True) if desc_elem else "N/A"
                
                if title != "N/A":
                    products.append({
                        "title": title,
                        "price": price,
                        "description": description
                    })
            
            all_products = products  # Use collected products
            if all_products:
                break  # Success
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                status_text.error(f"All retries failed: {str(e)}")
                progress_bar.progress(0)
                return []
    
    return all_products

# Main Logic
if st.button("Scrape and Filter"):
    try:
        # Scrape data
        status_text.write("Scraping Jumia...")
        products = scrape_jumia(scrape_method, max_pages, max_scrolls, max_retries)
        
        # Filter with AI
        status_text.write("Filtering results with AI...")
        filtered_products = filter_products(products, query)
        
        # Display results
        if filtered_products:
            st.success(f"### Scraped and Filtered {len(filtered_products)} Products:")
            for i, product in enumerate(filtered_products, 1):
                with st.expander(f"Product {i}: {product['title'][:50]}..."):
                    st.write(f"**Title:** {product['title']}")
                    st.write(f"**Price:** {product['price']}")
                    st.write(f"**Description:** {product['description']}")
            
            # CSV Export
            df = pd.DataFrame(filtered_products)
            csv = df.to_csv(index=False).encode('utf-8')
            csv_placeholder.download_button(
                label="Download as CSV",
                data=csv,
                file_name="jumia_flash_sales.csv",
                mime="text/csv"
            )
        else:
            st.warning("No products found matching your query. Try increasing Max Pages or using Selenium.")
        
        st.info(f"Debug: Scraped {len(products)} total products before filtering.")
        progress_bar.progress(100)
        status_text.write("Complete!")
    
    except Exception as e:
        status_text.error(f"Error: {str(e)}")
        progress_bar.progress(0)