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

    def get_leaderboard(self, role='all', sort_by='total_pims', order='desc', season_id=65, games_called_threshold=5):
        """
        Fetches filtered and sorted leaderboard.
        Now filters games_called in Python to avoid needing a new index.
        """
        query = self.db.collection('officials').where('season_id', '==', season_id)

        # Apply Role Filter
        if role != 'all':
            query = query.where('role', '==', role)

        # Apply Sorting
        direction = 'DESCENDING' if order == 'desc' else 'ASCENDING'
        
        # Firestore Requirement: You might need to create an index in the Firebase Console
        # for these specific combinations of where() and order_by()
        query = query.order_by(sort_by, direction=direction)

        docs = query.stream()
        
        # Post-query filtering in Python
        results = [doc.to_dict() for doc in docs]
        
        if games_called_threshold > 0:
            results = [r for r in results if r.get('games_called', 0) >= games_called_threshold]
            
        return results