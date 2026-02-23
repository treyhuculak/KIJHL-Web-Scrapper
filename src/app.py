from flask import Flask, render_template, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import DatabaseManager
from league_config import LEAGUES
import time
from datetime import datetime, date
import pytz
import os
from pathlib import Path 

# Import new API-based functions
from getgames import get_game_ids_by_date, fetch_game_api

app = Flask(__name__)
db_manager = DatabaseManager()

def get_logo_path(league: str, team_abbrev: str) -> str:
    """
    Get the path to a cached team logo.
    
    Args:
        league: League identifier (e.g., 'kijhl', 'whl')
        team_abbrev: Team abbreviation (e.g., 'CGY', 'EDM')
        
    Returns:
        Path to the logo file (e.g., 'static/logos/kijhl/CGY.png')
        Returns an empty string if logo file doesn't exist
    """
    logo_path = Path(__file__).parent / "static" / "logos" / league / f"{team_abbrev}.png"
    if logo_path.exists():
        return f"static/logos/{league}/{team_abbrev}.png"
    return ''

def get_season_id_by_date(date_str, league='kijhl'):
    """
    Determine the season ID based on the provided date and league.
    Uses season_start_dates and season_ids from league_config.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        league: League identifier (e.g., 'kijhl', 'whl')
    
    Returns:
        int: Season ID if found, 0 otherwise
    """
    league_config = LEAGUES.get(league)
    if not league_config:
        return 0
    
    season_start_dates = league_config['season_start_dates']
    season_ids = league_config['season_ids']
    
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    # Iterate most-recent-first (dict is already ordered that way in league_config)
    for season_name, start_date in season_start_dates.items():
        if date_obj >= datetime.strptime(start_date, '%Y-%m-%d'):
            return season_ids.get(season_name, 0)
    return 0

def scrape_games(date, league='kijhl'):
    """Retrieve game data for a given date using the API.
    
    Args:
        date: Date string in YYYY-MM-DD format
        league: League identifier (e.g., 'kijhl', 'whl')
    """
    # Validate league
    if league not in LEAGUES:
        return {
            'games': [],
            'errors': [f"Unknown league: {league}"],
            'total_games': 0,
            'elapsed_time': 0,
            'success': False,
            'jungle_score': 0,
            'dirty_team': ""
        }
    
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
        season_id = get_season_id_by_date(date, league=league)
        if not season_id:
            results['errors'].append("No season found for the given date")
            results['elapsed_time'] = time.time() - start_time
            return results

        game_numbers = get_game_ids_by_date(date, league=league, season_id=season_id)
        results['total_games'] = len(game_numbers)
        
        if not game_numbers:
            results['errors'].append("No games found for this date")
            results['elapsed_time'] = time.time() - start_time
            return results

        # 2. Fetch Game Details (Concurrently)
        max_workers = min(15, len(game_numbers))  # Reasonable limit for concurrent requests
        dirtiest_team_name = ""
        dirtiest_team_pims = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_game = {executor.submit(fetch_game_api, game_num, league): game_num 
                              for game_num in game_numbers}
            
            for future in as_completed(future_to_game):
                game_num, data, error = future.result()
                
                if error:
                    results['errors'].append({
                        'game_number': game_num,
                        'error': error
                    })
                elif data:
                    visitor_abbrv = data['teams']['visitor_abbrv']
                    home_abbrv = data['teams']['home_abbrv']
                    visitor_pims = int(data['pims']['visitor'])
                    home_pims = int(data['pims']['home'])

                    game_obj = {
                        'game_number': game_num,
                        'venue': data['game_details']['venue'],
                        'attendance': data['game_details']['attendance'],
                        'status': data['game_details']['status'],
                        'visitor_city': data['teams']['visitor_city'],
                        'home_city': data['teams']['home_city'],
                        'visitor_nickname': data['teams']['visitor_nickname'],
                        'home_nickname': data['teams']['home_nickname'],
                        'visitor_abbrv': visitor_abbrv,
                        'home_abbrv': home_abbrv,
                        'visitor_goals': data['goals']['visitor'],
                        'home_goals': data['goals']['home'],
                        'visitor_pims': visitor_pims,
                        'home_pims': home_pims,
                        'total_pims': visitor_pims + home_pims,
                        'fight_count': data['pims'].get('fight_count', 0),
                        'major_penalty_count': data['pims'].get('major_penalty_count', 0),
                        'notable_penalties': data['pims'].get('notable_penalties', []),
                        'referees': data['officials']['referees'],
                        'linesmen': data['officials']['linesmen'],
                        'visitor_logo': get_logo_path(league, visitor_abbrv),
                        'home_logo': get_logo_path(league, home_abbrv),
                        'date': date,
                        'league': league
                    }

                    results['games'].append(game_obj)

                    results['jungle_score'] += game_obj['total_pims']

                    # Calculate dirtiest team
                    max_pims_in_game = max(visitor_pims, home_pims)
                    if max_pims_in_game > dirtiest_team_pims:
                        dirtiest_team_name = visitor_abbrv if visitor_pims > home_pims else home_abbrv
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
    """Render the league selector page"""
    return render_template('league_selector.html')

