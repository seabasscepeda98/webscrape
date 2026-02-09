from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import re
from datetime import datetime

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.binary_location = '/usr/bin/chromium-browser'

service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

# List to store all property data
property_data = []

def select_auction_date(driver):
    """
    Display available auction dates and let user select one by entering the date
    Returns the selected auction value
    """
    try:
        # Wait for the dropdown to be present
        select_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "chooseauct"))
        )
        
        # Create Select object
        select = Select(select_element)
        
        # Get all available options
        options = select.options
        
        # Build a list of available dates (skip the first optgroup if present)
        available_dates = []
        date_lookup = {}  # Map formatted dates to dropdown values
        
        for option in options:
            value = option.get_attribute('value')
            text = option.text
            if value and text:  # Skip empty options
                # Parse the date text (format: MM/DD/YYYY)
                try:
                    date_obj = datetime.strptime(text, "%m/%d/%Y")
                    formatted_date = date_obj.strftime("%m/%d/%Y")  # Convert to dd/MM/YYYY
                    
                    available_dates.append({
                        'value': value,
                        'text': text,  # Original MM/DD/YYYY format
                        'formatted': formatted_date,  # dd/MM/YYYY format
                        'date_obj': date_obj
                    })
                    
                    # Store in lookup dictionary
                    date_lookup[date_obj] = value
                    
                except ValueError:
                    # If date parsing fails, skip this option
                    continue
        
        if not available_dates:
            print("No auction dates found!")
            return None
        
        # Sort by date (most recent first)
        available_dates.sort(key=lambda x: x['date_obj'], reverse=True)
        
        # Display available dates
        print("\n" + "="*60)
        print("AVAILABLE AUCTION DATES")
        print("="*60)
        for date_info in available_dates:
            print(f"  {date_info['formatted']}")
        print("="*60)
        
        # Get user selection
        while True:
            try:
                user_input = input(f"\nEnter auction date (MM/dd/YYYY format) or 'q' to quit: ").strip()
                
                if user_input.lower() == 'q':
                    print("Exiting...")
                    return None
                
                # Validate date format
                try:
                    user_date = datetime.strptime(user_input, "%m/%d/%Y")
                    formatted_input = user_date.strftime("%m/%d/%Y")
                    
                    # Check if date exists in available dates
                    if user_date in date_lookup:
                        selected_value = date_lookup[user_date]
                        print(f"\n✓ Selected: {formatted_input}")
                        print(f"{selected_value}")
                        return selected_value
                    else:
                        print(f"\n✗ Date '{formatted_input}' not found in available auctions.")
                        print("Please choose from the available dates listed above.")
                        
                except ValueError:
                    print("\nInvalid date format. Please use MM/dd/YYYY format (e.g., 01/07/2026)")
                    
            except KeyboardInterrupt:
                print("\n\nScript cancelled by user")
                return None
                
    except Exception as e:
        print(f"Error selecting auction date: {e}")
        return None

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
    
    # SELECT AUCTION DATE
    selected_auction_value = select_auction_date(driver)
    
    if selected_auction_value is None:
        print("No auction date selected. Exiting...")
        driver.quit()
        exit()
    
    # Submit the form with selected auction date
    try:
        select_element = driver.find_element(By.NAME, "chooseauct")
        select = Select(select_element)
        select.select_by_value(selected_auction_value)
        
        # Submit the form
        form = driver.find_element(By.NAME, "chooseauctf")
        form.submit()
        
        print(f"\nLoading auction data...")
        time.sleep(3)
        
        print(f"Current URL after selection: {driver.current_url}")
        
    except Exception as e:
        print(f"Error submitting auction selection: {e}")
        driver.quit()
        exit()
    
    # Extract T.D. numbers and base bids from the main listing page
    print("\n=== Extracting T.D. Numbers and Base Bids ===")
    
    # Wait for the main table to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "maintable"))
    )
    
    # Create a mapping of parcel numbers to T.D. numbers and base bids
    td_mapping = {}
    redeemed_parcels = set()  # Track redeemed parcels to skip later
    
    # Find all rows in the table
    table = driver.find_element(By.ID, "maintable")
    rows = table.find_elements(By.TAG_NAME, "tr")
    
    current_td_number = None
    current_base_bid = None
    current_list_number = None
    is_current_redeemed = False
    
    for row in rows:
        # Check if this row contains a redeemed indicator
        redeemed_cells = row.find_elements(
            By.XPATH, 
            ".//td[@width='525' and contains(@background, 'redeemed.gif')]"
        )
        
        if redeemed_cells:
            is_current_redeemed = True
            print(f"Found REDEEMED property in this row")
        
        # Check if this row contains a T.D. number and list number
        th_elements = row.find_elements(By.TAG_NAME, "th")
        for th in th_elements:
            text = th.text.strip()
            if text.startswith("T.D."):
                current_td_number = text
                # Reset redeemed status for new T.D. number
                is_current_redeemed = False
                
                # Try to find the list number in the preceding td cell
                try:
                    td_cells = row.find_elements(By.TAG_NAME, "td")
                    if td_cells:
                        # The list number is in the first td cell (e.g., "1.", "2.", etc.)
                        list_num_text = td_cells[0].text.strip()
                        # Remove the period if present
                        current_list_number = list_num_text.rstrip('.')
                    else:
                        current_list_number = "N/A"
                except Exception as e:
                    print(f"Could not extract list number: {e}")
                    current_list_number = "N/A"
                
                print(f"Found List Number: {current_list_number}, T.D. number: {current_td_number}")
        
        # Check if this row contains the base bid
        if current_td_number:
            # Look for base bid in the row (it's in a <th> with <u> tag)
            th_with_u = row.find_elements(By.XPATH, ".//th/u")
            if th_with_u:
                bid_text = th_with_u[0].text.strip()
                # Only capture if it starts with $ (monetary value)
                if bid_text.startswith("$"):
                    current_base_bid = bid_text
                    print(f"  Base Bid: {current_base_bid}")
        
        # Check if this row contains parcel information
        td_elements = row.find_elements(By.TAG_NAME, "td")
        for td in td_elements:
            text = td.text
            # Look for "Parcel Number" in the text
            if "Parcel Number" in text:
                # Extract parcel number using regex
                parcel_match = re.search(r'Parcel Number (\S+)', text)
                if parcel_match and current_td_number:
                    parcel_number = parcel_match.group(1)
                    
                    if is_current_redeemed:
                        redeemed_parcels.add(parcel_number)
                        print(f"  Parcel {parcel_number}: REDEEMED (will skip)")
                    else:
                        td_mapping[parcel_number] = {
                            'list_number': current_list_number if current_list_number else "N/A",
                            'td_number': current_td_number,
                            'base_bid': current_base_bid if current_base_bid else "N/A"
                        }
                        print(f"  Mapped to Parcel: {parcel_number} (active)")
    
    print(f"\nTotal active mappings created: {len(td_mapping)}")
    print(f"Total redeemed parcels skipped: {len(redeemed_parcels)}")
    
    # Print list of redeemed parcels
    if redeemed_parcels:
        print(f"\nRedeemed parcels (will be excluded):")
        for parcel in sorted(redeemed_parcels):
            print(f"  - {parcel}")
    
    # Find all Property Appraiser Lookup links
    lookup_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Property Appraiser Lookup")
    
    # Extract URLs and filter out redeemed properties
    property_urls = []
    
    for link in lookup_links:
        url = link.get_attribute('href')
        
        # Extract parcel number from URL to check if redeemed
        try:
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            parcel_number = query_params.get('parcel', [''])[0]
            
            # Skip if this parcel is in the redeemed set
            if parcel_number in redeemed_parcels:
                continue
            
            property_urls.append(url)
            
        except Exception as e:
            print(f"Error parsing URL {url}: {e}")
            # Include URL if we can't parse it to be safe
            property_urls.append(url)
    
    
    print(f"\n{'='*60}")
    print(f"Found {len(property_urls)} active properties to process")
    print(f"{'='*60}")
    
    # Print the active property URLs that will be processed
    if property_urls:
        print(f"\nActive properties to process:")
        for idx, url in enumerate(property_urls, 1):
            # Extract parcel from URL for display
            try:
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                parcel = query_params.get('parcel', ['Unknown'])[0]
                print(f"  {idx}. Parcel: {parcel}")
            except:
                print(f"  {idx}. URL: {url}")
    
    print(f"\n{'='*60}")
    
    # Visit each property URL
    for i, url in enumerate(property_urls):
        print(f"\n{'='*60}")
        print(f"Processing property {i+1}/{len(property_urls)}")
        print(f"URL: {url}")
        
        driver.get(url)
        
        # Handle the second disclaimer on the property page (only on first property)
        if i == 0:
            try:
                second_accept = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "btnAccept"))
                )
                print("Found second disclaimer, accepting...")
                second_accept.click()
                time.sleep(2)
            except TimeoutException:
                print("No second disclaimer found or already dismissed")
        else:
            # Wait briefly for page to load instead of checking for disclaimer
            time.sleep(1)
        
        # Extract property information
        try:
            # Extract Parcel Number from URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(driver.current_url)
            query_params = parse_qs(parsed_url.query)
            parcel_number = query_params.get('parcel', ['N/A'])[0]
            
            # Double-check if this parcel is redeemed (safety check)
            if parcel_number in redeemed_parcels:
                print(f"Skipping redeemed parcel: {parcel_number}")
                continue
            
            # Get T.D. number and base bid from mapping
            td_info = td_mapping.get(parcel_number, {'list_number': 'N/A', 'td_number': 'N/A', 'base_bid': 'N/A'})
            list_number = td_info['list_number']
            td_number = td_info['td_number']
            base_bid = td_info['base_bid']
            
            print(f"List Number: {list_number}")
            print(f"Parcel: {parcel_number}")
            print(f"T.D. Number: {td_number}")
            print(f"Base Bid: {base_bid}")
            
            # Extract 911 Address
            try:
                address_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "parcel-911-address"))
                )
                address_divs = address_element.find_elements(By.TAG_NAME, "div")
                address_parts = [div.text for div in address_divs if div.text.strip()]
                address = ' '.join(address_parts) if address_parts else "None"
            except (TimeoutException, NoSuchElementException):
                address = "None"
            
            # Extract Description - wait for it to load
            try:
                description_label = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//div[@class='col-md-2 font-weight-bold' and contains(text(), 'Description:')]"))
                )
                description = description_label.find_element(By.XPATH, 
                    "following-sibling::div[@class='col-md-10']").text
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Description not found: {e}")
                description = "N/A"

            # Extract Market Value - wait for the summary card to load
            try:
                # Wait for the summary card to be present
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "summary-card"))
                )
                
                marketval_label = driver.find_element(By.XPATH, 
                    "//td[@class='row-heading' and contains(text(), 'Market Adjusted:')]")
                marketval = marketval_label.find_element(By.XPATH, 
                    "following-sibling::td[@class='text-right pr-2']").text
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Market Value not found: {e}")
                marketval = "N/A"

            # Extract Total Acreage
            try:
                acreage_label = driver.find_element(By.XPATH, 
                    "//td[@class='row-heading' and contains(text(), 'Total Acreage:')]")
                acreage = acreage_label.find_element(By.XPATH, 
                    "following-sibling::td[@class='text-right pr-2']").text
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Total Acreage not found: {e}")
                acreage = "N/A"

            # Extract Property Use 
            try:
                prop_use_label = driver.find_element(By.XPATH, 
                    "//td[@class='row-heading' and contains(text(), 'Property Use:')]")
                prop_use = prop_use_label.find_element(By.XPATH, 
                    "following-sibling::td[@class='text-right pr-2']").text
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Property Use not found: {e}")
                prop_use = "N/A"                
            
            print(f"Address: {address}")
            print(f"Description: {description}")
            print(f"Market Adjusted: {marketval}")
            print(f"Total Acreage: {acreage}")
            print(f"Property Use: {prop_use}")

            # Extract Land Details from Land tab
            land_details = {}
            try:
                # Click the Land tab
                land_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "tab-Land"))
                )
                land_tab.click()
                print("Clicked Land tab")
                
                # Wait for tab content to be visible and loaded
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "details-Land"))
                )
                
                # Wait for content to fully load
                time.sleep(2)
                
                # Initialize default values
                land_use = "N/A"
                land_units = "N/A"
                land_depth = "N/A"
                zoning_code = "N/A"
                future_land_use = "N/A"
                
                # Extract land table data
                try:
                    # Find the first details card in the Land tab (contains the land table)
                    land_cards = driver.find_elements(By.CSS_SELECTOR, "#details-Land .card.details-card")
                    
                    if land_cards:
                        # First card should be the Land table
                        land_table = land_cards[0].find_element(By.CSS_SELECTOR, "table.putnam-table")
                        
                        # Find all data rows (skip header)
                        tbody = land_table.find_element(By.TAG_NAME, "tbody")
                        rows = tbody.find_elements(By.TAG_NAME, "tr")
                        
                        if rows:
                            # Get first data row
                            cells = rows[0].find_elements(By.TAG_NAME, "td")
                            
                            # Based on the HTML structure:
                            # Column 0: Line
                            # Column 1: Land Use
                            # Column 9: Units
                            # Column 3: Depth (Feet)
                            
                            if len(cells) > 1:
                                land_use = cells[1].text.strip()
                            if len(cells) > 9:
                                land_units = cells[9].text.strip()
                            if len(cells) > 3:
                                land_depth = cells[3].text.strip()
                            
                            print(f"Land Use: {land_use}")
                            print(f"Land Units: {land_units}")
                            print(f"Land Depth: {land_depth}")
                    
                except (NoSuchElementException, IndexError) as e:
                    print(f"Could not extract land table data: {e}")
                
                # Extract Zoning from second card
                try:
                    if len(land_cards) > 1:
                        zoning_table = land_cards[1].find_element(By.CSS_SELECTOR, "table.putnam-table")
                        zoning_tbody = zoning_table.find_element(By.TAG_NAME, "tbody")
                        zoning_rows = zoning_tbody.find_elements(By.TAG_NAME, "tr")
                        
                        if zoning_rows:
                            zoning_cells = zoning_rows[0].find_elements(By.TAG_NAME, "td")
                            # Column 1 is Code, Column 2 is Description
                            if len(zoning_cells) > 1:
                                zoning_code = zoning_cells[1].text.strip()
                                if len(zoning_cells) > 2:
                                    zoning_code += " - " + zoning_cells[2].text.strip()
                            
                            print(f"Zoning Code: {zoning_code}")
                
                except (NoSuchElementException, IndexError) as e:
                    print(f"Could not extract zoning data: {e}")
                
                # Extract Future Land Use from third card
                try:
                    if len(land_cards) > 2:
                        flum_table = land_cards[2].find_element(By.CSS_SELECTOR, "table.putnam-table")
                        flum_tbody = flum_table.find_element(By.TAG_NAME, "tbody")
                        flum_rows = flum_tbody.find_elements(By.TAG_NAME, "tr")
                        
                        if flum_rows:
                            flum_cells = flum_rows[0].find_elements(By.TAG_NAME, "td")
                            # Column 0 is Code, Column 1 is Description
                            if len(flum_cells) > 0:
                                future_land_use = flum_cells[0].text.strip()
                                if len(flum_cells) > 1:
                                    future_land_use += " - " + flum_cells[1].text.strip()
                            
                            print(f"Future Land Use: {future_land_use}")
                
                except (NoSuchElementException, IndexError) as e:
                    print(f"Could not extract FLUM data: {e}")
                
                land_details = {
                    'land_use': land_use,
                    'land_units': land_units,
                    'land_depth': land_depth,
                    'zoning_code': zoning_code,
                    'future_land_use': future_land_use
                }
                        
            except TimeoutException:
                print("Timeout waiting for Land tab")
                land_details = {
                    'land_use': 'N/A',
                    'land_units': 'N/A',
                    'land_depth': 'N/A',
                    'zoning_code': 'N/A',
                    'future_land_use': 'N/A'
                }
            except Exception as e:
                print(f"Error extracting land details: {e}")
                land_details = {
                    'land_use': 'N/A',
                    'land_units': 'N/A',
                    'land_depth': 'N/A',
                    'zoning_code': 'N/A',
                    'future_land_use': 'N/A'
                }

            # Extract Sales Details from Sales tab
            sales_details = {}
            try:
                # Click the Sales tab
                sales_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "tab-Sales"))
                )
                sales_tab.click()
                print("Clicked Sales tab")
                
                # Wait for tab content to be visible and loaded
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "details-Sales"))
                )
                
                # Wait for content to fully load
                time.sleep(2)
                
                # Initialize default value
                instruments = []
                
                # Extract all instruments from sales table
                try:
                    # Find the sales table
                    sales_table = driver.find_element(By.CSS_SELECTOR, "#details-Sales table.putnam-table")
                    
                    # Find tbody and get all rows
                    tbody = sales_table.find_element(By.TAG_NAME, "tbody")
                    rows = tbody.find_elements(By.TAG_NAME, "tr")
                    
                    # Extract instrument from each row
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        # Based on the HTML structure:
                        # Column 0: Book / Page
                        # Column 1: Instrument
                        # Column 2: Sale Date
                        # Column 3: QSCD
                        # Column 4: Price
                        
                        if len(cells) > 1:
                            instrument = cells[1].text.strip()
                            if instrument:  # Only add non-empty instruments
                                instruments.append(instrument)
                    
                    # Count occurrences of each instrument type
                    from collections import Counter
                    instrument_counts = Counter(instruments)

                    # Get unique instruments in order of first appearance
                    seen = set()
                    unique_instruments = []
                    for instrument in instruments:
                        if instrument not in seen:
                            unique_instruments.append(instrument)
                            seen.add(instrument)

                    # Format instruments with counts (only show count if > 1)
                    formatted_instruments = []
                    for instrument in unique_instruments:
                        count = instrument_counts[instrument]
                        if count > 1:
                            formatted_instruments.append(f"{instrument} ({count})")
                        else:
                            formatted_instruments.append(instrument)

                    # Join all instruments with a separator (e.g., semicolon)
                    instruments_str = "; ".join(formatted_instruments) if formatted_instruments else "N/A"
                    
                    print(f"Instruments: {instruments_str}")
                    print(f"Total sales records found: {len(instruments)}")
                
                except (NoSuchElementException, IndexError) as e:
                    print(f"Could not extract sales data: {e}")
                    instruments_str = "N/A"
                
                sales_details = {
                    'instruments': instruments_str,
                    'sales_count': len(instruments) if instruments else 0
                }
                        
            except TimeoutException:
                print("Timeout waiting for Sales tab")
                sales_details = {
                    'instruments': 'N/A',
                    'sales_count': 0
                }
            except Exception as e:
                print(f"Error extracting sales details: {e}")
                sales_details = {
                    'instruments': 'N/A',
                    'sales_count': 0
                }

             # Extract Improvement Details from Improvements tab
            improvements_list = []
            try:
                # Click the Improvements tab
                improvements_tab = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "tab-Improvements"))
                )
                improvements_tab.click()
                print("Clicked Improvements tab")
                
                # Wait for tab content to be visible and loaded
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "details-Improvements"))
                )
                
                # Wait for content to fully load
                time.sleep(2)
                
                # Check if there are any improvements
                try:
                    # Look for the accordion container
                    accordion = driver.find_element(By.ID, "improvements-accordion")
                    
                    # Find all improvement cards
                    improvement_cards = accordion.find_elements(By.CSS_SELECTOR, ".card.wrapper-card")
                    
                    print(f"Found {len(improvement_cards)} improvement(s)")
                    
                    for idx, card in enumerate(improvement_cards, 1):
                        try:
                            # Click to expand the improvement card
                            header = card.find_element(By.CSS_SELECTOR, ".card-header.accordion-header")
                            
                            # Check if already expanded
                            if "collapsed" in header.get_attribute("class"):
                                header.click()
                                time.sleep(1)  # Wait for expansion animation
                            
                            # Initialize default values
                            year_built = "N/A"
                            grading_type = "N/A"
                            base_sqft = "N/A"
                            
                            # Extract Actual Year Built
                            try:
                                year_label = card.find_element(By.XPATH, 
                                    ".//td[@class='row-heading' and contains(text(), 'Actual Year Built:')]")
                                year_built = year_label.find_element(By.XPATH, 
                                    "following-sibling::td").text.strip()
                                print(f"    Found year: {year_built}")
                            except NoSuchElementException:
                                print(f"    Year not found")
                                pass
                            
                            # Extract Grading Type
                            try:
                                grading_label = card.find_element(By.XPATH, 
                                    ".//td[@class='row-heading' and contains(text(), 'Grading Type:')]")
                                grading_type = grading_label.find_element(By.XPATH, 
                                    "following-sibling::td").text.strip()
                                print(f"    Found type: {grading_type}")
                            except NoSuchElementException:
                                print(f"    Type not found")
                                pass
                            
                            # Extract Base Square Feet from Area and Additions table
                            try:
                                # Find the "Area and Additions" card
                                area_card = card.find_element(By.XPATH, 
                                    ".//div[@class='card-header bg-primary text-white p-0 pl-2' and contains(text(), 'Area and Additions')]")
                                
                                # Get the table in this card
                                area_table = area_card.find_element(By.XPATH, 
                                    "following-sibling::div//table[@class='table table-sm table-striped putnam-table']")
                                
                                # Find the tbody and get rows
                                tbody = area_table.find_element(By.TAG_NAME, "tbody")
                                rows = tbody.find_elements(By.TAG_NAME, "tr")
                                
                                # Look for the "Base" row
                                for row in rows:
                                    cells = row.find_elements(By.TAG_NAME, "td")
                                    if len(cells) > 0 and cells[0].text.strip() == "Base":
                                        # Square Feet is in column 3 (0-indexed)
                                        if len(cells) > 3:
                                            base_sqft = cells[3].text.strip()
                                            print(f"    Found sqft: {base_sqft}")
                                        break
                            
                            except NoSuchElementException:
                                print(f"    Sqft not found")
                                pass
                            
                            # Format as single string: "Year GradingType, SqFt sqft"
                            improvement_str = f"{year_built} {grading_type}, {base_sqft} sqft"
                            
                            print(f"  Improvement {idx}: {improvement_str}")
                            
                            # Always append to the list
                            improvements_list.append(improvement_str)
                            
                        except Exception as e:
                            print(f"  Error extracting improvement {idx}: {e}")
                            # Still append an error entry so we maintain the count
                            improvements_list.append(f"Error extracting improvement {idx}")
                    
                    print(f"Total improvements extracted: {len(improvements_list)}")
                    
                except NoSuchElementException:
                    print("No improvements found or improvements accordion not present")
                        
            except TimeoutException:
                print("Timeout waiting for Improvements tab")
            except Exception as e:
                print(f"Error extracting improvements details: {e}")

            # Debug: print what we have
            print(f"DEBUG: improvements_list = {improvements_list}")

            # If no improvements found, ensure we have at least one N/A entry
            if not improvements_list:
                improvements_list = ["N/A"]
                print("No improvements extracted, setting to ['N/A']")

            # Add to property data list
            print(f"DEBUG: About to store improvements: {improvements_list}")

            def extract_extra_features(driver):
                """
                Scrapes Code, Description, and Sq. Footage from the Features tab under
                'Outbuildings and Extra Features' and returns a single compressed string.
                Format: "Code, Description, Sq.Ft; Code, Description, Sq.Ft; ..."
                
                Table structure:
                Column 0: Code
                Column 1: Description
                Column 2: Units
                Column 3: Length
                Column 4: Width
                Column 5: Sq. Footage
                Column 6: Rate
                Column 7: Amount
                """
                features_output = []

                try:
                    # Click Features tab
                    features_tab = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "tab-Features"))
                    )
                    features_tab.click()

                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "details-Features"))
                    )
                    time.sleep(2)

                    # Find all feature cards
                    cards = driver.find_elements(By.CSS_SELECTOR, "#details-Features .card.details-card")

                    target_table = None
                    for card in cards:
                        try:
                            header = card.find_element(By.CSS_SELECTOR, ".card-header")
                            # Check for either "Extra Features / Outbuildings" or "Outbuildings and Extra Features"
                            if "Outbuildings" in header.text or "Extra Features" in header.text:
                                target_table = card.find_element(By.CSS_SELECTOR, "table.putnam-table")
                                break
                        except NoSuchElementException:
                            continue

                    if not target_table:
                        return "None"

                    tbody = target_table.find_element(By.TAG_NAME, "tbody")
                    rows = tbody.find_elements(By.TAG_NAME, "tr")

                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        # Extract: Column 0 = Code, Column 1 = Description, Column 5 = Sq. Footage
                        if len(cells) >= 6:
                            code = cells[0].text.strip() if len(cells) > 0 else "N/A"
                            description = cells[1].text.strip() if len(cells) > 1 else "N/A"
                            sq_footage = cells[5].text.strip() if len(cells) > 5 else "N/A"
                            
                            if code and code != "N/A":
                                # Format: "Code, Description, Sq.Ft"
                                features_output.append(
                                    f"{code}, {description}, {sq_footage}"
                                )

                    # Join multiple features with semicolon separator
                    return "; ".join(features_output) if features_output else "None"

                except (TimeoutException, NoSuchElementException) as e:
                    print(f"Extra Features extraction failed: {e}")
                    return "None"
                
            extra_features = extract_extra_features(driver)
            print(f"Extra Features: {extra_features}")


            property_data.append({
                    'list_number': list_number,
                    'td_number': td_number,
                    'base_bid': base_bid,
                    'parcel_number': parcel_number,
                    'address': address,
                    'description': description,
                    'market_adjusted': marketval,
                    'total_acreage': acreage,
                    'property_use': prop_use,
                    'land_use': land_details.get('land_use', 'N/A'),
                    'land_units': land_details.get('land_units', 'N/A'),
                    'land_depth': land_details.get('land_depth', 'N/A'),
                    'zoning_code': land_details.get('zoning_code', 'N/A'),
                    'future_land_use': land_details.get('future_land_use', 'N/A'),
                    'instruments': sales_details.get('instruments', 'N/A'),
                    'sales_count': sales_details.get('sales_count', 0),
                    'extra_features': extra_features,
                    'improvements': improvements_list.copy(),
                })

            print(f"DEBUG: Stored property with {len(improvements_list)} improvements")

        except Exception as e:
            print(f"Error extracting data: {e}")
            property_data.append({
                'list_number': 'Error',
                'td_number': 'Error',
                'base_bid': 'Error',
                'parcel_number': 'Error',
                'address': 'Error',
                'description': 'Error',
                'market_adjusted': 'Error',
                'total_acreage': 'Error',
                'property_use': 'Error',
                'land_use': 'Error',
                'land_units': 'Error',
                'land_depth': 'Error',
                'zoning_code': 'Error',
                'future_land_use': 'Error',
                'instruments': 'Error',
                'sales_count': 0,
                'extra_features' : 'Error',
                'url': url
            })
    
    print("\n" + "="*60)
    print("All properties processed!")
    
    # Save data to CSV file
    if property_data:
        with open("auction_data.csv", 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['list_number', 'base_bid', 'td_number', 'address', 'description', 'property_use', 
                        'total_acreage', 'market_adjusted', 'land_use', 'land_units', 'land_depth', 
                        'zoning_code', 'future_land_use', 'instruments', 'sales_count', 'extra_features',
                        'improvements',]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for prop in property_data:
                # Flatten improvements data for CSV
                row = {k: v for k, v in prop.items() if k != 'improvements'}
                
                # Combine all improvements into a single string separated by commas
                improvements = prop.get('improvements', [])
                
                # Debug
                print(f"Writing property {prop.get('parcel_number', 'unknown')}: {len(improvements)} improvements")
                for i, imp in enumerate(improvements):
                    print(f"  - Improvement {i+1}: {imp}")
                
                # Join all improvements with comma separator
                row['improvements'] = ', '.join(improvements) if improvements else 'N/A'
                
                print(f"  CSV row improvements: {row['improvements']}")
                
                writer.writerow(row)

        print(f"\nSaved {len(property_data)} properties to auction_data.csv")
    
    # Print summary
    print("\n=== SUMMARY ===")
    for i, prop in enumerate(property_data, 1):
        print(f"\nProperty {i}:")
        print(f"  List Number: {prop['list_number']}")
        print(f"  T.D. Number: {prop['td_number']}")
        print(f"  Base Bid: {prop['base_bid']}")
        print(f"  Parcel: {prop['parcel_number']}")
        print(f"  Address: {prop['address']}")
        print(f"  Description: {prop['description']}")
        print(f"  Market Adjusted: {prop['market_adjusted']}")
        print(f"  Total Acreage: {prop['total_acreage']}")
        print(f"  Property Use: {prop['property_use']}")
        print(f"  Land Use: {prop['land_use']}")
        print(f"  Land Units: {prop['land_units']}")
        print(f"  Land Depth: {prop['land_depth']}")
        print(f"  Zoning Code: {prop['zoning_code']}")
        print(f"  Future Land Use: {prop['future_land_use']}")
        print(f"  Instruments: {prop['instruments']}")
        print(f"  Sales Count: {prop['sales_count']}")
        
        # Print improvements
        improvements = prop.get('improvements', [])
        for idx, imp in enumerate(improvements, 1):
            print(f"  Improvement {idx}: {imp}")



finally:
    driver.quit()

# **Key changes:**

# 1. **Added `datetime` import** - To parse and validate date formats

# 2. **Updated `select_auction_date()` function**:
#    - Parses dates from the dropdown (originally in MM/DD/YYYY format)
#    - Converts them to dd/MM/YYYY format for display
#    - Creates a `date_lookup` dictionary mapping dd/MM/YYYY dates to dropdown values
#    - Sorts dates chronologically (most recent first)
#    - Displays all available dates in dd/MM/YYYY format

# 3. **User input validation**:
#    - Accepts dates in dd/MM/YYYY format (e.g., "07/01/2026" for January 7, 2026)
#    - Validates the format using `datetime.strptime()`
#    - Checks if the entered date exists in the available auctions
#    - Provides helpful error messages for invalid formats or unavailable dates
#    - Allows user to type 'q' to quit

# **Example interaction:**
# ```
# ============================================================
# AVAILABLE AUCTION DATES
# ============================================================
#   11/02/2026
#   21/01/2026
#   07/01/2026
#   10/12/2025
#   ...
# ============================================================

# Enter auction date (dd/MM/YYYY format) or 'q' to quit: 07/01/2026

# Selected: 07/01/2026