import requests
import json
import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    'Referer': 'https://www.kijhl.ca/',
    'Accept': 'application/json, text/plain, */*',
}

def _load_jsonp(text: str) -> dict:
    """Helper: Strip JSONP callback and return parsed JSON dict."""
    if not text:
        return {}
    try:
        # Regex to capture content between first ( and last )
        match = re.search(r'angular\.callbacks\._\d+\((.*)\)', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        
        # Fallback for simple parenthesis
        if text.startswith('(') and text.endswith(')'):
            return json.loads(text[1:-1])
            
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error parsing JSONP: {e}")
        return {}

def get_game_ids_by_date(date_str: str, season_id: int = 65) -> list:
    """
    Fetches game IDs for a specific date (YYYY-MM-DD).
    """
    try:
        # Parse input date
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        
        # 1. Format date for filtering (e.g., "Fri, Nov 7")
        # We remove zero-padding from day (e.g., 07 -> 7) to match API format
        day_val = dt.day
        formatted_date = dt.strftime(f"%a, %b {day_val}")

        # 2. Construct URL dynamically based on month
        # month in API seems to be 1-12. 
        url = (f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=schedule"
               f"&team=-1&season={season_id}&month={dt.month}&location=homeaway&key=2589e0f644b1bb71"
               f"&client_code=kijhl&site_id=2&league_id=1&conference_id=-1&division_id=-1&lang=en"
               f"&callback=angular.callbacks._3")

        response = requests.get(url, headers=BASE_HEADERS, timeout=10)
        response.raise_for_status()
        
        data = _load_jsonp(response.text)
        
        game_ids = []
        
        # Navigate JSON structure: [0]['sections'][0]['data']
        if data and isinstance(data, list) and data[0].get('sections'):
            games_data = data[0]['sections'][0].get('data', [])
            for game in games_data:
                row = game.get('row', {})
                # Match the formatted date string
                if row.get('date_with_day') == formatted_date:
                    if 'game_id' in row:
                        game_ids.append(row['game_id'])
        
        return game_ids

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching schedule: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching schedule: {e}")
        return []

def fetch_team_logos(season_id: int = 65) -> dict:
    """Fetch team metadata and return map { abbrv -> logo_url }"""
    url = (f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=teamsForSeason"
           f"&season={season_id}&key=2589e0f644b1bb71&client_code=kijhl&site_id=2"
           f"&callback=angular.callbacks._6")
    
    try:
        response = requests.get(url, headers=BASE_HEADERS, timeout=15)
        response.raise_for_status()
        data = _load_jsonp(response.text)
        
        logos = {}
        teams_list = data.get('teamsNoAll') or data.get('teams') or []
        for t in teams_list:
            code = t.get('team_code')
            logo = t.get('logo')
            if code and logo:
                logos[code] = logo
        return logos
    except Exception as e:
        logger.error(f"Error fetching logos: {e}")
        return {}

def fetch_game_api(game_number):
    """Fetch detailed game stats."""
    url = (f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=gameSummary"
           f"&game_id={game_number}&key=2589e0f644b1bb71&site_id=2&client_code=kijhl&lang=en"
           f"&league_id=")

    try:
        response = requests.get(url, headers=BASE_HEADERS, timeout=15)
        response.raise_for_status()
        data = _load_jsonp(response.text)
        
        if not data:
            return game_number, None, "Empty response"

        # Helper to safely get referee/linesmen names
        def get_official_name(officials_list, index):
            if len(officials_list) > index:
                o = officials_list[index]
                return f"{o.get('firstName', 'Unknown')} {o.get('lastName', 'Unknown')}"
            return 'Unknown'

        referees = data.get('referees', [])
        linesmen = data.get('linesmen', [])

        # Extract Stats
        visiting = data.get('visitingTeam', {})
        home = data.get('homeTeam', {})
        
        away_pims = visiting.get('stats', {}).get('penaltyMinuteCount', 0)
        home_pims = home.get('stats', {}).get('penaltyMinuteCount', 0)

        stats = {
            'teams': [
                visiting.get('info', {}).get('name', 'Unknown'),
                home.get('info', {}).get('name', 'Unknown')
            ],
            'teams_abbrv': [
                visiting.get('info', {}).get('abbreviation', 'Unknown'),
                home.get('info', {}).get('abbreviation', 'Unknown')
            ],
            'score': f"{visiting.get('stats', {}).get('goals', 0)} - {home.get('stats', {}).get('goals', 0)}",
            'home_pims': str(home_pims),
            'away_pims': str(away_pims),
            'total_pims': int(home_pims) + int(away_pims),
            'referees': [get_official_name(referees, 0), get_official_name(referees, 1)],
            'linesmen': [get_official_name(linesmen, 0), get_official_name(linesmen, 1)]
        }
        return game_number, stats, None
            
    except Exception as e:
        return game_number, None, f"{type(e).__name__}: {str(e)}"