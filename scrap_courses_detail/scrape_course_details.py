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

def scrape_course_details(university_subdomain, course_dept, course_number, output_file="course_details.csv"):
    """Scrape detailed course information from a specific course page."""
    course_url = f"https://www.coursicle.com/{university_subdomain}/courses/{course_dept}/{course_number}/"
    logger.info(f"Starting course detail scraper for URL: {course_url}")
    
    driver = None
    try:
        driver = setup_driver()
        logger.info("WebDriver set up successfully")
        
        # Navigate to the URL
        driver.get(course_url)
        logger.info(f"Navigated to {course_url}")
        
        # Wait for the page to load - wait for the course title
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "itemViewHeader"))
        )
        logger.info("Course details page loaded")
        
        # Extract course title
        course_title_element = driver.find_element(By.ID, "itemViewHeader")
        course_title = course_title_element.text.strip()
        logger.info(f"Course title: {course_title}")
        
        # Extract course description
        description = ""
        try:
            description_container = driver.find_element(By.ID, "subItemDescription")
            description_content = description_container.find_element(By.CLASS_NAME, "subItemContent")
            description = description_content.text.strip()
            logger.info(f"Found course description, length: {len(description)}")
        except NoSuchElementException:
            logger.warning("Course description not found")
        
        # Extract professors
        professors = []
        try:
            professors_container = driver.find_element(By.ID, "subItemProfessors")
            professor_links = professors_container.find_elements(By.CLASS_NAME, "professorLink")
            for prof_link in professor_links:
                professors.append(prof_link.text.strip())
            logger.info(f"Found {len(professors)} professors")
        except NoSuchElementException:
            logger.warning("Professors section not found")
        
        # Extract recent semesters
        recent_semesters = ""
        try:
            # Try with the specific ID for course pages
            try:
                semesters_container = driver.find_element(By.ID, "subItemRecentSemestersCoursePage")
            except NoSuchElementException:
                # Fallback to a more generic search if the specific ID isn't found
                semesters_container = driver.find_element(By.XPATH, "//div[contains(@class, 'subItem')]/div[contains(@class, 'subItemLabel') and text()='Recent Semesters']/..")
            
            semesters_content = semesters_container.find_element(By.CLASS_NAME, "subItemContent")
            recent_semesters = semesters_content.text.strip()
            logger.info(f"Found recent semesters: {recent_semesters}")
        except NoSuchElementException:
            logger.warning("Recent semesters section not found")
        
        # Extract credits if available
        credits = ""
        try:
            credits_container = driver.find_element(By.ID, "subItemCredits")
            credits_content = credits_container.find_element(By.CLASS_NAME, "subItemContent")
            credits = credits_content.text.strip()
            logger.info(f"Found credits: {credits}")
        except NoSuchElementException:
            logger.warning("Credits section not found")
        
        # Prepare course details dictionary
        course_details = {
            "university": university_subdomain,
            "course_dept": course_dept,
            "course_number": course_number,
            "course_title": course_title,
            "description": description,
            "professors": "; ".join(professors),
            "recent_semesters": recent_semesters,
            "credits": credits,
            "url": course_url
        }
        
        # Save to CSV
        save_to_csv([course_details], output_file)
        logger.info(f"Saved course details to {output_file}")
        
        return course_details
    
    except Exception as e:
        logger.error(f"Error during course detail scraping: {e}")
        if driver:
            driver.save_screenshot("course_detail_error.png")
            with open("course_detail_error.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        return None
    
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

def scrape_multiple_courses(courses_list, output_file="courses_details.csv"):
    """Scrape details for multiple courses from a list of course information."""
    all_course_details = []
    
    for i, course in enumerate(courses_list):
        university = course.get('university', '')
        course_dept = course.get('course_dept', '')
        course_number = course.get('course_number', '')
        
        logger.info(f"Processing course {i+1}/{len(courses_list)}: {course_dept} {course_number} at {university}")
        
        try:
            course_details = scrape_course_details(university, course_dept, course_number)
            if course_details:
                all_course_details.append(course_details)
                logger.info(f"Successfully scraped details for {course_dept} {course_number}")
            
            # Add a delay between requests to avoid overloading the server
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error scraping course {course_dept} {course_number}: {e}")
    
    # Save all details to CSV
    if all_course_details:
        save_to_csv(all_course_details, output_file)
        logger.info(f"Saved details for {len(all_course_details)} courses to {output_file}")
    
    return all_course_details

def save_to_csv(courses, filename):
    """Save course details to a CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["university", "course_dept", "course_number", "course_title", 
                         "description", "professors", "recent_semesters", "credits", "url"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for course in courses:
                writer.writerow(course)
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")

def parse_course_code(full_code):
    """Parse a course code like 'CS 28' into department and number."""
    parts = full_code.strip().split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

def test_course_scraping():
    """Test the course detail scraping function with a specific example."""
    print("Starting course detail scraper test...")
    
    # Test with Stanford CS 28
    university = "stanford"
    course_dept = "CS"
    course_number = "28"
    
    course_details = scrape_course_details(university, course_dept, course_number)
    
    if not course_details:
        print("\nNo course details were scraped or an error occurred during scraping.")
        print("Please check the console output for errors, ensure website structure hasn't changed,")
        print("and verify your internet connection and Selenium setup.")
    else:
        print(f"\nSuccessfully scraped details for {course_dept} {course_number}!")
        print(f"Title: {course_details['course_title']}")
        print(f"Professors: {course_details['professors']}")
        print(f"Recent Semesters: {course_details['recent_semesters']}")
        print(f"Data saved to course_details.csv")

if __name__ == "__main__":
    test_course_scraping()