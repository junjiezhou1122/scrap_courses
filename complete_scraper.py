import os
import time
import csv
import logging
import random
import importlib.util
from datetime import datetime
import json

# Add these imports for handling user-agents and proxies
import requests
from fake_useragent import UserAgent
from requests.exceptions import ProxyError

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"complete_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Class to track entities that encountered the "you don't smell like a human" error
class HumanErrorTracker:
    def __init__(self, tracker_file="output/human_error_items.json"):
        self.tracker_file = tracker_file
        self.error_items = self._load_items()
    
    def _load_items(self):
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading human error tracker: {e}")
                return self._create_empty_tracker()
        else:
            return self._create_empty_tracker()
    
    def _create_empty_tracker(self):
        return {
            "universities": [],
            "departments": [],
            "courses": [],
            "updated_at": datetime.now().isoformat()
        }
    
    def save(self):
        self.error_items["updated_at"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.error_items, f, indent=2)
            logger.info(f"Human error items saved to {self.tracker_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving human error items: {e}")
            return False
    
    def add_university(self, subdomain):
        if subdomain not in self.error_items["universities"]:
            self.error_items["universities"].append(subdomain)
            logger.info(f"Added university {subdomain} to human error tracker")
            return self.save()
        return True
    
    def add_department(self, university, department_code):
        item = {"university": university, "department": department_code}
        if item not in self.error_items["departments"]:
            self.error_items["departments"].append(item)
            logger.info(f"Added department {department_code} at {university} to human error tracker")
            return self.save()
        return True
    
    def add_course(self, university, department_code, course_number):
        item = {"university": university, "department": department_code, "course": course_number}
        if item not in self.error_items["courses"]:
            self.error_items["courses"].append(item)
            logger.info(f"Added course {course_number} in {department_code} at {university} to human error tracker")
            return self.save()
        return True
    
    def is_university_in_error(self, subdomain):
        return subdomain in self.error_items["universities"]
    
    def is_department_in_error(self, university, department_code):
        return {"university": university, "department": department_code} in self.error_items["departments"]
    
    def is_course_in_error(self, university, department_code, course_number):
        return {"university": university, "department": department_code, "course": course_number} in self.error_items["courses"]
    
    def get_all_error_universities(self):
        return self.error_items["universities"]
    
    def get_all_error_departments(self):
        return self.error_items["departments"]
    
    def get_all_error_courses(self):
        return self.error_items["courses"]

# Initialize human error tracker
human_error_tracker = HumanErrorTracker()

# Function to get a random user agent
def get_random_user_agent():
    try:
        ua = UserAgent()
        return ua.random
    except Exception as e:
        logger.warning(f"Error getting random user agent: {e}")
        # Fallback user agents in case fake_useragent fails
        fallback_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.48',
        ]
        return random.choice(fallback_agents)

# Function to get browser-like headers
def get_browser_headers(referrer=None):
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    if referrer:
        headers['Referer'] = referrer
    
    return headers

# Proxy handling
def get_proxy():
    # You'll need to add your own proxy list or service here
    # This is just an example - you can use free proxy lists or paid services
    proxies = [
        # Add your proxies here in the format:
        # 'http://username:password@ip:port',
        # 'https://username:password@ip:port',
        # 'http://ip:port',  # For proxies without authentication
        # 'https://ip:port',
    ]
    
    if not proxies:
        return None
    
    # Choose a random proxy from the list
    proxy_url = random.choice(proxies)
    
    # Return in the format requests expects: {'http': proxy_url, 'https': proxy_url}
    # This assumes your proxy supports both HTTP and HTTPS, adjust if needed
    return {
        'http': proxy_url,
        'https': proxy_url 
    }

# Function to create a requests session with human-like behavior
def create_human_session():
    session = requests.Session()
    session.headers.update(get_browser_headers())
    
    # Add cookies and other browser-like attributes
    session.cookies.update({
        'consent': 'true',
        'visited': 'yes',
    })

    # Assign a proxy to the session if available
    proxy = get_proxy()
    if proxy:
        session.proxies = proxy
        logger.info(f"Using proxy: {proxy['http']}") # Log only one, assuming http/https are the same base
    
    return session

