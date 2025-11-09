import streamlit as st
import requests
from bs4 import BeautifulSoup

# Set up the Streamlit app
st.title("Betika Kenya Scraper")

# Function to scrape Betika
def scrape_betika():
    url = "https://www.betika.com/"  # Replace with the specific URL if needed
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad responses

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Example: Find specific elements (e.g., match odds)
    matches = soup.find_all('div', class_='match')  # Update with the correct class or tag

    results = []
    for match in matches:
        team1 = match.find('div', class_='team1').get_text(strip=True)
        team2 = match.find('div', class_='team2').get_text(strip=True)
        odds = match.find('div', class_='odds').get_text(strip=True)
        results.append(f"{team1} vs {team2}: {odds}")

    return results

if st.button("Scrape Betika"):
    try:
        matches = scrape_betika()
        st.write("Latest Matches and Odds:")
        for match in matches:
            st.write(match)
    except Exception as e:
        st.error(f"Error: {e}")
