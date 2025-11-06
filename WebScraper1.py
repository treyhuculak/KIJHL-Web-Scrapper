from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class WebScraper:
    def __init__(self, url):
        self.url = url
        self.page_content = None
        self.driver = None

    def setup_driver(self, headless=True):
        """Set up Chrome driver with options"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")  # Run without opening browser window
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)

    def fetch_page(self, wait_for_class=None, timeout=10):
        """
        Fetch page using Selenium and wait for JavaScript to load
        
        Args:
            wait_for_class: Class name to wait for before getting page content
            timeout: Maximum seconds to wait for element
        """
        try:
            if self.driver is None:
                self.setup_driver()
            
            print(f"Loading page: {self.url}")
            self.driver.get(self.url)
            
            # Wait for the page to load
            if wait_for_class:
                print(f"Waiting for element with class: {wait_for_class}")
                wait = WebDriverWait(self.driver, timeout)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, wait_for_class)))
            else:
                # Generic wait for page to load
                time.sleep(1)
            
            # Get the fully rendered page source
            self.page_content = self.driver.page_source
            print("Page loaded successfully!")
            
        except Exception as e:
            print(f"An error occurred while fetching the page: {e}")
            self.page_content = None

    def parse_page(self):
        """Parse the page content with BeautifulSoup"""
        if self.page_content is None:
            print("No page content to parse. Please fetch the page first.")
            return None
        
        soup = BeautifulSoup(self.page_content, 'html.parser')
        return soup

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")

    
if __name__ == "__main__":
    input_date = input("Enter the date (YYYY-MM-DD): ")
    date = input_date.strip()
    url = f"https://www.kijhl.ca/stats/daily-schedule/{date}?league=1&season=65&division=-1"
    
    scraper = WebScraper(url)
    
    try:
        # Fetch page and wait for the schedule element to load
        scraper.fetch_page(wait_for_class="ht-daily-sch-page")
        
        soup = scraper.parse_page()
        
        if soup is None:
            print("Failed to parse page")
            exit()
        
        # Now try to find the schedule
        schedule_div = soup.find('div', class_='ht-daily-sch-page').find('div', class_='ng-hide')
        
        if not schedule_div:
            print("Could not find schedule container")
            print("\nDebugging info:")
            print(f"Page content length: {len(scraper.page_content)}")
            print(f"'ht-daily-sch-page' in content: {'ht-daily-sch-page' in scraper.page_content}")
        else:
            print("Found schedule container!")
            
            # Find all game boxes
            game_boxes = schedule_div.find_all('div', class_='ht-sch-box')
            print(f"\nFound {len(game_boxes)} games\n")
            
            game_numbers = [i.get('id', 'N/A') for i in game_boxes]

            for game_number in game_numbers:
                scraper.driver.get(f"https://www.kijhl.ca/stats/game-center/{game_number}")
                time.sleep(1)
                scraper.page_content = scraper.driver.page_source
                soup = scraper.parse_page()
                teams = None
                
                if soup:
                    teams = soup.find_all('div', class_='ht-team-name')
                    teams = [team.text.strip() for team in teams]
                    score = soup.find('div', class_='ht-mobile-score-box')
                    score_text = score.text.strip() if score else "N/A"
                    print(f"Game {game_number}: {' vs '.join(teams)} - Score: {score_text}")

                pims_table = soup.find_all('table', class_='ht-table ht-table-no-overflow')[2].find('tbody').find_all('tr')
                if pims_table:
                    home_pims = pims_table[0].find_all('td')[2].find('span').text.split()[0]
                    away_pims = pims_table[1].find_all('td')[2].find('span').text.split()[0]

                    print(f"\t{teams[0]} PIMs: {home_pims}, {teams[1]} PIMs: {away_pims}")
                    print(f"\tTotal PIMs: {int(home_pims) + int(away_pims)}")
                else:
                    print(f"No PIMs table found for game {game_number}\n")
                    break
                

    finally:
        # Always close the browser
        scraper.close()
