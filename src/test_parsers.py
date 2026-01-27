import json
import requests
from getgames import fetch_game_api, BASE_HEADERS, _load_jsonp
from league_config import LEAGUES

def test_raw_whl_response():
    """Debug: Check the raw WHL API response."""
    game_number_whl = 1022633
    config = LEAGUES.get('whl')
    url = config['base_url'].format(game_id=game_number_whl)
    
    print(f"URL: {url}\n")
    
    response = requests.get(url, headers=BASE_HEADERS.get('whl', {}), timeout=15)
    print(f"Status Code: {response.status_code}\n")
    
    # Try parsing with _load_jsonp
    data = _load_jsonp(response.text)
    
    # Print the full WHL Gamesummary structure
    gamesummary = data.get('GC', {}).get('Gamesummary', {})
    print("Full WHL Gamesummary structure:")
    print(json.dumps(gamesummary, indent=2))
    print("\n")

def test_parsers():
    """Test the parse_whl_game and parse_kijhl_game functions with real API data."""
    
    print("=" * 80)
    print("DEBUG: Raw WHL API Response")
    print("=" * 80)
    test_raw_whl_response()
    
    print("=" * 80)
    print("Testing WHL Parser with Real API Data")
    print("=" * 80)
    game_number_whl = 1022633
    game_num, stats, error = fetch_game_api(game_number_whl, 'whl')
    
    if error:
        print(f"❌ Error fetching WHL game {game_number_whl}: {error}")
    else:
        print(f"✓ Successfully fetched WHL game {game_number_whl}")
        print(json.dumps(stats, indent=2))
    
    print("\n" + "=" * 80)
    print("Testing KIJHL Parser with Real API Data")
    print("=" * 80)
    game_number_kijhl = 19059
    game_num, stats, error = fetch_game_api(game_number_kijhl, 'kijhl')
    
    if error:
        print(f"❌ Error fetching KIJHL game {game_number_kijhl}: {error}")
    else:
        print(f"✓ Successfully fetched KIJHL game {game_number_kijhl}")
        print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    test_parsers()
