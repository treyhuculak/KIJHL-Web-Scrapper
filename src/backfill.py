"""
Backfill scaffolding.

This script will populate the database with historical seasons.
For now, it only accepts a list of season IDs (to be provided later)
and prints what it would process without actually scraping.
"""
from typing import List
import pandas as pd

def backfill_seasons() -> None:
    """
    Placeholder: backfill by season.
    Later this will:
      - iterate dates or game lists for each season
      - fetch games and insert them into the DB
    """
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    for year in years:
        for date in pd.date_range(f'{year}-01-01', f'{year}-12-31'):
            # date.strftime('%Y-%m-%d') -> WebScraper()
            continue


if __name__ == "__main__":
    backfill_seasons()


