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

def scrape_departments(university_subdomain="mit", output_file="departments.csv"):
    """Scrape department information from a university's courses page."""
    url = f"https://www.coursicle.com/{university_subdomain}/courses/"
    logger.info(f"Starting department scraper for URL: {url}")
    
    driver = None
    try:
        driver = setup_driver()
        logger.info("WebDriver set up successfully")
        
        # Navigate to the URL
        driver.get(url)
        logger.info(f"Navigated to {url}")
        
        # Wait for the page to load - wait for the tile container
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "tileContainer"))
        )
        logger.info("Tile container loaded")
        
        # Initialize our departments list
        departments = []
        
        # Look for more button if it exists
        more_button = None
        try:
            more_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "moreTile"))
            )
            logger.info("Found 'More' button, will click to show all departments")
            
            # Click the more button until all departments are loaded
            while more_button.is_displayed():
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", more_button)
                    logger.info("Clicked 'More' button")
                    time.sleep(2)  # Give time for new tiles to load
                except Exception as e:
                    logger.warning(f"Error clicking 'More' button: {e}")
                    break
        except (TimeoutException, NoSuchElementException):
            logger.info("No 'More' button found or it's not needed")
        
        # Get all department elements
        department_elements = driver.find_elements(By.CSS_SELECTOR, "a.tileElement:not(#moreTile)")
        logger.info(f"Found {len(department_elements)} department tiles")
        
        # Extract data from each department element
        for element in department_elements:
            try:
                # Get the department code/name
                name_element = element.find_element(By.CLASS_NAME, "tileElementText")
                department_name = name_element.text.strip()
                
                # Get the department URL
                department_url = element.get_attribute("href")
                
                # Add to departments list (removed background_color)
                departments.append({
                    "university": university_subdomain,
                    "department_code": department_name,
                    "url": department_url
                })
                
                logger.info(f"Processed department: {department_name}")
                
            except Exception as e:
                logger.warning(f"Error extracting department data: {e}")
        
        # Check if we found any departments
        if not departments:
            logger.warning("No departments found, saving debug information")
            driver.save_screenshot("department_scraping_debug.png")
            with open("department_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        
        logger.info(f"Successfully extracted data for {len(departments)} departments")
        
        # Save to CSV
        save_to_csv(departments, output_file)
        logger.info(f"Saved department data to {output_file}")
        
        return departments
    
    except Exception as e:
        logger.error(f"Error during department scraping: {e}")
        if driver:
            driver.save_screenshot("department_scraping_error.png")
            with open("department_scraping_error.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        return []
    
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

def save_to_csv(departments, filename):
    """Save department data to a CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["university", "department_code", "url"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for department in departments:
                writer.writerow(department)
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")

def scrape_multiple_universities_departments(university_list, base_output_folder=""):
    """Scrape departments for multiple universities."""
    results = {}
    
    for university in university_list:
        subdomain = university.get('subdomain')
        if not subdomain:
            logger.warning(f"Missing subdomain for university: {university}")
            continue
            
        output_file = f"{base_output_folder}{subdomain}_departments.csv" if base_output_folder else f"{subdomain}_departments.csv"
        
        logger.info(f"Scraping departments for {subdomain}")
        departments = scrape_departments(subdomain, output_file)
        
        if departments:
            results[subdomain] = departments
            logger.info(f"Successfully scraped {len(departments)} departments for {subdomain}")
        else:
            logger.warning(f"Failed to scrape departments for {subdomain}")
    
    return results

def test_department_scraping():
    """Test the department scraping function."""
    print("Starting department scraper test...")
    
    # Test with MIT (Massachusetts Institute of Technology)
    university_subdomain = "mit"
    output_file = "mit_departments.csv"
    
    departments = scrape_departments(university_subdomain, output_file)
    
    if not departments:
        print("\nNo departments were scraped or an error occurred during scraping.")
        print("Please check the console output for errors, ensure website structure hasn't changed,")
        print("and verify your internet connection and Selenium setup.")
    else:
        print(f"\nSuccessfully scraped {len(departments)} departments from {university_subdomain}!")
        print(f"Data saved to {output_file}")

if __name__ == "__main__":
    test_department_scraping()