# Step 1: Install necessary packages
!pip install pandas selenium beautifulsoup4 PyGithub

# Step 2: Set up Chrome driver
!apt-get update
!apt-get install -y chromium-chromedriver
!cp /usr/lib/chromium-browser/chromedriver /usr/bin

import pandas as pd
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit, urljoin
import xml.etree.ElementTree as ET
from github import Github
from datetime import datetime

# Step 3: Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# List of URLs to scrape
urls = [
    "https://diks.net/voertuigen/1/personenautos",
    "https://diks.net/voertuigen/2/bestelbussen",
    "https://diks.net/voertuigen/3/personenbussen",
    "https://diks.net/voertuigen/4/koelwagens",
    "https://diks.net/voertuigen/6/autotransporters",
    "https://diks.net/voertuigen/7/vrachtwagens",
    "https://diks.net/voertuigen/62/elektrisch"
]

# Set up Chrome options for Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Set up Selenium WebDriver
driver = webdriver.Chrome(options=options)

# List to store all products from all URLs
all_products = []

for url in urls:
    logging.debug(f"URL to scrape: {url}")
    
    driver.get(url)
    
    # Wait for the page to load by waiting for a specific element
    try:
        element_present = EC.presence_of_element_located((By.CSS_SELECTOR, '.grid a'))
        WebDriverWait(driver, 10).until(element_present)
    except TimeoutException:
        logging.error("Timed out waiting for page to load")
        continue  # Skip to the next URL

    # Get the page content
    page_content = driver.page_source
    logging.debug("Page content retrieved")
    
    # Parse the page content
    soup = BeautifulSoup(page_content, 'html.parser')
    logging.debug("Page content parsed with BeautifulSoup")
    
    # Find all product cards
    product_cards = soup.select('.grid a')
    logging.debug(f"Found {len(product_cards)} product cards")
    
    # Extract details from each product card
    for index, card in enumerate(product_cards):
        logging.debug(f"Processing product card {index + 1}")
        
        def extract_text(element, class_name=None, attr_name=None):
            if element:
                if class_name:
                    text = element.text.strip()
                elif attr_name:
                    text = element[attr_name].strip()
                else:
                    text = element.strip()
                return text
            return None

        product_name = extract_text(card.find(class_='text-brand-500'), class_name=True)
        logging.debug(f"Product name: {product_name}")
        
        product_price = extract_text(card.find(attrs={"data-testid": "VehicleCard.price"}), class_name=True)
        logging.debug(f"Product price: {product_price}")
        
        product_url = extract_text(card, attr_name='href')
        if product_url:
            product_url = urljoin("https://diks.net/", product_url)
            # Remove query parameters
            parsed_url = urlsplit(product_url)
            product_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', ''))
        logging.debug(f"Product URL: {product_url}")
        
        product_image = extract_text(card.find('img'), attr_name='src')
        logging.debug(f"Product image URL: {product_image}")
        
        # Extract id from the image URL using regex
        product_id_match = re.search(r'/category/([^/]+)/', product_image)
        product_id = product_id_match.group(1) if product_id_match else None
        logging.debug(f"Product ID: {product_id}")

        all_products.append({
            'id': product_id,
            'name': product_name,
            'price': product_price,
            'url': product_url,
            'image_url': product_image
        })

# Close the Selenium WebDriver
driver.quit()

# Create the root element of the RSS feed
rss = ET.Element('rss', version='2.0')
channel = ET.SubElement(rss, 'channel')

# Add channel information
ET.SubElement(channel, 'title').text = 'Diks Vehicles'
ET.SubElement(channel, 'link', {'rel': 'self', 'href': 'https://diks.net/', 'crossorigin': 'anonymous'})
ET.SubElement(channel, 'updated').text = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

# Add items to the RSS feed
for product in all_products:
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'id').text = product['id'] or 'No ID'
    ET.SubElement(item, 'title').text = product['name'] or 'No Title'
    ET.SubElement(item, 'link', {'href': product['url'], 'crossorigin': 'anonymous'}).text = product['url'] or 'No Link'
    ET.SubElement(item, 'language').text = 'en-US'
    # ET.SubElement(item, 'image_link', {'crossorigin': 'anonymous'}).text = product['image_url'] or 'No Image'
    ET.SubElement(item, 'google_product_category').text = '404'  # Example category

# Convert the ElementTree to a string and write it to a file
rss_tree = ET.ElementTree(rss)
rss_tree.write('/content/scraped_products.xml', encoding='utf-8', xml_declaration=True)

logging.debug("Data saved to RSS XML file: scraped_products.xml")
print("Scraping completed and data saved to /content/scraped_products.xml")

# Step 4: Upload the file to GitHub
from github import Github

# GitHub token
key = "Replace wit git token"

# GitHub repository name
repo_name = "Diks"

# Authenticate to GitHub
g = Github(key)

# Get the repository
repo = g.get_user().get_repo(repo_name)

# Read the XML file content
with open('/content/scraped_products.xml', 'r') as file:
    content = file.read()

# Create or update the file in the repository
try:
    contents = repo.get_contents("scraped_products.xml")
    repo.update_file(contents.path, "Update XML file", content, contents.sha, branch="main")
except:
    repo.create_file("scraped_products.xml", "Add XML file", content, branch="main")

# GitHub Pages URL
github_pages_url = f"https://github.com/rvhinthum/{repo_name}/blob/main/scraped_products.xml"

print("File has been uploaded and can be accessed at:")
print(github_pages_url)