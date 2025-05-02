import time
import csv
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_driver():
    """Set up and return a configured Chrome WebDriver."""
    try:
        options = webdriver.ChromeOptions()
        # Uncomment the next line to run in headless mode if needed
        # options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Failed to set up WebDriver: {e}")
        raise

def scrape_universities(url="https://www.coursicle.com/schools/", output_file="universities.csv"):
    """Scrape university information from the Coursicle schools page."""
    logger.info(f"Starting university scraper for URL: {url}")
    
    driver = None
    try:
        driver = setup_driver()
        logger.info("WebDriver set up successfully")
        
        # Navigate to the URL
        driver.get(url)
        logger.info(f"Navigated to {url}")
        
        # Wait for the page to load - wait for the university search results container
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "universalSchoolSearchResultsContainer"))
        )
        logger.info("School results container loaded")
        
        # Initialize our universities list and set to track subdomains to avoid duplicates
        universities = []
        processed_subdomains = set()
        
        # Set up scroll handling for dynamic loading
        last_height = driver.execute_script("return document.getElementById('universalSchoolSearchResultsContainer').scrollHeight")
        scroll_pauses = 0
        max_scroll_pauses = 30  # Limit scrolling attempts
        
        while scroll_pauses < max_scroll_pauses:
            # Get university elements
            university_elements = driver.find_elements(By.CSS_SELECTOR, ".universalSchoolSearchResult:not(#searchResultTemplate)")
            
            # Extract data from each university element
            for element in university_elements:
                try:
                    # Get the subdomain (unique identifier for the university)
                    subdomain = element.get_attribute("data-school-subdomain")
                    
                    # Skip if we've already processed this subdomain or if it's empty
                    if not subdomain or subdomain in processed_subdomains:
                        continue
                    
                    # Extract university name
                    name_element = element.find_element(By.CSS_SELECTOR, ".universalSchoolSearchResultSchoolName")
                    university_name = name_element.text.strip()
                    
                    # Check if name is empty - the page has some empty elements
                    if not university_name:
                        continue
                    
                    # Extract location if available
                    location = ""
                    try:
                        location_element = element.find_element(By.CSS_SELECTOR, ".universalSchoolSearchResultSchoolLocation")
                        location = location_element.text.strip()
                    except NoSuchElementException:
                        pass  # Location might not be available for all universities
                    
                    # Extract country flag if available
                    country = ""
                    try:
                        country_element = element.find_element(By.CSS_SELECTOR, ".universalSchoolSearchResultCountryFlag")
                        country = country_element.text.strip()
                    except NoSuchElementException:
                        pass  # Country flag might not be available for all universities
                    
                    # Construct the university URL
                    university_url = f"https://www.coursicle.com/{subdomain}/"
                    
                    # Add university data to our list
                    universities.append({
                        "name": university_name,
                        "location": location,
                        "country": country,
                        "subdomain": subdomain,
                        "url": university_url
                    })
                    
                    # Mark this subdomain as processed
                    processed_subdomains.add(subdomain)
                    
                except Exception as e:
                    logger.warning(f"Error extracting university data: {e}")
            
            # Log progress
            logger.info(f"Processed {len(universities)} universities so far")
            
            # Scroll down to load more universities
            university_container = driver.find_element(By.ID, "universalSchoolSearchResultsContainer")
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", university_container)
            
            # Wait for new content to load
            time.sleep(2)
            
            # Check if we've reached the end of the scrollable content
            new_height = driver.execute_script("return document.getElementById('universalSchoolSearchResultsContainer').scrollHeight")
            if new_height == last_height:
                scroll_pauses += 1
                logger.info(f"No new content loaded, pause count: {scroll_pauses}")
                if scroll_pauses >= 3:  # If no new content after 3 attempts, break
                    logger.info("Reached the end of scrollable content")
                    break
            else:
                scroll_pauses = 0  # Reset counter if new content was loaded
                last_height = new_height
                
            # Take a short break to avoid overwhelming the server
            time.sleep(1)
        
        # Check if we found any universities
        if not universities:
            logger.warning("No universities found, saving debug information")
            driver.save_screenshot("university_scraping_debug.png")
            with open("university_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        
        logger.info(f"Successfully extracted data for {len(universities)} universities")
        
        # Save to CSV
        save_to_csv(universities, output_file)
        logger.info(f"Saved university data to {output_file}")
        
        return universities
    
    except Exception as e:
        logger.error(f"Error during university scraping: {e}")
        if driver:
            driver.save_screenshot("university_scraping_error.png")
            with open("university_scraping_error.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        return []
    
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

def save_to_csv(universities, filename):
    """Save university data to a CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["name", "location", "country", "subdomain", "url"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for university in universities:
                writer.writerow(university)
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")

def test_university_scraping():
    """Test the university scraping function with a limit."""
    print("Starting university scraper...")
    universities = scrape_universities()
    
    if not universities:
        print("\nNo universities were scraped or an error occurred during scraping.")
        print("Please check the console output for errors, ensure website structure hasn't changed,")
        print("and verify your internet connection and Selenium setup.")
    else:
        print(f"\nSuccessfully scraped {len(universities)} universities! Data saved to universities.csv")

if __name__ == "__main__":
    test_university_scraping()