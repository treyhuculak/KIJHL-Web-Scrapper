"""
Daily update scaffolding.

This script will be scheduled to run daily and pull the most recent games,
then update the database. For now, it only prints which date it would run for.
"""
from datetime import datetime, timedelta


def run_daily_for(date_str: str) -> None:
    """
    Placeholder: run a daily update for the provided date (YYYY-MM-DD).
    Later this will:
      - fetch that date's games
      - insert into DB and link referees
    """
    print(f"[DailyUpdate] Would process games for: {date_str}")


if __name__ == "__main__":
    today_local = datetime.now().date()
    yday = (today_local - timedelta(days=1)).strftime("%Y-%m-%d")
    run_daily_for(yday)


