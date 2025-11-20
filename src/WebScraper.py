from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
import json
import time

def _load_jsonp(text: str) -> dict:
    """Strip JSONP callback and return parsed JSON dict."""
    if not text:
        return {}
    if 'angular.callbacks.' in text:
        start = text.index('(') + 1
        end = text.rindex(')')
        json_text = text[start:end]
    elif text.startswith('(') and text.endswith(')'):
        json_text = text[1:-1]
    else:
        json_text = text
    try:
        return json.loads(json_text)
    except Exception:
        return {}

def fetch_team_logos(season_id: int = 65) -> dict:
    """
    Fetch team metadata for a season and return a map:
    { team_code (abbrv) -> logo_url }
    """
    url = f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=teamsForSeason&season={season_id}&key=2589e0f644b1bb71&client_code=kijhl&site_id=2&callback=angular.callbacks._6"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Referer': 'https://www.kijhl.ca/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()  # Raise an exception for bad status codes
    text = response.text
    data = _load_jsonp(text)
    logos = {}
    # prefer teamsNoAll if present (excludes "All Teams")
    teams_list = data.get('teamsNoAll') or data.get('teams') or []
    for t in teams_list:
        code = t.get('team_code')
        logo = t.get('logo')
        if code and logo:
            logos[code] = logo
    return logos

class WebScraper:
    def __init__(self, url):
        self.url = url
        self.page_content = None
        self.driver = None

    def set_url(self, url):
        self.url = url

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
            self.driver.get(self.url) # type: ignore
            
            if wait_for_class:
                print(f"Waiting for element with class: {wait_for_class}")
                wait = WebDriverWait(self.driver, timeout) # type: ignore
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, wait_for_class)))
            else:
                time.sleep(1)
            
            self.page_content = self.driver.page_source # type: ignore
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
    """Fetch game data from the HockeyTech gameSummary API"""
    game_api_url = f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=gameSummary&game_id={game_number}&key=2589e0f644b1bb71&site_id=2&client_code=kijhl&lang=en&league_id="
    team_info_api = "https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=teamsForSeason&season=65&key=2589e0f644b1bb71&client_code=kijhl&site_id=2&callback=angular.callbacks._6"


    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
            'Referer': 'https://www.kijhl.ca/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }
        response = requests.get(game_api_url, headers=headers, timeout=15)
        response.raise_for_status()
        text = response.text
            
        if not text or len(text) < 10:
            return game_number, None, f"Empty response"
        
        # Remove JSONP callback: angular.callbacks._4({...})
        if 'angular.callbacks.' in text:
            start = text.index('(') + 1
            end = text.rindex(')')
            json_text = text[start:end]
        elif text.startswith('(') and text.endswith(')'):
            json_text = text[1:-1]
        else:
            json_text = text
        
        data = json.loads(json_text)

        # Extract Referees
        referees_list = data.get('referees', [])
        referee1_name = 'Unknown'
        referee2_name = 'Unknown'
        
        if len(referees_list) > 0:
            referee1 = referees_list[0]
            referee1_name = f"{referee1.get('firstName', 'Unknown')} {referee1.get('lastName', 'Unknown')}"
        
        if len(referees_list) > 1:
            referee2 = referees_list[1]
            referee2_name = f"{referee2.get('firstName', 'Unknown')} {referee2.get('lastName', 'Unknown')}"

        # Extract Linesmen
        linesmen_list = data.get('linesmen', [])
        linesman1_name = 'Unknown'
        linesman2_name = 'Unknown'
        
        if len(linesmen_list) > 0:
            linesman1 = linesmen_list[0]
            linesman1_name = f"{linesman1.get('firstName', 'Unknown')} {linesman1.get('lastName', 'Unknown')}"
        
        if len(linesmen_list) > 1:
            linesman2 = linesmen_list[1]
            linesman2_name = f"{linesman2.get('firstName', 'Unknown')} {linesman2.get('lastName', 'Unknown')}"

        # Extract team names
        away_team = data.get('visitingTeam', {}).get('info', {}).get('name', 'Unknown')
        home_team = data.get('homeTeam', {}).get('info', {}).get('name', 'Unknown')

        # Extract team abbreviations
        away_abbrv = data.get('visitingTeam', {}).get('info', {}).get('abbreviation', 'Unknown')
        home_abbrv = data.get('homeTeam', {}).get('info', {}).get('abbreviation', 'Unknown')
        
        # Extract scores
        away_score = data.get('visitingTeam', {}).get('stats', {}).get('goals', 0)
        home_score = data.get('homeTeam', {}).get('stats', {}).get('goals', 0)
        score_text = f"{away_score} - {home_score}"
        
        # Extract PIMs
        away_pims = data.get('visitingTeam', {}).get('stats', {}).get('penaltyMinuteCount', 0)
        home_pims = data.get('homeTeam', {}).get('stats', {}).get('penaltyMinuteCount', 0)
        
        return game_number, {
                'teams': [away_team, home_team],
                'teams_abbrv': [away_abbrv, home_abbrv],
                'score': score_text,
                'home_pims': str(home_pims),
                'away_pims': str(away_pims),
                'total_pims': int(home_pims) + int(away_pims),
                'referees': [referee1_name, referee2_name],
                'linesmen': [linesman1_name, linesman2_name]
            }, None
            
    except Exception as e:
        return game_number, None, f"{type(e).__name__}: {str(e)}"

