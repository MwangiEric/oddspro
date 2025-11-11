import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("Jumia Flash Sales Scraper")

# URL for Jumia flash sales
url = "https://www.jumia.co.ke/phones-tablets/flash-sales/"

if st.button("Scrape Flash Sales"):
    try:
        # Set headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        }

        # Send a GET request to the URL
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Find product listings (update class based on inspection)
        listings = soup.find_all("article", class_="prd _fb col c-prd")

        # Extract details from each listing
        products = []
        for listing in listings:
            # Safely extract title, price, and description
            title_elem = listing.find("h3", class_="name")
            price_elem = listing.find("div", class_="prc")
            desc_elem = listing.find("div", class_="s-prc-w")  # Adjust class if needed

            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            description = desc_elem.get_text(strip=True) if desc_elem else "N/A"

            products.append({
                "Title": title,
                "Price": price,
                "Description": description
            })

        # Display the results
        if products:
            st.write(f"### Scraped {len(products)} Products:")
            for product in products:
                st.write(f"**Title:** {product['Title']}")
                st.write(f"**Price:** {product['Price']}")
                st.write(f"**Description:** {product['Description']}")
                st.write("---")
        else:
            st.write("No products found. Check the class names or URL.")

        # Debugging: Show number of listings found
        st.write(f"Debug: Found {len(listings)} listings.")

    except requests.RequestException as e:
        st.error(f"Network error: {e}")
    except Exception as e:
        st.error(f"Error: {e}")