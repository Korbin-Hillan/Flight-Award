import csv
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def extract_flight_data(driver):
    """Extract flight data from the current United.com results page"""
    try:
        print("\n🔍 Detecting flight search parameters...")

        # Extract origin, destination, and date from URL or page
        current_url = driver.current_url

        # Parse URL parameters
        origin = None
        destination = None
        date = None

        # Extract from URL (format: f=ORIGIN, t=DESTINATION, d=DATE)
        if 'f=' in current_url:
            origin = re.search(r'f=([A-Z]{3})', current_url)
            origin = origin.group(1) if origin else 'UNKNOWN'

        if 't=' in current_url:
            destination = re.search(r't=([A-Z]{3})', current_url)
            destination = destination.group(1) if destination else 'UNKNOWN'

        if 'd=' in current_url:
            date = re.search(r'd=(\d{4}-\d{2}-\d{2})', current_url)
            date = date.group(1) if date else 'UNKNOWN'

        print(f"📍 Route: {origin} → {destination}")
        print(f"📅 Date: {date}")

        # Wait a bit for all flights to load
        time.sleep(3)

        flights_found = 0
        min_miles = None

        # Check for error message from United
        error_messages = driver.find_elements(By.XPATH, "//*[contains(text(), 'unable to complete your request') or contains(text(), 'Please try again later')]")
        if error_messages:
            print("❌ ERROR: United.com blocked the request")
            return {
                'origin': origin,
                'destination': destination,
                'date': date,
                'flights_found': 'BLOCKED',
                'min_miles': 'BLOCKED',
                'scraped_at': datetime.now().isoformat()
            }

        # Look for flight cards/results
        print("🔎 Scanning for flight results...")
        flight_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='flight-result'], [class*='FlightResult'], [data-qa*='flight']")

        if not flight_elements:
            flight_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='flightCard'], [class*='flight-card']")

        if not flight_elements:
            flight_elements = driver.find_elements(By.CSS_SELECTOR, "li[class*='flight'], div[class*='flight']")

        flights_found = len(flight_elements)
        print(f"✈️  Found {flights_found} flight elements")

        # Extract miles pricing
        miles_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='miles'], [class*='award-price'], [data-qa*='price']")

        miles_prices = []
        for elem in miles_elements:
            text = elem.text.strip()
            # Extract numeric values from text like "12,500 miles" or "12500"
            numbers = ''.join(filter(lambda x: x.isdigit(), text))
            if numbers:
                miles_prices.append(int(numbers))

        if miles_prices:
            min_miles = min(miles_prices)
            print(f"💰 Minimum miles found: {min_miles:,}")
        else:
            print("⚠️  No mile pricing found")

        # Check for "no flights" messages
        no_flights_indicators = driver.find_elements(By.XPATH, "//*[contains(text(), 'No flights') or contains(text(), 'no flights') or contains(text(), 'not available')]")
        if no_flights_indicators and flights_found == 0:
            flights_found = 0
            min_miles = None
            print("ℹ️  No flights available for this route/date")

        flight_data = {
            'origin': origin,
            'destination': destination,
            'date': date,
            'flights_found': flights_found,
            'min_miles': min_miles if min_miles else 'N/A',
            'scraped_at': datetime.now().isoformat()
        }

        return flight_data

    except Exception as e:
        print(f"❌ Error extracting flight data: {e}")
        return None

def save_to_csv(flight_data, filename='united_awards.csv'):
    """Save flight data to CSV file"""
    try:
        # Check if file exists to determine if we need to write headers
        try:
            with open(filename, 'r') as f:
                write_header = False
        except FileNotFoundError:
            write_header = True

        # Append to CSV
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['origin', 'destination', 'date', 'flights_found', 'min_miles', 'scraped_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if write_header:
                writer.writeheader()

            writer.writerow(flight_data)

        print(f"✅ Data saved to {filename}")
        return True

    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")
        return False

def setup_driver():
    """Configure Chrome to avoid bot detection"""
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    driver = uc.Chrome(options=options, version_main=None)
    return driver

def wait_for_search_results(driver, timeout=60):
    """Wait for user to perform a search and results to load"""
    print("\n⏳ Waiting for you to search for flights on United.com...")
    print("   (The script will auto-detect when results appear)")

    start_time = time.time()
    last_url = driver.current_url

    while time.time() - start_time < timeout:
        current_url = driver.current_url

        # Check if URL changed to a flight search results page
        if 'choose-flights' in current_url or 'fsr' in current_url:
            print("\n✅ Flight results page detected!")
            # Wait a bit more for results to fully load
            time.sleep(5)
            return True

        # Check if URL changed at all (user is navigating)
        if current_url != last_url:
            last_url = current_url
            print(f"   Detected navigation... still waiting for results page")

        time.sleep(1)

    return False

def main():
    """Main function"""
    print("="*70)
    print("     UNITED AWARD FLIGHT AUTO-SCRAPER")
    print("="*70)
    print("\n📋 How this works:")
    print("   1. Chrome will open to United.com")
    print("   2. Log in to your United MileagePlus account")
    print("   3. Use United's search form to find award flights")
    print("   4. Click 'Find flights'")
    print("   5. The script will AUTO-DETECT results and save them to CSV")
    print("   6. You can search again for more routes!")
    print("\n" + "="*70 + "\n")

    input("Press ENTER to start...")

    # Initialize Chrome
    print("\n🚀 Opening Chrome...")
    driver = setup_driver()

    try:
        # Navigate to United homepage
        print("🌐 Loading United.com...")
        driver.get("https://www.united.com")

        print("\n" + "="*70)
        print("✋ PLEASE LOG IN TO YOUR UNITED ACCOUNT NOW")
        print("="*70)
        input("\nPress ENTER after you've logged in...")

        # Continuous monitoring loop
        while True:
            print("\n" + "="*70)
            print("🔍 READY TO SCRAPE")
            print("="*70)
            print("✈️  Go ahead and search for flights using United's search form")
            print("⌨️  Or press Ctrl+C to exit")
            print("="*70 + "\n")

            # Wait for user to search
            if wait_for_search_results(driver, timeout=300):  # 5 minute timeout
                # Extract flight data
                flight_data = extract_flight_data(driver)

                if flight_data:
                    # Display results
                    print("\n" + "="*70)
                    print("📊 SCRAPED DATA:")
                    print("="*70)
                    for key, value in flight_data.items():
                        print(f"   {key}: {value}")
                    print("="*70)

                    # Save to CSV
                    save_to_csv(flight_data)

                    print("\n✨ Ready for next search!")
                    print("   You can:")
                    print("   - Go back and search for another route")
                    print("   - Or press Ctrl+C to exit\n")
                else:
                    print("⚠️  Could not extract flight data. Try searching again.")
            else:
                print("\n⏱️  Timeout waiting for search. Please try again.")

    except KeyboardInterrupt:
        print("\n\n👋 Exiting... Chrome will close.")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

    finally:
        driver.quit()
        print("✅ Chrome closed. Goodbye!")

if __name__ == "__main__":
    main()
