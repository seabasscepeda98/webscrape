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
            # Extract Parcel Number from the details card header
            parcel_element = driver.find_element(By.CSS_SELECTOR, ".card-header.bg-primary.text-white.p-1.pl-2")
            parcel_text = parcel_element.text
            # Extract parcel number from text like "Interim Parcel Details | 12-10-23-4183-0980-0020 | 30607"
            if '|' in parcel_text:
                parts = parcel_text.split('|')
                parcel_number = parts[1].strip() if len(parts) > 1 else "N/A"
            else:
                parcel_number = "N/A"
            
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
            
            print(f"Parcel: {parcel_number}")
            print(f"Address: {address}")
            print(f"Description: {description}")
            
            # Add to property data list
            property_data.append({
                'parcel_number': parcel_number,
                'address': address,
                'description': description,
                'url': url
            })
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            property_data.append({
                'parcel_number': 'Error',
                'address': 'Error',
                'description': 'Error',
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
            fieldnames = ['parcel_number', 'address', 'description', 'url']
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