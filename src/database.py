import firebase_admin
from firebase_admin import credentials, firestore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def game_exists(self, game_id):
        doc = self.db.collection('games').document(str(game_id)).get()
        return doc.exists

    def save_game_results(self, game_data, season_id=65):
        game_id = str(game_data['game_number'])
        
        if self.game_exists(game_id):
            logger.info(f"Game {game_id} already exists. Skipping.")
            return False

        # Save Game
        game_data['season_id'] = season_id # Add season ID to game data
        self.db.collection('games').document(game_id).set(game_data)

        # Process Officials
        officials = []
        for ref_name in game_data.get('referees', []):
            if ref_name and ref_name.strip() not in ["Unknown", "Unknown Unknown"]:
                officials.append({'name': ref_name.strip(), 'type': 'referee'})
        for line_name in game_data.get('linesmen', []):
            if line_name and line_name.strip() not in ["Unknown", "Unknown Unknown"]:
                officials.append({'name': line_name.strip(), 'type': 'linesman'})

        batch = self.db.batch()
        
        for official in officials:
            # KEY CHANGE: Composite ID (Name + Season) to separate stats per season
            # ID example: "Steve_Smith_65"
            doc_id = f"{official['name'].replace(' ', '_')}_{season_id}"
            ref_ref = self.db.collection('officials').document(doc_id)
            
            doc = ref_ref.get()
            
            if doc.exists:
                current_data = doc.to_dict()
                new_games = current_data.get('games_called', 0) + 1 # type: ignore
                new_pims = current_data.get('total_pims', 0) + int(game_data['total_pims']) # type: ignore
            else:
                new_games = 1
                new_pims = int(game_data['total_pims'])

            batch.set(ref_ref, {
                'name': official['name'],
                'role': official['type'],
                'season_id': season_id, # Store season ID
                'games_called': new_games,
                'total_pims': new_pims,
                'avg_pims': round(new_pims / new_games, 1)
            }, merge=True)

        batch.commit()
        return True

    def get_all_officials_for_season(self, season_id=65):
        """
        Fetches ALL officials for a given season without any filtering or sorting.
        Filtering and sorting will be done client-side to reduce database reads.
        
        FUTURE: To support multiple leagues, add a league_id parameter and query:
                .where('season_id', '==', season_id).where('league_id', '==', league_id)
        """
        query = self.db.collection('officials').where('season_id', '==', season_id)
        docs = query.stream()
        
        # Return all officials as-is
        results = [doc.to_dict() for doc in docs]
        return results
    
    # DEPRECATED: Kept for backwards compatibility if needed
    def get_leaderboard(self, role='all', sort_by='total_pims', order='desc', season_id=65, games_called_threshold=5):
        """
        DEPRECATED: Use get_all_officials_for_season() and filter/sort client-side instead.
        This method still works but performs filtering on the server, causing more database reads.
        """
        query = self.db.collection('officials').where('season_id', '==', season_id)

        # Apply Role Filter
        if role != 'all':
            query = query.where('role', '==', role)

        # Apply Sorting
        direction = 'DESCENDING' if order == 'desc' else 'ASCENDING'
        query = query.order_by(sort_by, direction=direction)

        docs = query.stream()
        
        # Post-query filtering in Python
        results = [doc.to_dict() for doc in docs]
        
        if games_called_threshold > 0:
            results = [r for r in results if r.get('games_called', 0) >= games_called_threshold]
            
        return results

    def get_official_career_stats(self, official_name):
        """
        Fetches all season records for a specific official to build career stats.
        Returns a list of season stats and calculated career totals.
        """
        query = self.db.collection('officials').where('name', '==', official_name)
        docs = query.stream()
        
        seasons = []
        for doc in docs:
            data = doc.to_dict()
            seasons.append(data)
        
        # Sort by season_id descending (most recent first)
        seasons.sort(key=lambda x: x.get('season_id', 0), reverse=True)
        
        # Calculate career totals
        career_totals = {
            'total_games': sum(s.get('games_called', 0) for s in seasons),
            'total_pims': sum(s.get('total_pims', 0) for s in seasons),
            'seasons_count': len(seasons)
        }
        
        if career_totals['total_games'] > 0:
            career_totals['career_avg'] = int(round(career_totals['total_pims'] / career_totals['total_games'], 1))
        else:
            career_totals['career_avg'] = 0
        
        return {
            'name': official_name,
            'seasons': seasons,
            'career': career_totals
        }