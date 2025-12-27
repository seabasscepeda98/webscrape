from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.binary_location = '/usr/bin/chromium-browser'

service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

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
        
        # Save the property page
        with open(f'property_{i+1}.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        print(f"Saved property_{i+1}.html")
    
    print("\nAll properties processed!")
    
finally:
    driver.quit()