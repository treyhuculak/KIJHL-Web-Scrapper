from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

# Import new API-based functions
from getgames import get_game_ids_by_date, fetch_game_api, fetch_team_logos

app = Flask(__name__)

def scrape_games(date):
    """
    Retrieve game data for a given date using the API.
    """
    results = {
        'games': [],
        'errors': [],
        'total_games': 0,
        'elapsed_time': 0,
        'success': False,
        'jungle_score': 0,
        'dirty_team': ""
    }
    
    start_time = time.time()
    
    try:
        # 1. Fetch Game IDs directly from API (Replaces Selenium/BS4)
        # Note: Season 65 is hardcoded in getgames defaults, can be passed if needed
        game_numbers = get_game_ids_by_date(date)
        results['total_games'] = len(game_numbers)
        
        if not game_numbers:
            results['errors'].append("No games found for this date")
            results['elapsed_time'] = time.time() - start_time
            return results

        # 2. Fetch Logos (Once per request, or could be cached globally)
        logo_map = fetch_team_logos()
        
        # 3. Fetch Game Details (Concurrently)
        max_workers = min(20, len(game_numbers))
        dirtiest_team_name = ""
        dirtiest_team_pims = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_game = {executor.submit(fetch_game_api, game_num): game_num 
                              for game_num in game_numbers}
            
            for future in as_completed(future_to_game):
                game_num, data, error = future.result()
                
                if error:
                    results['errors'].append({
                        'game_number': game_num,
                        'error': error
                    })
                elif data:
                    away_abbrv = data['teams_abbrv'][0]
                    home_abbrv = data['teams_abbrv'][1]
                    away_pims = int(data['away_pims'])
                    home_pims = int(data['home_pims'])

                    results['games'].append({
                        'game_number': game_num,
                        'away_team': data['teams'][0],
                        'home_team': data['teams'][1],
                        'away_abbrv': away_abbrv,
                        'home_abbrv': home_abbrv,
                        'score': data['score'],
                        'away_pims': data['away_pims'],
                        'home_pims': data['home_pims'],
                        'total_pims': data['total_pims'],
                        'referees': data['referees'],
                        'linesmen': data['linesmen'],
                        'away_logo': logo_map.get(away_abbrv),
                        'home_logo': logo_map.get(home_abbrv)
                    })
                    results['jungle_score'] += data['total_pims']

                    # Calculate dirtiest team
                    max_pims_in_game = max(away_pims, home_pims)
                    if max_pims_in_game > dirtiest_team_pims:
                        dirtiest_team_name = away_abbrv if away_pims > home_pims else home_abbrv
                        dirtiest_team_pims = max_pims_in_game
        
        # 4. Final Calculations
        if results['total_games'] > 0:
            results['jungle_score'] = round(results['jungle_score'] / results['total_games'], 1)
        
        results['dirty_team'] = dirtiest_team_name
        results['success'] = True
        
    except Exception as e:
        results['errors'].append(f"An application error occurred: {str(e)}")
    
    results['elapsed_time'] = time.time() - start_time
    return results

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint to scrape games for a given date"""
    data = request.get_json()
    date = data.get('date', '').strip()
    
    if not date:
        return jsonify({'error': 'Date is required'}), 400
    
    # Validate date format (YYYY-MM-DD)
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD'}), 400
    
    results = scrape_games(date)
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)