import csv
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

# Top 50 major US cities by airport code
AIRPORTS = [
    'ATL', 'LAX', 'ORD', 'DFW', 'DEN', 'JFK', 'SFO', 'SEA', 'LAS', 'MCO',
    'EWR', 'CLT', 'PHX', 'IAH', 'MIA', 'BOS', 'MSP', 'FLL', 'DTW', 'PHL',
    'LGA', 'BWI', 'SLC', 'SAN', 'DCA', 'MDW', 'TPA', 'PDX', 'HNL', 'STL',
    'BNA', 'AUS', 'OAK', 'SJC', 'MCI', 'RSW', 'SAT', 'SMF', 'DAL', 'SNA',
    'PIT', 'RDU', 'CVG', 'CMH', 'IND', 'CLE', 'JAX', 'OGG', 'BDL', 'MKE'
]

def generate_routes():
    """Generate all direct route combinations"""
    routes = []
    for origin in AIRPORTS:
        for destination in AIRPORTS:
            if origin != destination:
                routes.append((origin, destination))
    return routes

def scrape_united_awards(origin, destination, date, driver, debug=False):
    """Scrape United award flights for a specific route and date"""
    try:
        # Format date as YYYY-MM-DD
        date_str = date.strftime('%Y-%m-%d')

        # United award search URL (based on actual United URL format)
        url = f"https://www.united.com/en/us/fsr/choose-flights?tt=1&st=bestmatches&d={date_str}&clm=7&taxng=1&f={origin}&px=1&newHP=True&fareWheel=true&sc=7&at=0&t={destination}"

        driver.get(url)

        if debug:
            print(f"  URL: {url}")

        # Wait for page to load - give it more time for flights to appear
        wait = WebDriverWait(driver, 20)

        # Random delay to appear more human-like
        time.sleep(random.uniform(5, 10))  # Random wait between 5-10 seconds

        flights_found = 0
        min_miles = None
        flight_details = []

        # Check for error message from United
        error_messages = driver.find_elements(By.XPATH, "//*[contains(text(), 'unable to complete your request') or contains(text(), 'Please try again later')]")
        if error_messages:
            print(f"  ERROR: United.com blocked the request")
            return {
                'origin': origin,
                'destination': destination,
                'date': date_str,
                'flights_found': 'BLOCKED',
                'min_miles': 'BLOCKED',
                'scraped_at': datetime.now().isoformat()
            }

        try:
            if debug:
                # Save screenshot for debugging
                screenshot_path = f"debug_{origin}_{destination}_{date_str}.png"
                driver.save_screenshot(screenshot_path)
                print(f"  Screenshot saved: {screenshot_path}")

                # Print page title
                print(f"  Page title: {driver.title}")

            # Look for flight cards/results (adjust selectors based on United's actual page structure)
            flight_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='flight-result'], [class*='FlightResult'], [data-qa*='flight']")

            if not flight_elements:
                # Try alternative selectors
                flight_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='flightCard'], [class*='flight-card']")

            if not flight_elements:
                # Try even more generic selectors
                flight_elements = driver.find_elements(By.CSS_SELECTOR, "li[class*='flight'], div[class*='flight']")

            flights_found = len(flight_elements)

            if debug:
                print(f"  Found {flights_found} flight elements")
                if flight_elements:
                    print(f"  First flight element class: {flight_elements[0].get_attribute('class')}")

            # Extract miles pricing from each flight
            miles_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='miles'], [class*='award-price'], [data-qa*='price']")

            if debug:
                print(f"  Found {len(miles_elements)} miles elements")

            miles_prices = []
            for elem in miles_elements:
                text = elem.text.strip()
                # Extract numeric values from text like "12,500 miles" or "12500"
                numbers = ''.join(filter(lambda x: x.isdigit(), text))
                if numbers:
                    miles_prices.append(int(numbers))

            if miles_prices:
                min_miles = min(miles_prices)

            if debug and miles_prices:
                print(f"  Miles prices found: {miles_prices}")
                print(f"  Min miles: {min_miles}")

            # Check for "no flights" messages
            no_flights_indicators = driver.find_elements(By.XPATH, "//*[contains(text(), 'No flights') or contains(text(), 'no flights') or contains(text(), 'not available')]")
            if no_flights_indicators and flights_found == 0:
                flights_found = 0
                min_miles = None

        except Exception as e:
            print(f"  Warning: Could not extract flight details: {e}")
            # Continue with default values

        flights_data = {
            'origin': origin,
            'destination': destination,
            'date': date_str,
            'flights_found': flights_found,
            'min_miles': min_miles if min_miles else 'N/A',
            'scraped_at': datetime.now().isoformat()
        }

        return flights_data

    except Exception as e:
        print(f"Error scraping {origin}->{destination} on {date_str}: {e}")
        return {
            'origin': origin,
            'destination': destination,
            'date': date_str,
            'flights_found': 'ERROR',
            'min_miles': 'ERROR',
            'scraped_at': datetime.now().isoformat()
        }

