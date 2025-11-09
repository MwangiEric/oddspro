import requests
from bs4 import BeautifulSoup

# Define the URL to scrape
url = "https://www.property24.co.ke/property-for-sale-in-ruiru-c1849?fromprice=20000000&toprice=40000000"

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
        'title': title,
        'price': price,
        'location': location,
        'description': description
    })

# Print the extracted properties
for property in properties:
    print(f"Title: {property['title']}")
    print(f"Price: {property['price']}")
    print(f"Location: {property['location']}")
    print(f"Description: {property['description']}")
    print("-" * 40)
