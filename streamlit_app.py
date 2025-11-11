import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse

st.title("Jumia Flash Sales Scraper")

# Target URL for Jumia flash sales
target_url = "https://www.jumia.co.ke/phones-tablets/flash-sales/"
# Format with CORS proxy
url = f"https://cors.ericmwangi13.workers.dev/?url={urllib.parse.quote(target_url, safe=':/?#')}"

debug_mode = st.checkbox("Enable Debug Mode (Show Raw HTML)")

if st.button("Scrape Flash Sales"):
    try:
        # Set headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        }

        # Send a GET request to the proxied URL
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Raise an error for bad responses (e.g., 403)

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Debug: Show raw HTML if enabled (limited to first 2000 chars to avoid overload)
        if debug_mode:
            st.write("### Raw HTML Preview (First 2000 chars):")
            st.code(soup.prettify()[:2000], language="html")

        # Find product listings (common Jumia selector; adjust based on debug output)
        listings = soup.find_all("article", class_="prd _fb col c-prd") or \
                   soup.find_all("div", class_="-phs -pvxs row _no-g _4cl-3cm-shs")  # Fallback to your original

        # Extract details from each listing
        products = []
        for listing in listings:
            # Safely extract title, price, and description (adjust selectors as needed)
            title_elem = listing.find("h3", class_="name") or listing.find("a", class_="name")
            price_elem = listing.find("div", class_="prc") or listing.find("span", class_="p24_price")
            desc_elem = listing.find("p", class_="dscr") or listing.find("span", class_="p24_excerpt")

            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            description = desc_elem.get_text(strip=True) if desc_elem else "N/A"

            # Skip if no title (invalid listing)
            if title != "N/A":
                products.append({
                    "Title": title,
                    "Price": price,
                    "Description": description
                })

        # Display the results
        if products:
            st.success(f"### Scraped {len(products)} Products:")
            for i, product in enumerate(products, 1):
                with st.expander(f"Product {i}: {product['Title'][:50]}..."):
                    st.write(f"**Title:** {product['Title']}")
                    st.write(f"**Price:** {product['Price']}")
                    st.write(f"**Description:** {product['Description']}")
        else:
            st.warning("No products found. This may be due to JavaScript-loaded content. Enable Debug Mode to inspect HTML and update selectors.")

        # Debugging: Show number of listings found
        st.info(f"Debug: Found {len(listings)} potential listings.")

    except requests.RequestException as e:
        st.error(f"Network/Proxy Error (e.g., Forbidden or Timeout): {e}")
        st.info("Tip: The proxy might be rate-limited. Try again later or use a different proxy.")
    except Exception as e:
        st.error(f"Unexpected Error: {e}")