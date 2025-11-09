import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("Property Listings Scraper")

# Input for the URL to scrape
url = st.text_input("Enter the URL to scrape:", 
                    "https://www.property24.co.ke/property-for-sale-in-ruiru-c1849?fromprice=20000000&toprice=40000000")

if st.button("Scrape Properties"):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all property listings
        listings = soup.find_all('div', class_='p24_regularTile')

        # Extract details from each listing
        properties = []
        for listing in listings:
            title = listing.find('span', class_='p24_propertyTitle').get_text(strip=True)
            price = listing.find('span', class_='p24_price').get_text(strip=True)
            location = listing.find('span', class_='p24_location').get_text(strip=True)
            description = listing.find('span', class_='p24_excerpt').get_text(strip=True)

            properties.append({
                'Title': title,
                'Price': price,
                'Location': location,
                'Description': description
            })

        # Display the results in the Streamlit app
        if properties:
            st.write("### Scraped Properties:")
            for property in properties:
                st.write(f"**Title:** {property['Title']}")
                st.write(f"**Price:** {property['Price']}")
                st.write(f"**Location:** {property['Location']}")
                st.write(f"**Description:** {property['Description']}")
                st.write("---")
        else:
            st.write("No properties found.")

    except Exception as e:
        st.error(f"Error: {e}")