@app.route('/games')
def games():
    """Render the games page (original index.html)"""
    league = request.args.get('league', 'kijhl')
    season = request.args.get('season', '65')
    
    # Validate league
    if league not in LEAGUES:
        return jsonify({'error': f'Invalid league: {league}'}), 400
    
    league_config = LEAGUES[league]
    return render_template('index.html', league=league, season=season, league_config=league_config)

@app.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

@app.route('/rosters')
def rosters():
    """Render the rosters page"""
    league = request.args.get('league', 'kijhl')
    season = request.args.get('season', '65')
    
    # Validate league
    if league not in LEAGUES:
        return jsonify({'error': f'Invalid league: {league}'}), 400
    
    league_config = LEAGUES[league]
    return render_template('rosters.html', league=league, season=season, league_config=league_config)

@app.route('/statistics')
def statistics():
    """Renders the statistics page. No filtering/sorting done server-side.
    All officials data is fetched client-side via /api/officials endpoint.
    
    Query parameters:
        league: League identifier (e.g., 'kijhl', 'whl'). Defaults to 'kijhl'
        season: Season ID. Defaults to '65'
    """
    league = request.args.get('league', 'kijhl')
    season = request.args.get('season', '65')
    
    # Validate league exists
    if league not in LEAGUES:
        return f"Invalid league: {league}", 400
    
    return render_template('leaderboard.html',
                           current_league=league,
                           current_season=season)

@app.route('/api/officials')
def get_officials():
    """API endpoint that returns all officials for a given season and league as JSON.
    Filtering and sorting is done client-side to minimize database reads.
    
    Query parameters:
        league: League identifier (e.g., 'kijhl', 'whl'). Defaults to 'kijhl'
        season: Season ID. Defaults to '65'
    """
    league = request.args.get('league', 'kijhl')
    season = request.args.get('season', '65')
    
    # Validate league exists
    if league not in LEAGUES:
        return jsonify({'error': 'Invalid league', 'officials': []}), 400
    
    # Fetch all officials for this season (no filtering/sorting)
    officials = db_manager.get_all_officials_for_season(league=league, season_id=int(season))
    
    return jsonify({
        'officials': officials,
        'season': season,
        'league': league,
        'count': len(officials)
    })

@app.route('/api/official/<name>')
def get_official_stats(name):
    """API endpoint to get career stats for a specific official across all seasons in a league.
    
    Query parameters:
        league: League identifier (e.g., 'kijhl', 'whl'). Defaults to 'kijhl'
    """
    league = request.args.get('league', 'kijhl')
    
    # Validate league exists
    if league not in LEAGUES:
        return jsonify({'error': 'Invalid league'}), 400
    
    stats = db_manager.get_official_career_stats(league, name)
    
    # Build season ID -> readable name mapping dynamically from league_config
    season_names = {}
    for league_key, league_cfg in LEAGUES.items():
        for season_label, sid in league_cfg['season_ids'].items():
            season_names[sid] = season_label
    
    # Add readable season names to each season record
    for season in stats.get('seasons', []):
        season_id = season.get('season_id', 0)
        season['season_name'] = season_names.get(season_id, f'Season {season_id}')
    
    return jsonify(stats)

@app.route('/api/scrape', methods=['GET', 'POST'])
def api_scrape():
    """API endpoint to scrape games for a given date and league.
    
    Query parameters (GET):
        date: Date string in YYYY-MM-DD format (required)
        league: League identifier (e.g., 'kijhl', 'whl'). Defaults to 'kijhl'
    
    Request body (POST with JSON):
        date: Date string in YYYY-MM-DD format (required)
        league: League identifier (e.g., 'kijhl', 'whl'). Defaults to 'kijhl'
    """
    # Handle both GET query parameters and POST JSON body
    if request.method == 'GET':
        date = request.args.get('date', '').strip()
        league = request.args.get('league', 'kijhl')
    else:
        data = request.get_json()
        date = data.get('date', '').strip()
        league = data.get('league', 'kijhl')
    
    if not date:
        return jsonify({'error': 'Date is required'}), 400
    
    # Validate league exists
    if league not in LEAGUES:
        return jsonify({'error': f'Unknown league: {league}'}), 400
    
    # Validate date format (YYYY-MM-DD)
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD'}), 400
    
    results = scrape_games(date, league=league)
    return jsonify(results)

@app.route('/tasks/update-daily', methods=['GET', 'POST'])
def daily_update():
    """Route specifically for Cloud Scheduler.
    Scrapes games for today's date for KIJHL (main league).
    
    Query parameter:
        league: League identifier (e.g., 'kijhl', 'whl'). Defaults to 'kijhl'
    """
    league = request.args.get('league', 'kijhl')
    
    # Validate league exists
    if league not in LEAGUES:
        return jsonify({'error': f'Unknown league: {league}'}), 400
    
    today = datetime.now(pytz.timezone('America/Vancouver')).date()
    date_str = today.strftime('%Y-%m-%d')
    
    print(f"Running automated update for {league}: {date_str}")
    
    results = scrape_games(date_str, league=league)

    if results['success'] and results['games']:
        print(f"   > Found {len(results['games'])} games. Saving...")
        season_id_actual = get_season_id_by_date(date_str, league=league)
        for game in results['games']:
            db_manager.save_game_results(league, game, season_id=season_id_actual)
    else:
        print("   > No games or error.")
    
    return jsonify({
        "status": "success", 
        "date": date_str,
        "league": league,
        "games_found": results['total_games']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True,host='0.0.0.0', port=port)