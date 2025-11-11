"""
Backfill scaffolding.

This script will populate the database with historical seasons.
For now, it only accepts a list of season IDs (to be provided later)
and prints what it would process without actually scraping.
"""
from typing import List

from scraper.web_scraper import fetch_game_api, WebScraper  # future use


def backfill_seasons(season_ids: List[int]) -> None:
    """
    Placeholder: backfill by season.
    Later this will:
      - iterate dates or game lists for each season
      - fetch games and insert them into the DB
    """
    for sid in season_ids:
        print(f"[Backfill] Would process season: {sid}")


if __name__ == "__main__":
    # Example usage (replace with your season list later)
    example_seasons = []
    if not example_seasons:
        print("No seasons provided yet. Supply a list of season IDs when ready.")
    else:
        backfill_seasons(example_seasons)


