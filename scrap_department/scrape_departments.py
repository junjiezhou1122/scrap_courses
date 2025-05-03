import time
import csv
import logging
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_random_user_agent():
    """Get a random user agent string to avoid detection."""
    try:
        ua = UserAgent()
        return ua.random
    except Exception as e:
        logger.warning(f"Error getting random user agent: {e}")
        # Fallback user agents
        fallback_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        ]
        return random.choice(fallback_agents)

def setup_driver(proxy_string=None):
    """Set up and return a configured Chrome WebDriver with anti-bot detection measures."""
    try:
        options = webdriver.ChromeOptions()
        
        # Add a random user agent
        user_agent = get_random_user_agent()
        options.add_argument(f'user-agent={user_agent}')
        
        # Add anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Standard options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--headless") # Optional: run headless
        
        # Add proxy if provided
        if proxy_string:
            options.add_argument(f'--proxy-server={proxy_string}')
            logger.info(f"Using proxy for Selenium: {proxy_string}")
        
        driver = webdriver.Chrome(options=options)
        
        # Mask WebDriver to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set random window size to avoid fingerprinting
        window_width = random.randint(1050, 1200)
        window_height = random.randint(800, 950)
        driver.set_window_size(window_width, window_height)
        
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Failed to set up WebDriver: {e}")
        raise