def setup_driver():
    """Configure Chrome to avoid bot detection using undetected-chromedriver"""
    options = uc.ChromeOptions()

    # Chrome options
    options.add_argument('--start-maximized')

    # Use undetected-chromedriver which bypasses most bot detection
    driver = uc.Chrome(options=options, version_main=None)

    return driver

def main(test_mode=False, debug=False, manual_login=True):
    """Main scraping function"""
    routes = generate_routes()

    # Test mode: only scrape first route with first 2 dates
    if test_mode:
        routes = routes[:1]
        print("TEST MODE: Only scraping first route")

    print(f"Total routes to scrape: {len(routes)}")

    # Calculate dates for the next 365 days
    start_date = datetime.now()
    if test_mode:
        dates = [start_date + timedelta(days=i) for i in range(2)]
    else:
        dates = [start_date + timedelta(days=i) for i in range(365)]

    # Prepare CSV file
    output_file = 'united_awards.csv'
    fieldnames = ['origin', 'destination', 'date', 'flights_found', 'min_miles', 'scraped_at']

    # Initialize Chrome driver once and reuse it
    print("Initializing Chrome driver...")
    driver = setup_driver()

    # Navigate to United homepage first to establish session
    if manual_login:
        print("\n" + "="*60)
        print("MANUAL LOGIN REQUIRED")
        print("="*60)
        print("1. Opening United.com...")
        print("2. Please log in to your United account in the browser")
        print("3. After logging in, press ENTER to continue scraping")
        print("="*60 + "\n")

        driver.get("https://www.united.com")
        time.sleep(3)

        # Wait for user to log in
        input("Press ENTER after you've logged in...")
        print("\nStarting scraping process...\n")

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Scrape each route for each date
            total_searches = len(routes) * len(dates)
            current_search = 0

            for origin, destination in routes:
                for date in dates:
                    current_search += 1
                    print(f"[{current_search}/{total_searches}] Scraping {origin}->{destination} on {date.strftime('%Y-%m-%d')}")

                    flight_data = scrape_united_awards(origin, destination, date, driver, debug=debug)

                    if flight_data:
                        writer.writerow(flight_data)
                        csvfile.flush()  # Write to disk immediately

                    # Rate limiting - random wait between requests to avoid being blocked
                    wait_time = random.uniform(3, 7)
                    if debug:
                        print(f"  Waiting {wait_time:.1f}s before next request...")
                    time.sleep(wait_time)

        print(f"Scraping complete! Data saved to {output_file}")

    finally:
        driver.quit()
        print("Chrome driver closed")

if __name__ == "__main__":
    import sys

    # Check for command line arguments
    test_mode = '--test' in sys.argv
    debug = '--debug' in sys.argv
    manual_login = '--no-login' not in sys.argv  # Default to True unless --no-login is specified

    if test_mode:
        print("Running in TEST MODE")
    if debug:
        print("Running in DEBUG MODE")
    if not manual_login:
        print("Skipping manual login step")

    main(test_mode=test_mode, debug=debug, manual_login=manual_login)
