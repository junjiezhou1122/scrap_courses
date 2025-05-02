import os
import time
import csv
import logging
import random
from datetime import datetime

# Import from all our existing scraper modules
import sys
sys.path.append('/Users/meng/Desktop/tmp/scrap_courses/scrap_universities')
sys.path.append('/Users/meng/Desktop/tmp/scrap_courses/scrap_department')
sys.path.append('/Users/meng/Desktop/tmp/scrap_courses/scrap_courses')
sys.path.append('/Users/meng/Desktop/tmp/scrap_courses/scrap_courses_detail')

# Import the scraping functions from each module
try:
    from scrap_universities.scrape_universities import scrape_universities
    from scrap_department.scrape_departments import scrape_departments
    from scrap_courses.scrap_courses import scrape_courses
    from scrap_courses_detail.scrape_course_details import scrape_course_details
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all scraper modules are in the correct locations")
    sys.exit(1)

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
    
    for i, university in enumerate(universities):
        subdomain = university.get('subdomain')
        if not subdomain:
            logger.warning(f"Missing subdomain for university: {university}")
            continue
        
        logger.info(f"Processing university {i+1}/{total}: {subdomain}")
        
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
            else:
                # Scrape the departments
                departments = scrape_departments(university_subdomain=subdomain, output_file=output_file)
                
                if departments:
                    results[subdomain] = departments
                    logger.info(f"Successfully scraped {len(departments)} departments for {subdomain}")
                    count += 1
                else:
                    logger.warning(f"Failed to scrape departments for {subdomain}")
            
            # Add a random delay to avoid being blocked
            sleep_time = random.uniform(2, 5)
            logger.info(f"Waiting {sleep_time:.2f} seconds before next university")
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"Error processing university {subdomain}: {e}")
    
    logger.info(f"Completed scraping departments for {count} universities")
    return results

def scrape_department_courses(university_departments, limit_universities=None, limit_departments=None):
    """Scrape courses for each department."""
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
    
    for uni_idx, (university, departments) in enumerate(university_departments.items()):
        logger.info(f"Processing university {uni_idx+1}/{total_universities}: {university}")
        
        # Apply department limit if specified
        if limit_departments:
            departments = departments[:limit_departments]
        
        total_departments = len(departments)
        logger.info(f"Will process {total_departments} departments for {university}")
        
        university_results = {}
        processed_dept_count = 0
        
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
                else:
                    # Construct the URL for this department's courses
                    department_url = department.get('url')
                    
                    if not department_url:
                        # If URL is not in the department data, construct it
                        department_url = f"https://www.coursicle.com/{university}/courses/{department_code}/"
                    
                    # Scrape the courses
                    courses = scrape_courses(department_url, output_file=output_file, university_name=university)
                    
                    if courses:
                        university_results[department_code] = courses
                        logger.info(f"Successfully scraped {len(courses)} courses for {university} {department_code}")
                        processed_dept_count += 1
                    else:
                        logger.warning(f"Failed to scrape courses for {university} {department_code}")
                
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
    
    # Calculate and log total runtime
    end_time = time.time()
    total_time = end_time - start_time
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logger.info(f"Complete scraping process finished in {int(hours)}h {int(minutes)}m {int(seconds)}s")

if __name__ == "__main__":
    print("Starting Coursicle Complete Scraper")
    print("-----------------------------------")
    print("This script will scrape universities, departments, courses, and course details")
    print("The process can take a long time - use the limits to control how much is scraped")
    print("Data will be saved in the 'output' directory")
    print()
    
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