def add_human_behavior(driver):
    """Add random scrolls and mouse movements to mimic human behavior."""
    try:
        # Scroll down slowly, like a human would
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        scroll_points = random.randint(3, 7)  # Random number of scroll points
        
        for i in range(scroll_points):
            point = (i + 1) * (total_height // (scroll_points + 1))
            driver.execute_script(f"window.scrollTo(0, {point});")
            time.sleep(random.uniform(0.5, 1.5))  # Random delay between scrolls
        
        # Scroll back up randomly
        if random.random() > 0.5:  # 50% chance to scroll back up
            up_point = random.randint(0, total_height // 2)
            driver.execute_script(f"window.scrollTo(0, {up_point});")
            time.sleep(random.uniform(0.3, 0.8))
        
        # Random final scroll position
        final_point = random.randint(viewport_height, total_height - viewport_height)
        driver.execute_script(f"window.scrollTo(0, {final_point});")
        
    except Exception as e:
        logger.warning(f"Error during human behavior simulation: {e}")

def scrape_departments(university_subdomain="mit", output_file="departments.csv", progress_tracker=None, human_error_tracker=None, proxy_string=None):
    """Scrape department information from a university's courses page."""
    url = f"https://www.coursicle.com/{university_subdomain}/courses/"
    logger.info(f"Starting department scraper for URL: {url}")
    
    # Check if university is in human error tracker
    if human_error_tracker and human_error_tracker.is_university_in_error(university_subdomain):
        logger.warning(f"University {university_subdomain} previously triggered bot detection ('you don't smell like a human')")
        logger.warning(f"Skipping this university for now - it's in the human error tracker")
        print(f"⚠️ Skipping {university_subdomain} because it previously triggered bot detection.")
        print(f"   This university will be recorded for later scraping.")
        return []
    
    # Check if we've already processed this university in our progress tracker
    if progress_tracker and progress_tracker.is_university_processed(university_subdomain):
        logger.info(f"University {university_subdomain} already processed according to progress tracker")
        
        # Check if output file exists
        import os
        if os.path.exists(output_file):
            logger.info(f"Loading existing departments from {output_file}")
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    departments = list(reader)
                return departments
            except Exception as e:
                logger.error(f"Error loading existing departments: {e}")
                # If we can't load the file, continue with scraping
    
    driver = None
    try:
        driver = setup_driver(proxy_string=proxy_string)
        logger.info("WebDriver set up successfully")
        
        # Visit the homepage first to establish cookies
        home_url = f"https://www.coursicle.com/{university_subdomain}/"
        driver.get(home_url)
        logger.info(f"Visited homepage first: {home_url}")
        time.sleep(random.uniform(3, 5))  # Random wait like a human
        
        # Now navigate to the courses URL
        driver.get(url)
        logger.info(f"Navigated to {url}")
        
        # Add random waits and movements to appear more human-like
        time.sleep(random.uniform(2, 4))
        add_human_behavior(driver)
        
        # Wait for the page to load - wait for the tile container
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "tileContainer"))
            )
            logger.info("Tile container loaded")
        except TimeoutException:
            logger.warning("Timeout waiting for tile container, checking for bot detection")
            
            # Check for common bot detection elements
            if "you don't smell like a human" in driver.page_source.lower():
                logger.error("Bot detection triggered: 'You don't smell like a human' message found")
                
                # Save a screenshot and HTML for debugging
                error_dir = "error_screenshots"
                os.makedirs(error_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_file = os.path.join(error_dir, f"bot_detection_{university_subdomain}_{timestamp}.png")
                html_file = os.path.join(error_dir, f"bot_detection_{university_subdomain}_{timestamp}.html")
                
                driver.save_screenshot(screenshot_file)
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                logger.warning(f"Saved bot detection screenshot to {screenshot_file}")
                logger.warning(f"Saved bot detection HTML to {html_file}")
                
                # Add to human error tracker
                if human_error_tracker:
                    human_error_tracker.add_university(university_subdomain)
                    logger.info(f"Added {university_subdomain} to human error tracker")
                
                # Return empty list to skip this university
                print(f"⚠️ Bot detection ('you don't smell like a human') triggered for {university_subdomain}")
                print(f"   This university will be skipped and recorded for later scraping.")
                return []
                
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
                    # Scroll to the button with human-like behavior
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", more_button)
                    time.sleep(random.uniform(1, 2))  # Random pause like a human
                    
                    # Click with JavaScript to avoid WebDriver detection
                    driver.execute_script("arguments[0].click();", more_button)
                    logger.info("Clicked 'More' button")
                    
                    # Random wait time between clicks
                    time.sleep(random.uniform(1.5, 3.5))
                except Exception as e:
                    logger.warning(f"Error clicking 'More' button: {e}")
                    break
        except (TimeoutException, NoSuchElementException):
            logger.info("No 'More' button found or it's not needed")
        
        # Get all department elements
        department_elements = driver.find_elements(By.CSS_SELECTOR, "a.tileElement:not(#moreTile)")
        logger.info(f"Found {len(department_elements)} department tiles")
        
        # Add another random delay and scroll
        time.sleep(random.uniform(1, 2))
        add_human_behavior(driver)
        
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
                
                # Mark as processed in the progress tracker
                if progress_tracker:
                    progress_tracker.mark_department_processed(university_subdomain, department_name)
                
            except Exception as e:
                logger.warning(f"Error extracting department data: {e}")
        
        # Check if we found any departments
        if not departments:
            logger.warning("No departments found, saving debug information")
            error_dir = "error_screenshots"
            os.makedirs(error_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(os.path.join(error_dir, f"no_departments_{university_subdomain}_{timestamp}.png"))
            with open(os.path.join(error_dir, f"no_departments_{university_subdomain}_{timestamp}.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        
        logger.info(f"Successfully extracted data for {len(departments)} departments")
        
        # Save to CSV
        save_to_csv(departments, output_file)
        logger.info(f"Saved department data to {output_file}")
        
        # Mark university as fully processed
        if progress_tracker:
            progress_tracker.mark_university_processed(university_subdomain)
        
        return departments
    
    except Exception as e:
        logger.error(f"Error during department scraping: {e}")
        if driver:
            error_dir = "error_screenshots"
            os.makedirs(error_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(os.path.join(error_dir, f"error_{university_subdomain}_{timestamp}.png"))
            with open(os.path.join(error_dir, f"error_{university_subdomain}_{timestamp}.html"), "w", encoding="utf-8") as f:
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