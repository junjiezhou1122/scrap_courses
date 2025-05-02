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

def scrape_courses(url, output_file="stanford_cs_courses.csv", university_name="Stanford"):
    """Scrape course information from the given URL."""
    logger.info(f"Starting scraper for URL: {url}")
    
    driver = None
    try:
        driver = setup_driver()
        logger.info("WebDriver set up successfully")
        
        # Navigate to the URL
        driver.get(url)
        logger.info(f"Navigated to {url}")
        
        # Wait for the page to load initially - wait for the tile container
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "tileContainer"))
        )
        logger.info("Tile container loaded")
        
        # Initially find visible course tiles
        course_elements = driver.find_elements(By.CSS_SELECTOR, "a.tileElement")
        visible_count = len(course_elements)
        logger.info(f"Found {visible_count} visible course tiles initially")
        
        # Check if we need to load more courses
        more_button = None
        try:
            more_button = driver.find_element(By.ID, "moreTile")
            if more_button.is_displayed():
                logger.info("Found 'More' button, will attempt to load all remaining courses")
                click_more_button(driver, more_button)
                
                # Wait for potential AJAX operations to complete after loading more courses
                time.sleep(3)
                
                # Now get all the course elements, both visible and hidden
                all_elements = driver.find_elements(By.CSS_SELECTOR, "a.tileElement")
                logger.info(f"After loading all courses: found {len(all_elements)} course tiles")
                
                # Ensure we get all courses, even those that might be hidden
                # Enable all elements for scraping by making them visible via JavaScript
                driver.execute_script("""
                    document.querySelectorAll('a.tileElement').forEach(function(el) {
                        el.style.display = 'block';
                    });
                """)
                
                # Get the updated list of all course elements
                course_elements = driver.find_elements(By.CSS_SELECTOR, "a.tileElement")
                course_elements = [e for e in course_elements if e.get_attribute("id") != "moreTile"]
                
        except NoSuchElementException:
            logger.info("No 'More' button found, all courses may be displayed already")
        
        # If still no courses found, try taking a screenshot for debugging
        if len(course_elements) == 0:
            logger.warning("No course elements found, saving debug information")
            driver.save_screenshot("debug_screenshot.png")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []
        
        # Extract course information
        courses = []
        for element in course_elements:
            try:
                # Check if the element has valid content before trying to extract
                if element.get_attribute("href"):
                    # Course code is in the tileElementText span
                    code_span = element.find_element(By.CLASS_NAME, "tileElementText")
                    course_code = code_span.text.strip()
                    
                    # Course title is in the tileElementHiddenText div
                    title_div = element.find_element(By.CLASS_NAME, "tileElementHiddenText")
                    title = title_div.text.strip()
                    
                    # Get the URL (no longer capturing background color)
                    course_url = element.get_attribute("href")
                    
                    # Only add if we have both code and title
                    if course_code and title:
                        courses.append({
                            "university": university_name,  # Add university name as first column
                            "course_code": course_code,
                            "title": title,
                            "url": course_url
                        })
                    else:
                        logger.warning(f"Skipping course with incomplete data: code='{course_code}', title='{title}'")
                
            except Exception as e:
                logger.warning(f"Error extracting course data: {e}")
        
        logger.info(f"Successfully extracted data for {len(courses)} courses")
        
        # Save to CSV
        if courses:
            save_to_csv(courses, output_file)
            logger.info(f"Saved data to {output_file}")
        
        return courses
    
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        if driver:
            driver.save_screenshot("error_screenshot.png")
            with open("error_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        return []
    
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

def click_more_button(driver, more_button, max_attempts=50):
    """Click the 'More' button repeatedly until it's no longer available."""
    attempts = 0
    
    while attempts < max_attempts:
        try:
            # Check if the more button still exists and is displayed
            try:
                # Get fresh reference to the more button each time
                more_button = driver.find_element(By.ID, "moreTile")
                if not more_button.is_displayed():
                    logger.info("More button no longer displayed - all courses loaded")
                    break
            except NoSuchElementException:
                logger.info("More button no longer exists - all courses loaded")
                break
                
            # Get current course count (both visible and hidden)
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a.tileElement"))
            
            # Scroll to the button to ensure it's in view
            driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
            time.sleep(1)
            
            # Click the button
            driver.execute_script("arguments[0].click();", more_button)  # Using JS click for more reliability
            logger.info(f"Clicked 'More' button (attempt {attempts+1})")
            
            # Wait for new tiles to load by checking the count of elements
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.tileElement")) > current_count
                )
                
                new_count = len(driver.find_elements(By.CSS_SELECTOR, "a.tileElement"))
                logger.info(f"Loaded {new_count - current_count} more tiles, total now: {new_count}")
            except TimeoutException:
                logger.warning("No new tiles loaded after clicking. Might have reached the end.")
                # Try one more time to be sure
                time.sleep(3)
                new_count = len(driver.find_elements(By.CSS_SELECTOR, "a.tileElement"))
                if new_count > current_count:
                    logger.info(f"After delay: loaded {new_count - current_count} more tiles, total now: {new_count}")
                    continue
                else:
                    break
            
            attempts += 1
            time.sleep(2)  # Increased delay between clicks to let the page update fully
            
        except StaleElementReferenceException:
            logger.info("More button reference became stale, trying to find it again")
            try:
                more_button = driver.find_element(By.ID, "moreTile")
            except NoSuchElementException:
                logger.info("More button no longer exists after reference became stale")
                break
        except Exception as e:
            logger.error(f"Error clicking 'More' button: {e}")
            break
    
    if attempts >= max_attempts:
        logger.warning(f"Reached maximum number of attempts ({max_attempts}) for clicking 'More' button")
    
    logger.info(f"Finished loading all available courses after {attempts} clicks")

def save_to_csv(courses, filename):
    """Save course data to a CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["university", "course_code", "title", "url"]  # Added university as first column
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for course in courses:
                writer.writerow(course)
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")

if __name__ == "__main__":
    print("Starting scraper...")
    university_name = "Stanford"  # You can change this if scraping a different university
    courses = scrape_courses("https://www.coursicle.com/stanford/courses/CS/", university_name=university_name)
    
    if not courses:
        print("\nNo courses were scraped or an error occurred during scraping.")
        print("Please check the console output for errors, ensure website structure hasn't changed,")
        print("and verify your internet connection and Selenium setup.")
    else:
        print(f"\nSuccessfully scraped {len(courses)} {university_name} courses! Data saved to stanford_cs_courses.csv")