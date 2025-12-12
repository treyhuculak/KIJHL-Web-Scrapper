from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import DatabaseManager
import time
from datetime import datetime, date
import pytz
import os

# gcloud builds submit --tag us-west1-docker.pkg.dev/kijhl-app/kijhl-app-repo/kijhl-img:v4.2

# Import new API-based functions
from getgames import get_game_ids_by_date, fetch_game_api, fetch_team_logos

app = Flask(__name__)
db_manager = DatabaseManager()

def get_season_id_by_date(date_str):
    """
    Determine the season ID based on the provided date.
    This is a placeholder function and should be implemented
    based on actual season date ranges.
    """
    season_start_dates = {
        '2025-2026 (Playoffs)'  : ['2026-02-19', 66],
        '2025-2026 (Reg Season)': ['2025-09-19', 65],
        '2024-2025 (Playoffs)'  : ['2025-02-28', 63],
        '2024-2025 (Reg Season)': ['2024-09-20', 61],
        '2023-2024 (Playoffs)'  : ['2024-02-23', 59],
        '2023-2024 (Reg Season)': ['2023-09-22', 56],
        '2022-2023 (Playoffs)'  : ['2023-02-17', 54],
        '2022-2023 (Reg Season)': ['2022-09-23', 52],
        '2021-2022 (Playoffs)'  : ['2022-02-22', 51],
        '2021-2022 (Reg Season)': ['2021-10-01', 49]
    }
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    for season, (start_date, season_id) in season_start_dates.items():
        if date_obj >= datetime.strptime(start_date, '%Y-%m-%d'):
            return season_id
    return 0

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
        # 1. Fetch Game IDs directly from API
        season_id = get_season_id_by_date(date)
        if not season_id:
            results['errors'].append("No season found for the given date")
            results['elapsed_time'] = time.time() - start_time
            return results

        game_numbers = get_game_ids_by_date(date, season_id=season_id)
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

                    game_obj = {
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
                        'home_logo': logo_map.get(home_abbrv),
                        'date': date # Good to add the date to the saved object
                    }

                    results['games'].append(game_obj)

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

@app.route('/leaderboard')
def leaderboard():
    # Get filter params from URL (e.g., ?role=referee&sort=avg)
    role = request.args.get('role', 'all')
    sort = request.args.get('sort', 'pims') # 'pims' or 'avg'
    order = request.args.get('order', 'desc') # 'desc' or 'asc'
    season = request.args.get('season', '65') # Default to '65' if not provided
    games_called = request.args.get('games_called', 5, type=int) # Default to 5
    
    # Map frontend simple names to DB field names
    sort_map = {
        'pims': 'total_pims',
        'avg': 'avg_pims',
        'games': 'games_called'
    }
    sort_field = sort_map.get(sort, 'total_pims')
    
    officials = db_manager.get_leaderboard(
        role=role,
        sort_by=sort_field,
        order=order,
        season_id=int(season),
        games_called_threshold=games_called
    )
    
    # Determine the next order for the links in the template
    next_order = 'asc' if order == 'desc' else 'desc'
    
    return render_template('leaderboard.html',
                           officials=officials,
                           current_role=role,
                           current_sort=sort,
                           current_order=order,
                           next_order=next_order,
                           current_season=season,
                           current_games_called=games_called)

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

@app.route('/tasks/update-daily', methods=['GET', 'POST'])
def daily_update():
    """
    Route specifically for Cloud Scheduler.
    Scrapes games for todays date.
    """
    today = datetime.now(pytz.timezone('America/Vancouver')).date()
    date_str = today.strftime('%Y-%m-%d')
    
    print(f"Running automated update for: {date_str}")
    
    results = scrape_games(date_str)

    if results['success'] and results['games']:
        print(f"   > Found {len(results['games'])} games. Saving...")
        season_id_actual = get_season_id_by_date(date_str)
        for game in results['games']:
            db_manager.save_game_results(game, season_id=season_id_actual)
    else:
        print("   > No games or error.")
    
    return jsonify({
        "status": "success", 
        "date": date_str,
        "games_found": results['total_games']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True,host='0.0.0.0', port=port)