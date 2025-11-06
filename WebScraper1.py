from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import json
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
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)

    def fetch_page(self, wait_for_class=None, timeout=10):
        """Fetch page using Selenium and wait for JavaScript to load"""
        try:
            if self.driver is None:
                self.setup_driver()
            
            print(f"Loading page: {self.url}")
            self.driver.get(self.url)
            
            if wait_for_class:
                print(f"Waiting for element with class: {wait_for_class}")
                wait = WebDriverWait(self.driver, timeout)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, wait_for_class)))
            else:
                time.sleep(1)
            
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


def fetch_game_api(game_number):
    """Try to fetch game data from the API endpoint"""
    # The Angular app likely calls an API - this is a common pattern
    api_url = f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=gameSummary&game_id={game_number}&key=50c2cd9b5e18e390&client_code=kijhl&site_id=2&league_id=1&lang=en"
    
    try:
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract team info
            home_team = data.get('homeTeam', {}).get('name', 'Unknown')
            away_team = data.get('visitingTeam', {}).get('name', 'Unknown')
            
            # Extract score
            home_score = data.get('homeTeam', {}).get('score', '0')
            away_score = data.get('visitingTeam', {}).get('score', '0')
            score_text = f"{away_score} - {home_score}"
            
            # Extract PIMs
            home_pims = data.get('homeTeam', {}).get('stats', {}).get('penalties', {}).get('mins', '0')
            away_pims = data.get('visitingTeam', {}).get('stats', {}).get('penalties', {}).get('mins', '0')
            
            return game_number, {
                'teams': [away_team, home_team],
                'score': score_text,
                'home_pims': str(home_pims),
                'away_pims': str(away_pims),
                'total_pims': int(home_pims) + int(away_pims)
            }, None
            
    except Exception as e:
        return game_number, None, f"API fetch failed: {str(e)}"


if __name__ == "__main__":
    input_date = input("Enter the date (YYYY-MM-DD): ")
    date = input_date.strip()
    url = f"https://www.kijhl.ca/stats/daily-schedule/{date}?league=1&season=65&division=-1"
    
    scraper = WebScraper(url)
    
    try:
        # Fetch the main schedule page (still need Selenium for this)
        scraper.fetch_page(wait_for_class="ht-daily-sch-page")
        soup = scraper.parse_page()
        
        if soup is None:
            print("Failed to parse page")
            exit()
        
        # Find the schedule
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
            
            # Try API approach first
            print("Fetching game details via API (SUPER FAST)...\n")
            start_time = time.time()
            
            max_workers = min(20, len(game_numbers))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_game = {executor.submit(fetch_game_api, game_num): game_num 
                                  for game_num in game_numbers}
                
                for future in as_completed(future_to_game):
                    game_num, data, error = future.result()
                    
                    if error:
                        print(f"Game {game_num}: Error - {error}\n")
                    elif data:
                        print(f"Game {game_num}: {' vs '.join(data['teams'])} - Score: {data['score']}")
                        print(f"\t{data['teams'][1]} PIMs: {data['home_pims']}, {data['teams'][0]} PIMs: {data['away_pims']}")
                        print(f"\tTotal PIMs: {data['total_pims']}\n")
            
            elapsed_time = time.time() - start_time
            print(f"Total time: {elapsed_time:.2f} seconds")
            print(f"Average time per game: {elapsed_time/len(game_numbers):.2f} seconds")

    finally:
        scraper.close()