if st.button("Scrape Properties"):
    try:
        response = requests.get(url)
        response.raise_for_status()
        st.write("Successfully fetched the URL!")  # Debugging output

        soup = BeautifulSoup(response.content, 'html.parser')
        listings = soup.find_all('div', class_='p24_regularTile')

        st.write(f"Found {len(listings)} listings.")  # Debugging output
        properties = []

        for listing in listings:
            # Extract relevant data
            title = listing.find('span', class_='p24_propertyTitle').get_text(strip=True)
            price = listing.find('span', class_='p24_price').get_text(strip=True)
            location = listing.find('span', class_='p24_location').get_text(strip=True)
            description = listing.find('span', class_='p24_excerpt').get_text(strip=True)
            properties.append({'Title': title, 'Price': price, 'Location': location, 'Description': description})

        # Display results
        for property in properties:
            st.write(f"Title: {property['Title']}, Price: {property['Price']}, Location: {property['Location']}, Description: {property['Description']}")

    except Exception as e:
        st.error(f"Error: {e}")
