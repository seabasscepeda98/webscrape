from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.binary_location = '/usr/bin/chromium-browser'

service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

# List to store all property data
property_data = []

try:
    # Navigate to disclaimer page
    driver.get("https://apps.putnam-fl.com/coc/taxdeeds/public/disclaimer.php")
    print("Loaded disclaimer page")
    
    # Click the first "I Accept" button
    wait = WebDriverWait(driver, 10)
    accept_button = wait.until(
        EC.element_to_be_clickable((By.CLASS_NAME, "acceptbutton"))
    )
    accept_button.click()
    time.sleep(3)
    
    print(f"Current URL: {driver.current_url}")
    
    # Find all Property Appraiser Lookup links
    lookup_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Property Appraiser Lookup")
    
    # Extract all the URLs
    property_urls = [link.get_attribute('href') for link in lookup_links]
    
    print(f"Found {len(property_urls)} properties")
    
    # Visit each property URL
    for i, url in enumerate(property_urls):
        print(f"\nProcessing property {i+1}/{len(property_urls)}")
        print(f"URL: {url}")
        
        driver.get(url)
        time.sleep(2)
        
        # Handle the second disclaimer on the property page
        try:
            # Wait for the "I Accept" button with id="btnAccept"
            second_accept = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "btnAccept"))
            )
            print("Found second disclaimer, accepting...")
            second_accept.click()
            time.sleep(2)
        except:
            print("No second disclaimer found or already dismissed")
        
        # Extract property information
        try:
            # Extract Parcel Number from URL
            # URL format: https://apps.putnam-fl.com/pa/property/?type=api&parcel=02-12-27-1829-0110-0090
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(driver.current_url)
            query_params = parse_qs(parsed_url.query)
            parcel_number = query_params.get('parcel', ['N/A'])[0]
            
            # Extract 911 Address
            try:
                address_element = driver.find_element(By.CLASS_NAME, "parcel-911-address")
                address_divs = address_element.find_elements(By.TAG_NAME, "div")
                address_parts = [div.text for div in address_divs if div.text.strip()]
                address = ' '.join(address_parts) if address_parts else "None"
            except:
                address = "None"
            
            # Extract Description - it's in the summary card
            try:
                # Find all rows in the summary card
                description_label = driver.find_element(By.XPATH, "//div[@class='col-md-2 font-weight-bold' and contains(text(), 'Description:')]")
                # Get the sibling div that contains the description
                description = description_label.find_element(By.XPATH, "following-sibling::div[@class='col-md-10']").text
            except:
                description = "N/A"

            # Extract Market Value
            try:
                # Find row that matches Market Value
                marketval_label = driver.find_element(By.XPATH, "//div[@class='row-heading' and contains(text(), 'Market Value:')]")
                 # Get the sibling div that contains the Market Value
                marketval = marketval_label.find_element(By.XPATH, "following-sibling::div[@class='text-right pr-2']").text
            except: 
                marketval = "N/A"

            # Extract Total acreage
            try:
                # Find row that matches Total acreage
                acreage_label = driver.find_element(By.XPATH, "//div[@class='row-heading' and contains(text(), 'Total Acreage:')]")
                # Get the sibling div that contains the Total acreage
                acreage = acreage_label.find_element(By.XPATH, "following-sibling::div[@class='text-right pr-2']").text
            except: 
                acreage = "N/A"

            # Extract Property Use 
            try:
                # Find row that matches Total acreage
                prop_use_label = driver.find_element(By.XPATH, "//div[@class='row-heading' and contains(text(), 'Property Use:')]")
                # Get the sibling div that contains the Total acreage
                prop_use = prop_use_label.find_element(By.XPATH, "following-sibling::div[@class='text-right pr-2']").text
            except: 
                prop_use = "N/A"                
            
            print(f"Parcel: {parcel_number}")
            print(f"Address: {address}")
            print(f"Description: {description}")
            print(f"Market Value: {marketval}")
            print(f"Total Acreage: {acreage}")
            print(f"Property Use: {prop_use}")

            
            # Add to property data list
            property_data.append({
                'parcel_number': parcel_number,
                'address': address,
                'description': description,
                'market_value': marketval,
                'total_acreage': acreage,
                'url': url
            })
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            property_data.append({
                'parcel_number': 'Error',
                'address': 'Error',
                'description': 'Error',
                'market_value': 'Error',
                'total_acreage': 'Error',
                'url': url
            })
        
        # Save the property page
        with open(f'property_{i+1}.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        print(f"Saved property_{i+1}.html")
    
    print("\nAll properties processed!")
    
    # Save data to CSV file
    if property_data:
        with open('property_data.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['parcel_number', 'address', 'description', 'market_value', 'total_acreage', 'url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for prop in property_data:
                writer.writerow(prop)
        
        print(f"\nSaved {len(property_data)} properties to property_data.csv")
    
    # Print summary
    print("\n=== SUMMARY ===")
    for i, prop in enumerate(property_data, 1):
        print(f"\nProperty {i}:")
        print(f"  Parcel: {prop['parcel_number']}")
        print(f"  Address: {prop['address']}")
        print(f"  Description: {prop['description']}")
    
finally:
    driver.quit()