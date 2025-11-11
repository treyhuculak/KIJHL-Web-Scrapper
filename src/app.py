from flask import Flask, render_template, request, jsonify
from WebScraper import WebScraper, fetch_game_api, fetch_team_logos
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

app = Flask(__name__)

def scrape_games(date):
    """Scrape games for a given date and return results"""
    url = f"https://www.kijhl.ca/stats/daily-schedule/{date}?league=1&season=65&division=-1"
    
    scraper = WebScraper(url)
    results = {
        'games': [],
        'errors': [],
        'total_games': 0,
        'elapsed_time': 0,
        'success': False
    }
    
    try:
        # Fetch the main schedule page
        scraper.fetch_page(wait_for_class="ht-daily-sch-page")
        soup = scraper.parse_page()
        
        if soup is None:
            results['errors'].append("Failed to parse page")
            return results
        
        # Find the schedule
        schedule_div = soup.find('div', class_='ht-daily-sch-page')
        if schedule_div:
            schedule_div = schedule_div.find('div', class_='ng-hide')
        
        if not schedule_div:
            results['errors'].append("Could not find schedule container")
            return results
        
        # Find all game boxes
        game_boxes = schedule_div.find_all('div', class_='ht-sch-box')
        game_numbers = [box.get('id', 'N/A') for box in game_boxes]
        results['total_games'] = len(game_numbers)
        
        if len(game_numbers) == 0:
            results['errors'].append("No games found for this date")
            return results
        
        # Load team logos once for the season (65 is currently used in URL)
        logo_map = {}
        try:
            logo_map = fetch_team_logos(65)
        except Exception:
            logo_map = {}
        
        # Fetch game details via API
        start_time = time.time()
        max_workers = min(20, len(game_numbers))
        
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
        
        results['elapsed_time'] = time.time() - start_time
        results['success'] = True
        
    except Exception as e:
        results['errors'].append(f"An error occurred: {str(e)}")
    finally:
        scraper.close()
    
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
        time.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD'}), 400
    
    results = scrape_games(date)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

