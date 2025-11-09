import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("Jumia Flash Sales Scraper")

# URL for the Jumia flash sales
url = "https://cors.ericmwangi13.workers.dev/?url=https://www.jumia.co.ke/phones-tablets/flash-sales/#catalog-listing"

if st.button("Scrape Flash Sales"):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find product listings
        listings = soup.find_all('div', class_='p24_regularTile')  # Adjust class name if necessary

        # Extract details from each listing
        products = []
        for listing in listings:
            title = listing.find('span', class_='p24_propertyTitle').get_text(strip=True)
            price = listing.find('span', class_='p24_price').get_text(strip=True)
            description = listing.find('span', class_='p24_excerpt').get_text(strip=True)

            products.append({
                'Title': title,
                'Price': price,
                'Description': description
            })

        # Display the results
        if products:
            st.write("### Scraped Products:")
            for product in products:
                st.write(f"**Title:** {product['Title']}")
                st.write(f"**Price:** {product['Price']}")
                st.write(f"**Description:** {product['Description']}")
                st.write("---")
        else:
            st.write("No products found.")

    except Exception as e:
        st.error(f"Error: {e}")