# Progress tracking system
class ProgressTracker:
    def __init__(self, tracker_file="output/scraping_progress.json"):
        self.tracker_file = tracker_file
        self.progress = self._load_progress()
    
    def _load_progress(self):
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading progress tracker: {e}")
                return self._create_empty_progress()
        else:
            return self._create_empty_progress()
    
    def _create_empty_progress(self):
        return {
            "universities": {},
            "departments": {},
            "courses": {},
            "course_details": {},
            "last_university_index": 0,
            "last_update": datetime.now().isoformat()
        }
    
    def save_progress(self):
        self.progress["last_update"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
            logger.info(f"Progress saved to {self.tracker_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
            return False
    
    def mark_university_processed(self, subdomain):
        self.progress["universities"][subdomain] = {
            "processed": True,
            "timestamp": datetime.now().isoformat()
        }
        return self.save_progress()
    
    def mark_department_processed(self, university, department_code):
        key = f"{university}_{department_code}"
        self.progress["departments"][key] = {
            "processed": True,
            "timestamp": datetime.now().isoformat()
        }
        return self.save_progress()
    
    def mark_course_processed(self, university, department_code, course_number):
        key = f"{university}_{department_code}_{course_number}"
        self.progress["courses"][key] = {
            "processed": True,
            "timestamp": datetime.now().isoformat()
        }
        return self.save_progress()
    
    def mark_course_detail_processed(self, university, department_code, course_number):
        key = f"{university}_{department_code}_{course_number}"
        self.progress["course_details"][key] = {
            "processed": True,
            "timestamp": datetime.now().isoformat()
        }
        return self.save_progress()
    
    def is_university_processed(self, subdomain):
        return subdomain in self.progress["universities"] and self.progress["universities"][subdomain]["processed"]
    
    def is_department_processed(self, university, department_code):
        key = f"{university}_{department_code}"
        return key in self.progress["departments"] and self.progress["departments"][key]["processed"]
    
    def is_course_processed(self, university, department_code, course_number):
        key = f"{university}_{department_code}_{course_number}"
        return key in self.progress["courses"] and self.progress["courses"][key]["processed"]
    
    def is_course_detail_processed(self, university, department_code, course_number):
        key = f"{university}_{department_code}_{course_number}"
        return key in self.progress["course_details"] and self.progress["course_details"][key]["processed"]
    
    def update_last_university_index(self, index):
        self.progress["last_university_index"] = index
        return self.save_progress()
    
    def get_last_university_index(self):
        return self.progress.get("last_university_index", 0)

# Initialize the progress tracker
progress_tracker = ProgressTracker()

# Import scripts directly using importlib
def import_module_from_file(module_name, file_path):
    """Import a module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        logger.error(f"Could not find module file: {file_path}")
        return None
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error loading module {module_name} from {file_path}: {e}")
        return None

# Import all scraper modules
base_path = os.path.dirname(os.path.abspath(__file__))
universities_module = import_module_from_file("scrape_universities", 
                                             os.path.join(base_path, "scrap_universities", "scrape_universities.py"))
departments_module = import_module_from_file("scrape_departments", 
                                            os.path.join(base_path, "scrap_department", "scrape_departments.py"))
courses_module = import_module_from_file("scrap_courses", 
                                        os.path.join(base_path, "scrap_courses", "scrap_courses.py"))
course_details_module = import_module_from_file("scrape_course_details", 
                                               os.path.join(base_path, "scrap_courses_detail", "scrape_course_details.py"))

# Verify modules were loaded correctly
if not all([universities_module, departments_module, courses_module, course_details_module]):
    logger.error("Failed to load one or more required modules")
    print("Error: Could not load all required scraper modules. Check the paths and file names.")
    import sys
    sys.exit(1)

# Function references 
scrape_universities = universities_module.scrape_universities
scrape_departments = departments_module.scrape_departments
scrape_courses = courses_module.scrape_courses
scrape_course_details = course_details_module.scrape_course_details

# Create output directories for each type of data
def create_output_dirs():
    """Create directories for storing scraped data."""
    dirs = ["universities", "departments", "courses", "course_details"]
    
    for directory in dirs:
        path = os.path.join("output", directory)
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created output directory: {path}")

def load_universities(file_path=None):
    """Load universities from file or scrape if file not provided."""
    universities = []
    
    if file_path and os.path.exists(file_path):
        logger.info(f"Loading universities from {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                universities = list(reader)
            logger.info(f"Loaded {len(universities)} universities from file")
        except Exception as e:
            logger.error(f"Error loading universities from file: {e}")
            return []
    else:
        logger.info("No university file provided or file not found, will scrape universities")
        output_file = os.path.join("output", "universities", "all_universities.csv")
        universities = scrape_universities(output_file=output_file)
        
    return universities

def scrape_university_departments(universities, limit=None, start_index=0):
    """Scrape departments for each university."""
    results = {}
    count = 0
    
    # Apply limit if specified
    if limit:
        universities = universities[start_index:start_index+limit]
    elif start_index > 0:
        universities = universities[start_index:]
    
    total = len(universities)
    logger.info(f"Starting to scrape departments for {total} universities")
    
    # Load or initialize trackers
    global progress_tracker
    global human_error_tracker
    
    for i, university in enumerate(universities):
        subdomain = university.get('subdomain')
        if not subdomain:
            logger.warning(f"Missing subdomain for university: {university}")
            continue
        
        logger.info(f"Processing university {i+1}/{total}: {subdomain}")
        
        # Update the last university index in the progress tracker
        progress_tracker.update_last_university_index(start_index + i)
        
        # Check if this university is in the human error tracker (had 'you don't smell like a human' error)
        if human_error_tracker.is_university_in_error(subdomain):
            logger.warning(f"University {subdomain} is in human error tracker (previously had 'you don't smell like a human' error)")
            logger.warning(f"Skipping {subdomain} for now")
            print(f"⚠️ Skipping {subdomain} as it previously triggered the 'you don't smell like a human' error")
            continue
        
        # Check if we should skip this university based on progress tracker
        if progress_tracker.is_university_processed(subdomain):
            logger.info(f"University {subdomain} already processed according to progress tracker, checking for existing data")
            
            output_file = os.path.join("output", "departments", f"{subdomain}_departments.csv")
            if os.path.exists(output_file):
                # Load the existing departments
                with open(output_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    departments = list(reader)
                    
                results[subdomain] = departments
                logger.info(f"Loaded {len(departments)} existing departments for {subdomain}")
                continue
            else:
                logger.warning(f"University marked as processed but no data file found for {subdomain}, will scrape again")
        
        try:
            output_file = os.path.join("output", "departments", f"{subdomain}_departments.csv")
            
            # Check if we already have this university's departments
            if os.path.exists(output_file):
                logger.info(f"Departments for {subdomain} already exist in {output_file}, skipping")
                
                # Load the existing departments
                with open(output_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    departments = list(reader)
                    
                results[subdomain] = departments
                logger.info(f"Loaded {len(departments)} existing departments for {subdomain}")
                
                # Mark as processed in tracker
                progress_tracker.mark_university_processed(subdomain)
            else:
                # Scrape the departments with progress tracking and human error tracking
                departments = scrape_departments(
                    university_subdomain=subdomain, 
                    output_file=output_file,
                    progress_tracker=progress_tracker,
                    human_error_tracker=human_error_tracker
                )
                
                if departments:
                    results[subdomain] = departments
                    logger.info(f"Successfully scraped {len(departments)} departments for {subdomain}")
                    count += 1
                else:
                    logger.warning(f"Failed to scrape departments for {subdomain}")
            
            # Add a random delay with more variance to avoid being blocked
            sleep_time = random.uniform(3, 8)
            logger.info(f"Waiting {sleep_time:.2f} seconds before next university")
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"Error processing university {subdomain}: {e}")
    
    logger.info(f"Completed scraping departments for {count} universities")
    return results

def extract_courses_from_department_html(html_content, department_url, university_name):
    """Extract course information directly from department page HTML to avoid visiting each course URL."""
    from bs4 import BeautifulSoup
    
    courses = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        course_tiles = soup.select("a.tileElement:not(#moreTile)")
        
        logger.info(f"Found {len(course_tiles)} course tiles on department page")
        
        for tile in course_tiles:
            try:
                course_url = tile.get('href', '')
                course_code_elem = tile.select_one("div.tileElementSubText")
                course_title_elem = tile.select_one("div.tileElementText")
                
                course_code = course_code_elem.text.strip() if course_code_elem else ""
                course_title = course_title_elem.text.strip() if course_title_elem else ""
                
                # Skip entries without course codes
                if not course_code:
                    continue
                    
                courses.append({
                    'course_code': course_code,
                    'title': course_title,
                    'url': course_url,
                    'university': university_name
                })
                
            except Exception as e:
                logger.warning(f"Error extracting course data from tile: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(courses)} courses from department HTML")
        return courses
        
    except Exception as e:
        logger.error(f"Error parsing department HTML: {e}")
        return []

def scrape_department_courses(university_departments, limit_universities=None, limit_departments=None):
    """Scrape courses for each department with bot detection avoidance."""
    results = {}
    university_count = 0
    department_count = 0
    
    # Apply university limit if specified
    if limit_universities:
        university_keys = list(university_departments.keys())[:limit_universities]
        filtered_data = {k: university_departments[k] for k in university_keys}
        university_departments = filtered_data
    
    total_universities = len(university_departments)
    logger.info(f"Starting to scrape courses for departments from {total_universities} universities")
    
    # Create a session to maintain cookies and headers
    session = create_human_session()
    
    for uni_idx, (university, departments) in enumerate(university_departments.items()):
        logger.info(f"Processing university {uni_idx+1}/{total_universities}: {university}")
        
        # Apply department limit if specified
        if limit_departments:
            departments = departments[:limit_departments]
        
        total_departments = len(departments)
        logger.info(f"Will process {total_departments} departments for {university}")
        
        university_results = {}
        processed_dept_count = 0
        
        # Check if university has bot detection issues
        university_has_bot_issues = human_error_tracker.is_university_in_error(university)
        if university_has_bot_issues:
            logger.warning(f"University {university} is flagged for bot detection issues, using fallback method")
        
        for dept_idx, department in enumerate(departments):
            department_code = department.get('department_code')
            
            if not department_code:
                logger.warning(f"Missing department code for department: {department}")
                continue
            
            logger.info(f"Processing department {dept_idx+1}/{total_departments}: {department_code} at {university}")
            
            try:
                output_file = os.path.join("output", "courses", f"{university}_{department_code}_courses.csv")
                
                # Check if we already have this department's courses
                if os.path.exists(output_file):
                    logger.info(f"Courses for {university} {department_code} already exist in {output_file}, skipping")
                    
                    # Load the existing courses
                    with open(output_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        courses = list(reader)
                        
                    university_results[department_code] = courses
                    logger.info(f"Loaded {len(courses)} existing courses for {university} {department_code}")
                    continue
                
                # Check if department has bot detection issues
                dept_has_issues = human_error_tracker.is_department_in_error(university, department_code)
                
                # Determine if we should use fallback method (directly parse department HTML)
                use_fallback = university_has_bot_issues or dept_has_issues
                
                # Get department URL from the department data
                department_url = department.get('url')
                if not department_url:
                    # If URL is not in the department data, construct it
                    department_url = f"https://www.coursicle.com/{university}/courses/{department_code}/"
                
                # Use fallback method or regular scraping
                courses = []
                
                if use_fallback:
                    logger.info(f"Using fallback method for {university} {department_code} due to bot detection concerns")
                    
                    # Make a single request to the department page with our human-like session
                    try:
                        # Rotate headers for each request
                        session.headers.update(get_browser_headers(department_url))
                        
                        # Rotate proxy if session has proxies enabled
                        if session.proxies:
                            new_proxy = get_proxy()
                            if new_proxy:
                                session.proxies = new_proxy
                                logger.info(f"Rotated proxy to: {new_proxy['http']}")
                            else:
                                # If get_proxy returns None, clear session proxies
                                session.proxies = {} 
                                logger.info("Proxy list exhausted or empty, continuing without proxy")

                        # Add a delay before request
                        time.sleep(random.uniform(2, 5))
                        
                        # Make request
                        response = session.get(department_url, timeout=30)
                        
                        if "you don't smell like a human" in response.text.lower():
                            logger.warning(f"Bot detection triggered for {university} {department_code}, adding to tracker")
                            human_error_tracker.add_department(university, department_code)
                            
                            # Try with a completely fresh session and extra delay
                            logger.info("Trying with fresh session after a long delay...")
                            time.sleep(random.uniform(15, 30))
                            
                            fresh_session = create_human_session() # This will also get a new proxy if available
                            fresh_session.headers.update(get_browser_headers("https://www.google.com"))
                            
                            # First visit Google to look more like a real user
                            try:
                                fresh_session.get("https://www.google.com", timeout=15)
                                time.sleep(random.uniform(2, 5))
                            except Exception as ge:
                                logger.warning(f"Could not reach Google via proxy/network: {ge}")

                            # Then try the department URL
                            response = fresh_session.get(department_url, timeout=30)
                            
                            if "you don't smell like a human" in response.text.lower():
                                logger.error(f"Bot detection still triggered with fresh session for {university} {department_code}")
                                continue
                        
                        # Extract courses from the HTML
                        courses = extract_courses_from_department_html(response.text, department_url, university)
                        
                    except ProxyError as pe:
                         logger.error(f"Proxy error during fallback scraping for {university} {department_code}: {pe}")
                         # Optionally, implement logic to remove the failing proxy from your list
                         continue # Skip this department due to proxy failure
                    except Exception as e:
                        logger.error(f"Error with fallback scraping method: {e}")
                        continue
                else:
                    # Use the regular scraping method (imported from courses_module)
                    courses = scrape_courses(department_url, output_file=output_file, university_name=university)
                
                # Process results
                if courses:
                    # Write to file if not already written by scrape_courses
                    if use_fallback:
                        fieldnames = ['course_code', 'title', 'url', 'university']
                        try:
                            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(courses)
                            logger.info(f"Wrote {len(courses)} courses to {output_file}")
                        except Exception as e:
                            logger.error(f"Error writing courses to file: {e}")
                    
                    university_results[department_code] = courses
                    logger.info(f"Successfully scraped {len(courses)} courses for {university} {department_code}")
                    processed_dept_count += 1
                else:
                    logger.warning(f"No courses found for {university} {department_code}")
                
                # Add a random delay to avoid being blocked
                sleep_time = random.uniform(1, 3)
                logger.info(f"Waiting {sleep_time:.2f} seconds before next department")
                time.sleep(sleep_time)
                
                department_count += 1
                
            except Exception as e:
                logger.error(f"Error processing department {department_code} at {university}: {e}")
        
        results[university] = university_results
        
        if processed_dept_count > 0:
            university_count += 1
        
        # Add a larger delay between universities
        sleep_time = random.uniform(5, 10)
        logger.info(f"Waiting {sleep_time:.2f} seconds before next university")
        time.sleep(sleep_time)
    
    logger.info(f"Completed scraping courses for {department_count} departments from {university_count} universities")
    return results

def scrape_course_details_for_all(university_department_courses, limit_universities=None, limit_departments=None, limit_courses=None):
    """Scrape detailed information for each course."""
    results = {}
    university_count = 0
    department_count = 0
    course_count = 0
    
    # Apply university limit if specified
    if limit_universities:
        university_keys = list(university_department_courses.keys())[:limit_universities]
        filtered_data = {k: university_department_courses[k] for k in university_keys}
        university_department_courses = filtered_data
    
    total_universities = len(university_department_courses)
    logger.info(f"Starting to scrape details for courses from {total_universities} universities")
    
    for uni_idx, (university, departments) in enumerate(university_department_courses.items()):
        logger.info(f"Processing university {uni_idx+1}/{total_universities}: {university}")
        
        # Apply department limit if specified
        if limit_departments:
            department_keys = list(departments.keys())[:limit_departments]
            filtered_departments = {k: departments[k] for k in department_keys}
            departments = filtered_departments
        
        total_departments = len(departments)
        logger.info(f"Will process {total_departments} departments for {university}")
        
        university_results = {}
        processed_dept_count = 0
        
        for dept_idx, (department_code, courses) in enumerate(departments.items()):
            logger.info(f"Processing department {dept_idx+1}/{total_departments}: {department_code} at {university}")
            
            # Apply course limit if specified
            if limit_courses:
                courses = courses[:limit_courses]
            
            total_courses = len(courses)
            logger.info(f"Will process {total_courses} courses for {university} {department_code}")
            
            department_results = []
            processed_course_count = 0
            
            for course_idx, course in enumerate(courses):
                course_number = course.get('course_code')
                
                if not course_number:
                    logger.warning(f"Missing course code for course: {course}")
                    continue
                
                # Some courses might have their code in different formats, extract only the number part
                if ' ' in course_number:
                    parts = course_number.split(' ')
                    if len(parts) >= 2:
                        course_number = parts[1]
                
                logger.info(f"Processing course {course_idx+1}/{total_courses}: {department_code} {course_number} at {university}")
                
                try:
                    output_file = os.path.join("output", "course_details", f"{university}_{department_code}_{course_number}_details.csv")
                    
                    # Check if we already have this course's details
                    if os.path.exists(output_file):
                        logger.info(f"Details for {university} {department_code} {course_number} already exist in {output_file}, skipping")
                        
                        # Load the existing course details
                        with open(output_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            details = list(reader)
                            
                        if details:
                            department_results.append(details[0])
                            logger.info(f"Loaded existing details for {university} {department_code} {course_number}")
                    else:
                        # Scrape the course details
                        details = scrape_course_details(university, department_code, course_number, output_file=output_file)
                        
                        if details:
                            department_results.append(details)
                            logger.info(f"Successfully scraped details for {university} {department_code} {course_number}")
                            processed_course_count += 1
                        else:
                            logger.warning(f"Failed to scrape details for {university} {department_code} {course_number}")
                    
                    # Add a random delay to avoid being blocked
                    sleep_time = random.uniform(1, 2)
                    logger.info(f"Waiting {sleep_time:.2f} seconds before next course")
                    time.sleep(sleep_time)
                    
                    course_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing course {department_code} {course_number} at {university}: {e}")
            
            if department_results:
                university_results[department_code] = department_results
                if processed_course_count > 0:
                    processed_dept_count += 1
            
            # Add a larger delay between departments
            sleep_time = random.uniform(2, 5)
            logger.info(f"Waiting {sleep_time:.2f} seconds before next department")
            time.sleep(sleep_time)
            
            department_count += 1
            
        if university_results:
            results[university] = university_results
            if processed_dept_count > 0:
                university_count += 1
        
        # Add an even larger delay between universities
        sleep_time = random.uniform(5, 15)
        logger.info(f"Waiting {sleep_time:.2f} seconds before next university")
        time.sleep(sleep_time)
    
    logger.info(f"Completed scraping details for {course_count} courses from {department_count} departments and {university_count} universities")
    return results

def generate_consolidated_csv(universities, university_departments, university_department_courses, course_details, output_file="output/all_data_consolidated.csv"):
    """Generate a single consolidated CSV file with all scraped data."""
    logger.info("Generating consolidated CSV file with all scraped data")
    consolidated_data = []
    
    # Prepare university info lookup
    university_info = {}
    for uni in universities:
        subdomain = uni.get('subdomain')
        if subdomain:
            university_info[subdomain] = uni
    
    # Process all data
    for university_subdomain, departments in university_departments.items():
        # Get university info
        uni_info = university_info.get(university_subdomain, {})
        university_name = uni_info.get('name', university_subdomain)
        university_location = uni_info.get('location', '')
        
        # Get departments for this university
        for department in departments:
            department_code = department.get('department_code', '')
            department_url = department.get('url', '')
            
            # Get courses for this department
            courses = []
            if university_subdomain in university_department_courses:
                uni_courses = university_department_courses[university_subdomain]
                if department_code in uni_courses:
                    courses = uni_courses[department_code]
            
            for course in courses:
                course_code = course.get('course_code', '')
                course_title = course.get('title', '')
                course_url = course.get('url', '')
                
                # Extract course number from code if it contains a space
                course_number = course_code
                if ' ' in course_code:
                    parts = course_code.split(' ')
                    if len(parts) >= 2:
                        course_number = parts[1]
                
                # Get course details
                course_desc = ""
                course_professors = ""
                course_semesters = ""
                course_credits = ""
                
                # Look for this course in the course details
                if university_subdomain in course_details:
                    uni_details = course_details[university_subdomain]
                    if department_code in uni_details:
                        dept_details = uni_details[department_code]
                        
                        # Find matching course detail
                        for detail in dept_details:
                            if detail.get('course_number') == course_number:
                                course_desc = detail.get('description', '')
                                course_professors = detail.get('professors', '')
                                course_semesters = detail.get('recent_semesters', '')
                                course_credits = detail.get('credits', '')
                                break
                
                # Add this course to the consolidated data
                consolidated_data.append({
                    'university_subdomain': university_subdomain,
                    'university_name': university_name,
                    'university_location': university_location,
                    'department_code': department_code,
                    'department_url': department_url,
                    'course_code': course_code,
                    'course_title': course_title,
                    'course_url': course_url,
                    'course_description': course_desc,
                    'course_professors': course_professors,
                    'course_recent_semesters': course_semesters,
                    'course_credits': course_credits
                })
    
    # Save to CSV
    if consolidated_data:
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'university_subdomain', 'university_name', 'university_location',
                    'department_code', 'department_url',
                    'course_code', 'course_title', 'course_url',
                    'course_description', 'course_professors', 'course_recent_semesters', 'course_credits'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for data in consolidated_data:
                    writer.writerow(data)
                
            logger.info(f"Successfully saved {len(consolidated_data)} records to consolidated file: {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error writing consolidated CSV: {e}")
            return False
    else:
        logger.warning("No data to write to consolidated CSV")
        return False

def run_complete_scrape(
    universities_file=None,
    limit_universities=None,
    limit_departments=None,
    limit_courses=None,
    start_university_index=0,
    skip_universities=False,
    skip_departments=False,
    skip_courses=False,
    skip_details=False
):
    """Run the complete scraping process from universities to course details."""
    start_time = time.time()
    logger.info("Starting complete scraping process")
    
    # Create output directories
    create_output_dirs()
    
    # Step 1: Get universities (either from file or by scraping)
    universities = []
    if not skip_universities:
        universities = load_universities(universities_file)
        logger.info(f"Loaded/scraped {len(universities)} universities")
    elif universities_file and os.path.exists(universities_file):
        universities = load_universities(universities_file)
        logger.info(f"Loaded {len(universities)} universities from file (skipping scraping)")
    else:
        logger.error("No university file provided and university scraping is skipped, cannot proceed")
        return
    
    # Step 2: Get departments for each university
    university_departments = {}
    if not skip_departments:
        university_departments = scrape_university_departments(
            universities, 
            limit=limit_universities,
            start_index=start_university_index
        )
        logger.info(f"Scraped departments for {len(university_departments)} universities")
    else:
        logger.info("Skipping department scraping")
        # If departments are skipped, try to load from existing files
        output_dir = os.path.join("output", "departments")
        if os.path.exists(output_dir):
            for university in universities:
                subdomain = university.get('subdomain')
                if not subdomain:
                    continue
                
                file_path = os.path.join(output_dir, f"{subdomain}_departments.csv")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        departments = list(reader)
                        
                    if departments:
                        university_departments[subdomain] = departments
                        logger.info(f"Loaded {len(departments)} departments for {subdomain} from file")
        
        if not university_departments:
            logger.warning("No department data available, cannot proceed to course scraping")
            if not skip_courses and not skip_details:
                return
    
    # Step 3: Get courses for each department
    university_department_courses = {}
    if not skip_courses and university_departments:
        university_department_courses = scrape_department_courses(
            university_departments,
            limit_universities=limit_universities,
            limit_departments=limit_departments
        )
        logger.info(f"Scraped courses for {len(university_department_courses)} universities")
    else:
        logger.info("Skipping course scraping")
        # If courses are skipped, try to load from existing files
        if university_departments:
            university_department_courses = {}
            output_dir = os.path.join("output", "courses")
            
            if os.path.exists(output_dir):
                for university, departments in university_departments.items():
                    university_courses = {}
                    
                    for department in departments:
                        department_code = department.get('department_code')
                        if not department_code:
                            continue
                        
                        file_path = os.path.join(output_dir, f"{university}_{department_code}_courses.csv")
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                reader = csv.DictReader(f)
                                courses = list(reader)
                                
                            if courses:
                                university_courses[department_code] = courses
                                logger.info(f"Loaded {len(courses)} courses for {university} {department_code} from file")
                    
                    if university_courses:
                        university_department_courses[university] = university_courses
            
            if not university_department_courses:
                logger.warning("No course data available, cannot proceed to course details scraping")
                if not skip_details:
                    return
    
    # Step 4: Get details for each course
    course_details = {}
    if not skip_details and university_department_courses:
        course_details = scrape_course_details_for_all(
            university_department_courses,
            limit_universities=limit_universities,
            limit_departments=limit_departments,
            limit_courses=limit_courses
        )
        logger.info(f"Scraped details for courses from {len(course_details)} universities")
    else:
        logger.info("Skipping course details scraping")
        # Try to load existing course details
        if university_department_courses:
            course_details = {}
            output_dir = os.path.join("output", "course_details")
            
            if os.path.exists(output_dir):
                for university, departments in university_department_courses.items():
                    university_details = {}
                    
                    for dept_code, courses in departments.items():
                        department_details = []
                        
                        for course in courses:
                            course_code = course.get('course_code', '')
                            course_number = course_code
                            
                            # Extract course number if needed
                            if ' ' in course_code:
                                parts = course_code.split(' ')
                                if len(parts) >= 2:
                                    course_number = parts[1]
                            
                            file_path = os.path.join(output_dir, f"{university}_{dept_code}_{course_number}_details.csv")
                            if os.path.exists(file_path):
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    reader = csv.DictReader(f)
                                    details = list(reader)
                                    
                                if details:
                                    department_details.append(details[0])
                        
                        if department_details:
                            university_details[dept_code] = department_details
                    
                    if university_details:
                        course_details[university] = university_details
    
    # Generate consolidated CSV with all data
    consolidated_output = os.path.join("output", "all_coursicle_data.csv")
    success = generate_consolidated_csv(
        universities, 
        university_departments, 
        university_department_courses, 
        course_details,
        output_file=consolidated_output
    )
    
    if success:
        logger.info(f"Successfully generated consolidated CSV file: {consolidated_output}")
        print(f"\nAll data has been consolidated into a single CSV file: {consolidated_output}")
    else:
        logger.warning("Failed to generate consolidated CSV file")
        print("\nWarning: Could not generate consolidated CSV file. Check logs for details.")
    
    # Calculate and log total runtime
    end_time = time.time()
    total_time = end_time - start_time
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logger.info(f"Complete scraping process finished in {int(hours)}h {int(minutes)}m {int(seconds)}s")

def retry_human_error_universities():
    """Retry scraping universities that previously encountered 'you don't smell like a human' errors."""
    global human_error_tracker
    global progress_tracker
    
    # Create necessary directories
    create_output_dirs()
    
    # Get all universities that triggered the human error
    error_universities = human_error_tracker.get_all_error_universities()
    
    if not error_universities:
        print("No universities found that previously triggered bot detection.")
        return
    
    print(f"\nFound {len(error_universities)} universities that previously triggered bot detection:")
    for i, univ in enumerate(error_universities):
        print(f"{i+1}. {univ}")
    
    print("\nWe'll attempt to scrape these with enhanced anti-bot measures.")
    
    # Use an increased delay and even more randomization
    min_delay = float(input("Enter minimum delay between requests (seconds, recommended 10+): ") or "10")
    max_delay = float(input("Enter maximum delay between requests (seconds, recommended 30+): ") or "30")
    
    # We'll need to load the list of all universities to get their full info
    all_universities = []
    universities_file = os.path.join("output", "universities", "all_universities.csv")
    if os.path.exists(universities_file):
        with open(universities_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            all_universities = list(reader)
    
    if not all_universities:
        print("Error: Could not load university data. Need full university info to retry.")
        return
    
    # Filter to only the universities with errors
    retry_universities = [u for u in all_universities if u.get('subdomain') in error_universities]
    
    total = len(retry_universities)
    print(f"\nPreparing to retry {total} universities with enhanced anti-bot measures.")
    print("Press Ctrl+C at any time to stop the process.")
    
    try:
        # Start with a long delay before the first request
        print("Waiting before starting retries...")
        time.sleep(random.uniform(15, 30))
        
        for i, university in enumerate(retry_universities):
            subdomain = university.get('subdomain')
            if not subdomain:
                continue
                
            print(f"\nRetrying university {i+1}/{total}: {subdomain}")
            
            # First, remove this university from the human error tracker since we're retrying it
            if subdomain in human_error_tracker.error_items["universities"]:
                human_error_tracker.error_items["universities"].remove(subdomain)
                human_error_tracker.save()
                print(f"Removed {subdomain} from human error tracker for retry")
            
            output_file = os.path.join("output", "departments", f"{subdomain}_departments.csv")
            
            # Try to scrape with enhanced anti-bot measures
            print(f"Starting scrape attempt for {subdomain} with enhanced anti-bot measures...")
            
            # Create a special instance of departments_module.scrape_departments with even more anti-bot protection
            from selenium import webdriver
            from datetime import datetime
            
            # We need to import these from scrape_departments.py
            try:
                from scrap_department.scrape_departments import setup_driver, add_human_behavior, save_to_csv
                
                # Use a completely different setup for enhanced anti-bot protection
                def enhanced_setup_driver():
                    """Set up a WebDriver with extreme anti-bot measures."""
                    options = webdriver.ChromeOptions()
                    
                    # Use a completely random user agent
                    user_agent = get_random_user_agent()
                    options.add_argument(f'user-agent={user_agent}')
                    
                    # Add enhanced anti-detection measures
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_argument("--disable-extensions")
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    options.add_experimental_option('useAutomationExtension', False)
                    
                    # Standard options
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    
                    # Add proxy if needed - you could implement proxy rotation here
                    # options.add_argument('--proxy-server=http://your-proxy-address:port')
                    
                    # Set a completely random window size for each session
                    driver = webdriver.Chrome(options=options)
                    
                    # Mask WebDriver with more aggressive measures
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() { return [1, 2, 3, 4, 5]; }})")
                    
                    # Random window size that looks like a real browser
                    window_width = random.randint(1100, 1300)
                    window_height = random.randint(800, 1000)
                    driver.set_window_size(window_width, window_height)
                    
                    # Long page load timeout
                    driver.set_page_load_timeout(45)
                    return driver
                
                # Create a very human-like scraping routine
                driver = None
                try:
                    driver = enhanced_setup_driver()
                    logger.info(f"Enhanced WebDriver set up for retry of {subdomain}")
                    
                    # First, visit some popular websites to look more human
                    popular_sites = [
                        "https://www.google.com", 
                        "https://www.wikipedia.org",
                        "https://www.amazon.com"
                    ]
                    random.shuffle(popular_sites)
                    
                    # Visit 1-2 popular sites first to establish a normal browsing pattern
                    for i in range(random.randint(1, 2)):
                        if i < len(popular_sites):
                            print(f"Visiting common website first to appear more human...")
                            driver.get(popular_sites[i])
                            time.sleep(random.uniform(3, 6))
                    
                    # Then visit the university homepage
                    home_url = f"https://www.coursicle.com/{subdomain}/"
                    print(f"Visiting university homepage: {home_url}")
                    driver.get(home_url)
                    
                    # Very long wait and human-like behavior
                    wait_time = random.uniform(8, 15) 
                    print(f"Waiting {wait_time:.1f} seconds on homepage...")
                    time.sleep(wait_time)
                    add_human_behavior(driver)
                    
                    # Now navigate to the courses URL
                    courses_url = f"https://www.coursicle.com/{subdomain}/courses/"
                    print(f"Navigating to courses page: {courses_url}")
                    driver.get(courses_url)
                    
                    # Another long wait that's very human-like
                    wait_time = random.uniform(min_delay, max_delay)
                    print(f"Waiting {wait_time:.1f} seconds for page to fully load...")
                    time.sleep(wait_time)
                    
                    # Add random mouse movements and scrolls
                    add_human_behavior(driver)
                    
                    # Check for bot detection
                    if "you don't smell like a human" in driver.page_source.lower():
                        print(f"⚠️ Bot detection still triggered for {subdomain}! Saving screenshot and skipping.")
                        
                        # Save evidence
                        error_dir = "error_screenshots"
                        os.makedirs(error_dir, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_file = os.path.join(error_dir, f"retry_bot_detection_{subdomain}_{timestamp}.png")
                        driver.save_screenshot(screenshot_file)
                        
                        # Add back to human error tracker
                        human_error_tracker.add_university(subdomain)
                    else:
                        print("No bot detection found! Proceeding to scrape departments.")
                        
                        # Try to find department elements
                        from selenium.webdriver.common.by import By
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        
                        try:
                            # Wait for tile container with long timeout
                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.ID, "tileContainer"))
                            )
                            
                            # More human-like behavior
                            add_human_behavior(driver)
                            
                            # Check for more button and click if needed
                            try:
                                more_button = WebDriverWait(driver, 5).until(
                                    EC.presence_of_element_located((By.ID, "moreTile"))
                                )
                                
                                # Click the button multiple times if needed with random delays
                                while more_button.is_displayed():
                                    # Scroll to the button very naturally
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", more_button)
                                    time.sleep(random.uniform(2, 3))
                                    
                                    # Click with JavaScript
                                    driver.execute_script("arguments[0].click();", more_button)
                                    print("Clicked 'More' button")
                                    
                                    # Wait between clicks
                                    time.sleep(random.uniform(3, 5))
                            except Exception:
                                print("No 'More' button found or it's already been fully expanded")
                            
                            # Get all department elements
                            department_elements = driver.find_elements(By.CSS_SELECTOR, "a.tileElement:not(#moreTile)")
                            print(f"Found {len(department_elements)} department tiles")
                            
                            # Extract departments
                            departments = []
                            for element in department_elements:
                                name_element = element.find_element(By.CLASS_NAME, "tileElementText")
                                department_name = name_element.text.strip()
                                department_url = element.get_attribute("href")
                                
                                departments.append({
                                    "university": subdomain,
                                    "department_code": department_name,
                                    "url": department_url
                                })
                                
                                print(f"Found department: {department_name}")
                            
                            # Save results
                            if departments:
                                save_to_csv(departments, output_file)
                                print(f"✅ Successfully saved {len(departments)} departments to {output_file}")
                                
                                # Mark university as processed in progress tracker
                                progress_tracker.mark_university_processed(subdomain)
                            else:
                                print("⚠️ No departments found despite no bot detection")
                                human_error_tracker.add_university(subdomain)
                        
                        except Exception as e:
                            print(f"Error during scraping: {e}")
                            human_error_tracker.add_university(subdomain)
                
                except Exception as e:
                    print(f"Error setting up enhanced scraping for {subdomain}: {e}")
                    human_error_tracker.add_university(subdomain)
                
                finally:
                    if driver:
                        driver.quit()
                        print("Browser closed")
            
            except Exception as e:
                print(f"Could not import required modules: {e}")
                human_error_tracker.add_university(subdomain)
            
            # Long delay between universities
            wait_time = random.uniform(max_delay, max_delay * 1.5)
            print(f"Waiting {wait_time:.1f} seconds before next university...")
            time.sleep(wait_time)
    
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    
    finally:
        remaining = [u for u in human_error_tracker.get_all_error_universities()]
        if remaining:
            print(f"\nStill have {len(remaining)} universities with bot detection issues:")
            for univ in remaining:
                print(f"- {univ}")
            print("\nYou can retry these again later with even longer delays.")
        else:
            print("\nAll universities successfully scraped!")

