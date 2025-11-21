import requests
import json
import re

def get_game_ids_by_date(url, target_date):
    """
    Fetches KIJHL schedule data, parses the JSONP response, and extracts 
    the game IDs for all games occurring on the specified date.

    Args:
        url (str): The API URL providing the JSONP data.
        target_date (str): The date string to match (e.g., "Sat, Nov 1").

    Returns:
        list: A list of game_id strings for the target date.
    """
    try:
        # 1. Fetch the data from the API
        response = requests.get(url)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        jsonp_data = response.text

        # 2. Extract the raw JSON string from the JSONP function call
        # The regex finds content inside the first parenthesis, ignoring the "angular.callbacks._X(...)" wrapper.
        match = re.search(r'angular\.callbacks\._\d+\((.*)\)', jsonp_data, re.DOTALL)
        if not match:
            print("Error: Could not extract JSON object from JSONP data.")
            return []
            
        json_str = match.group(1)

        # 3. Parse the JSON string
        data = json.loads(json_str)

        # 4. Navigate the structure and filter games
        game_ids = []
        
        # The relevant game list is nested deeply: data[0]['sections'][0]['data']
        if data and data[0].get('sections'):
            games_data = data[0]['sections'][0].get('data', [])
        else:
            print("Error: JSON structure is unexpected.")
            return []

        for game in games_data:
            row = game.get('row', {})
            date_with_day = row.get('date_with_day')
            game_id = row.get('game_id')

            if date_with_day == target_date and game_id:
                game_ids.append(game_id)
        
        return game_ids

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

# --- Configuration ---
API_URL = "https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=schedule&team=-1&season=65&month=11&location=homeaway&key=2589e0f644b1bb71&client_code=kijhl&site_id=2&league_id=1&conference_id=-1&division_id=-1&lang=en&callback=angular.callbacks._3"
TARGET_DATE = "Fri, Nov 7" # Example: Change this to the date you want to check

# --- Execution ---
print(f"🏒 Fetching Game IDs for date: **{TARGET_DATE}**")
game_ids_list = get_game_ids_by_date(API_URL, TARGET_DATE)
game_ids_list2 = get_game_ids_by_date(API_URL, "Sat, Nov 8")

if game_ids_list:
    print("\n✅ Extracted Game IDs:")
    for game_id in game_ids_list:
        print(f"- {game_id}")
    print(f"\nTotal games found: **{len(game_ids_list)}**")
    for game_id in game_ids_list2:
        print(f"- {game_id}")
    print(f"\nTotal games found: **{len(game_ids_list2)}**")
    
else:
    print("\n⚠️ No Game IDs found for the specified date, or an error occurred.")