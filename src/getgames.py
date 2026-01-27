import requests
import json
import re
from datetime import datetime
import logging
from league_config import LEAGUES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BASE_HEADERS = {
    'kijhl' : {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Referer': 'https://www.kijhl.ca/',
        'Accept': 'application/json, text/plain, */*'
    },
    'whl' : {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Referer': 'https://whl.ca/',
        'Accept': 'application/json, text/plain, */*'
    }
}

def _load_jsonp(text: str) -> dict:
    """Helper: Strip JSONP callback and return parsed JSON dict."""
    if not text:
        return {}
    try:
        # Match angular.callbacks pattern: angular.callbacks._N(...)
        match = re.search(r'angular\.callbacks\._\d+\((.*)\)', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        
        # Match jsonp pattern: jsonp_TIMESTAMP_NUM(...) used by WHL API
        match = re.search(r'jsonp_\d+_\d+\((.*)\)', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        
        # Fallback for simple parenthesis
        if text.startswith('(') and text.endswith(')'):
            return json.loads(text[1:-1])
            
        return json.loads(text)
    except Exception as e:
        logger.error(f"Error parsing JSONP: {e}")
        return {}

def get_game_ids_by_date_kijhl(date_str: str, season_id: int) -> list:
    """
    Fetches game IDs for KIJHL for a specific date (YYYY-MM-DD).
    """
    try:
        # Get league config
        config = LEAGUES.get('kijhl')
        if not config:
            logger.error("KIJHL league config not found")
            return []
        
        # Parse input date
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Format date for filtering (e.g., "Fri, Nov 7")
        # Remove zero-padding from day (e.g., 07 -> 7) to match API format
        day_val = dt.day
        formatted_date = dt.strftime(f"%a, %b {day_val}")

        # Construct URL dynamically based on month using league config
        url = (f"https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=schedule"
               f"&team=-1&season={season_id}&month={dt.month}&location=homeaway&key={config['api_key']}"
               f"&client_code={config['client_code']}&site_id=2&league_id=1&conference_id=-1&division_id=-1&lang=en"
               f"&callback=angular.callbacks._3")

        response = requests.get(url, headers=BASE_HEADERS.get('kijhl', {}), timeout=10)
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
        logger.error(f"Network error fetching KIJHL schedule: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching KIJHL schedule: {e}")
        return []

def get_game_ids_by_date_whl(date_str: str, season_id: int) -> list:
    """
    Fetches game IDs for WHL for a specific date (YYYY-MM-DD).
    """
    url = (f"https://lscluster.hockeytech.com/feed/?feed=modulekit&key=f1aa699db3d81487&view=gamesbydate"
           f"&fetch_date={date_str}&client_code=whl&lang_code=en&fmt=json&callback=jsonp_1769492720618_46885")
    
    response = requests.get(url, headers=BASE_HEADERS.get('whl', {}), timeout=10)
    response.raise_for_status()

    data = _load_jsonp(response.text)

    game_ids = []

    # Navigate JSON structure: data['Games']
    gamesbydate = data.get('SiteKit', {}).get('Gamesbydate', [])

    for game in gamesbydate:
        game_ids.append(game.get('id'))

    return game_ids

def get_game_ids_by_date(date_str, league, season_id=None) -> list:
    """
    Fetches game IDs for a specific date (YYYY-MM-DD).
    Dispatches to league-specific implementations.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        league: League identifier (e.g., 'kijhl', 'whl')
        season_id: Season ID for the league
    """
    # League-specific dispatchers
    LEAGUE_DISPATCHERS = {
        'kijhl': get_game_ids_by_date_kijhl,
        'whl': get_game_ids_by_date_whl,
    }
    
    # Validate league
    if league not in LEAGUES:
        logger.error(f"Unknown league: {league}")
        return []
    
    if season_id is None:
        logger.error(f"season_id is required")
        return []
    
    # Get the appropriate dispatcher function
    dispatcher = LEAGUE_DISPATCHERS.get(league)
    if not dispatcher:
        logger.error(f"No dispatcher found for league: {league}")
        return []
    
    # Call the league-specific function
    return dispatcher(date_str, season_id)

def parse_kijhl_game(data: dict) -> dict:
    """Parse KIJHL game data from API response."""
    # Implementation specific to KIJHL data structure

    # Helper to safely get referee/linesmen names
    def get_official_name(officials_list, index):
        if len(officials_list) > index:
            o = officials_list[index]
            return f"{o.get('firstName', 'Unknown').rstrip().title()} {o.get('lastName', 'Unknown').rstrip().title()}"
        return 'Unknown'

    referees = data.get('referees', [])
    linesmen = data.get('linesmen', [])

    # Extract Stats
    visiting = data.get('visitingTeam', {})
    home = data.get('homeTeam', {})

    stats = {
        'teams': {
            'visitor': visiting.get('info', {}).get('name', 'Unknown'),
            'home': home.get('info', {}).get('name', 'Unknown')
        },
        'teams_abbrv': {
            'visitor': visiting.get('info', {}).get('abbreviation', 'Unknown'),
            'home': home.get('info', {}).get('abbreviation', 'Unknown')
        },
        'goals': {
            'visitor': visiting.get('stats', {}).get('goals', 0),
            'home': home.get('stats', {}).get('goals', 0)
        },
        'pims': {
            'visitor': visiting.get('stats', {}).get('penaltyMinuteCount', 0),
            'home': home.get('stats', {}).get('penaltyMinuteCount', 0)
        },
        'officials': {
            'referees': [
                [get_official_name(referees, 0), '0'], [get_official_name(referees, 1), '0']
            ],
            'linesmen': [
                [get_official_name(linesmen, 0), '0'], [get_official_name(linesmen, 1), '0']
            ]
        }
    }

    return stats

def parse_whl_game(data: dict) -> dict:
    """Parse WHL game data from API response."""
    # Implementation specific to WHL data structure
    # WHL API returns nested structure under GC.Gamesummary
    gamesummary = data.get('GC', {}).get('Gamesummary', {})
    
    # Extract team info
    home_team = gamesummary.get('home', {})
    visitor_team = gamesummary.get('visitor', {})

    goals = gamesummary.get('totalGoals', {})
    pims = gamesummary.get('pimTotal', {})
    officials = gamesummary.get('officialsOnIce', [])
    referees = [['Unknown', '0'], ['Unknown', '0']]
    linesmen = [["Unknown", '0'], ["Unknown", '0']]

    for official in officials:
        name = f"{official.get('first_name', 'Unknown').rstrip().title()} {official.get('last_name', 'Unknown').rstrip().title()}"

        if "Referee" in official.get("description", ""):
            referees.pop(0)
            referees.append([name, official.get('jersey_number', '0')])
        elif "Linesman" in official.get("description", ""):
            linesmen.pop(0)
            linesmen.append([name, official.get('jersey_number', '0')])
    
    stats = {
        'teams': {
            'visitor': visitor_team.get('name', 'Unknown'),
            'home': home_team.get('name', 'Unknown')
        },
        'teams_abbrv': {
            'visitor': visitor_team.get('team_code', 'Unknown'),
            'home': home_team.get('team_code', 'Unknown')
        },
        'goals': {
            'visitor': goals.get('visitor', 'Unknown'),
            'home': goals.get('home', 'Unknown')
        },
        'pims': {
            'visitor': pims.get('visitor', 0),
            'home': pims.get('home', 0)
        },
        'officials': {
            'referees': referees,
            'linesmen': linesmen,
        }
    }

    return stats

def fetch_game_api(game_number, league):
    """Fetch detailed game stats.
    
    Args:
        game_number: The game ID to fetch
        league: League identifier (e.g., 'kijhl', 'whl')
    """
    # Get league config
    config = LEAGUES.get(league)

    # League-specific parser mapping
    LEAGUE_DISPATCHERS = {
        'kijhl': parse_kijhl_game,
        'whl': parse_whl_game,
    }
    
    if not config:
        logger.error(f"Unknown league: {league}")
        return game_number, None, f"Unknown league: {league}"
    
    url = (config['base_url'].format(game_id=game_number))

    try:
        response = requests.get(url, headers=BASE_HEADERS.get(league, {}), timeout=15)
        response.raise_for_status()
        data = _load_jsonp(response.text)
        
        if not data:
            return game_number, None, "Empty response"
        
        parser = LEAGUE_DISPATCHERS.get(league)
        if not parser:
            return game_number, None, f"No parser for league: {league}"

        stats = parser(data)

        return game_number, stats, None
            
    except Exception as e:
        return game_number, None, f"{type(e).__name__}: {str(e)}"