def run_from_human_error_file():
    """Run scraping only for the items in the human error tracker that had bot detection issues."""
    global human_error_tracker
    
    error_file = "output/human_error_items.json"
    if not os.path.exists(error_file):
        print(f"No human error file found at {error_file}")
        return
    
    retry_human_error_universities()

if __name__ == "__main__":
    print("Starting Coursicle Complete Scraper")
    print("-----------------------------------")
    print("This script will scrape universities, departments, courses, and course details")
    print("Data will be saved in the 'output' directory")
    print()
    
    # Check if we have a human error file and offer to retry those first
    error_file = "output/human_error_items.json"
    if os.path.exists(error_file):
        try:
            with open(error_file, 'r') as f:
                error_data = json.load(f)
                if error_data.get("universities"):
                    print(f"Found {len(error_data['universities'])} universities that previously triggered bot detection.")
                    retry_option = input("Do you want to retry scraping these with enhanced anti-bot measures? (y/n) [n]: ").lower()
                    if retry_option == 'y':
                        retry_human_error_universities()
                        # Exit after retry attempt
                        print("\nRetry process completed. Run the script again for regular scraping.")
                        sys.exit(0)
        except Exception as e:
            print(f"Error reading human error file: {e}")
    
    # Ask for operation mode
    print("\nSelect operation mode:")
    print("1. Complete scrape (standard operation)")
    print("2. Retry universities with bot detection issues")
    print("3. Re-scrape courses using department HTML parsing (for bot detection issues)")
    print("4. Exit")
    
    mode = input("Enter your choice (1-4): ")
    
    if mode == "2":
        retry_human_error_universities()
        sys.exit(0)
    elif mode == "3":
        print("\nRe-scraping courses using department HTML parsing method...")
        
        # Load university data
        universities_file = os.path.join("output", "universities", "all_universities.csv")
        if not os.path.exists(universities_file):
            print(f"Error: University data not found at {universities_file}")
            sys.exit(1)
            
        universities = load_universities(universities_file)
        
        # Load department data for universities with bot detection issues
        university_departments = {}
        error_universities = human_error_tracker.get_all_error_universities()
        
        print(f"Found {len(error_universities)} universities with bot detection issues")
        
        # Ask if user wants to re-scrape all universities or just the problematic ones
        scope = input("Re-scrape courses for all universities (a) or just those with bot detection issues (b)? [b]: ").lower()
        
        departments_dir = os.path.join("output", "departments")
        if not os.path.exists(departments_dir):
            print(f"Error: Department data directory not found at {departments_dir}")
            sys.exit(1)
            
        # Load department data
        if scope == "a":
            print("Loading department data for all universities...")
            target_universities = [u.get('subdomain') for u in universities if u.get('subdomain')]
        else:
            print("Loading department data for universities with bot detection issues...")
            target_universities = error_universities
            
        for subdomain in target_universities:
            file_path = os.path.join(departments_dir, f"{subdomain}_departments.csv")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    departments = list(reader)
                    
                if departments:
                    university_departments[subdomain] = departments
                    print(f"Loaded {len(departments)} departments for {subdomain}")
            
        if not university_departments:
            print("No department data found. Cannot proceed.")
            sys.exit(1)
            
        # Run the modified scrape_department_courses function
        print(f"Starting to re-scrape courses for {len(university_departments)} universities using department HTML parsing")
        scrape_department_courses(university_departments)
        
        print("\nCourse re-scraping complete!")
        sys.exit(0)
    elif mode == "4":
        print("Exiting program.")
        sys.exit(0)
    elif mode != "1":
        print("Invalid choice, defaulting to complete scrape.")
        
    # Regular scraping process
    print("\nConfiguring complete scrape process...")
    
    # Ask for user input on what to scrape
    skip_universities = input("Skip university scraping (y/n)? [n]: ").lower() == 'y'
    universities_file = None
    if skip_universities:
        default_file = os.path.join("output", "universities", "all_universities.csv")
        if os.path.exists(default_file):
            universities_file = default_file
            print(f"Using existing university data from {default_file}")
        else:
            file_input = input(f"Enter path to universities CSV file: ")
            if file_input and os.path.exists(file_input):
                universities_file = file_input
            else:
                print("No valid file provided. Cannot proceed without university data.")
                sys.exit(1)
    
    skip_departments = input("Skip department scraping (y/n)? [n]: ").lower() == 'y'
    skip_courses = input("Skip course scraping (y/n)? [n]: ").lower() == 'y'
    skip_details = input("Skip course details scraping (y/n)? [n]: ").lower() == 'y'
    
    # Ask for limits
    limit_universities = input("Limit number of universities to scrape (leave blank for all): ")
    limit_universities = int(limit_universities) if limit_universities.isdigit() else None
    
    start_index = input("Start university index (leave blank for 0): ")
    start_index = int(start_index) if start_index.isdigit() else 0
    
    limit_departments = input("Limit number of departments per university (leave blank for all): ")
    limit_departments = int(limit_departments) if limit_departments.isdigit() else None
    
    limit_courses = input("Limit number of courses per department (leave blank for all): ")
    limit_courses = int(limit_courses) if limit_courses.isdigit() else None
    
    print("\nStarting scraping process...")
    run_complete_scrape(
        universities_file=universities_file,
        limit_universities=limit_universities,
        limit_departments=limit_departments,
        limit_courses=limit_courses,
        start_university_index=start_index,
        skip_universities=skip_universities,
        skip_departments=skip_departments,
        skip_courses=skip_courses,
        skip_details=skip_details
    )
    
    print("\nScraping complete! Check the logs for details.")