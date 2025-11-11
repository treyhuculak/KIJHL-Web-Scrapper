# Referee PIMs Tracking System

## Overview
Build a database system to track referee PIMs/game statistics with support for season-based and date-range queries, initial historical backfill, and daily updates.

## Database Schema

### Tables:
1. **games** - Store game data
   - `game_id` (PRIMARY KEY) - Game number from API
   - `game_date` (DATE) - Date of the game
   - `season_id` (INTEGER) - Season identifier
   - `away_team` (TEXT)
   - `home_team` (TEXT)
   - `total_pims` (INTEGER) - Total PIMs for the game
   - `created_at` (TIMESTAMP)

2. **referees** - Store referee information
   - `referee_id` (PRIMARY KEY, AUTO_INCREMENT)
   - `first_name` (TEXT)
   - `last_name` (TEXT)
   - `full_name` (TEXT, UNIQUE) - For quick lookups
   - `created_at` (TIMESTAMP)

3. **game_referees** - Junction table linking games to referees
   - `id` (PRIMARY KEY, AUTO_INCREMENT)
   - `game_id` (FOREIGN KEY -> games.game_id)
   - `referee_id` (FOREIGN KEY -> referees.referee_id)
   - `created_at` (TIMESTAMP)

4. **seasons** - Store season information
   - `season_id` (PRIMARY KEY)
   - `season_name` (TEXT) - e.g., "2023-2024"
   - `start_date` (DATE)
   - `end_date` (DATE)

## Implementation Files

### New Files:
- `database.py` - Database connection and schema management
- `referee_stats.py` - Functions to calculate and query referee statistics
- `backfill.py` - Script to backfill historical data (10 years)
- `daily_update.py` - Script for daily updates (can be scheduled via cron/task scheduler)

### Modified Files:
- `app.py` - Add database integration and new API endpoints
- `WebScraper.py` - Extract game date and season from API responses
- `templates/index.html` - Add UI for referee statistics queries
- `requirements.txt` - Add MySQL database driver (mysql-connector-python or pymysql)

## Key Features

### 1. Database Integration
- Use MySQL for hosting compatibility
- Create schema with proper indexes for performance
- Add functions for inserting/updating game and referee data
- Filter out pre-season games to avoid unnecessary data

### 2. Enhanced Scraping
- Modify `fetch_game_api()` to extract game date and season from API response
- Store game data in database after scraping
- Handle duplicate games (skip if already exists)

### 3. Referee Statistics Calculation
- Calculate PIMs/game = total PIMs from all games officiated / number of games
- Support queries by:
  - Season (using season_id) - returns per-season stats
  - Date range (using game_date)
  - Career (all games in database) - returns lifetime stats
- Exclude pre-season games from calculations

### 4. Backfill Script (`backfill.py`)
- Iterate through dates for last 10 years
- For each date, scrape games and store in database
- Progress tracking and error handling
- Resume capability (skip existing games)

### 5. Daily Update Script (`daily_update.py`)
- Scrape yesterday's games (or current day)
- Update database with new games
- Recalculate averages (or calculate on-the-fly)

### 6. API Endpoints
- `GET /api/referees` - List all referees
- `GET /api/referees/<referee_id>/stats` - Get stats with query params:
  - `season_id` - Filter by season (returns per-season stats)
  - `start_date` & `end_date` - Filter by date range
  - If no params, return lifetime/career stats
- `GET /api/seasons` - List all seasons

### 7. UI Enhancements
- Add section to query referee statistics
- Display PIMs/game, total games, total PIMs
- Support filtering by season or date range

## Implementation Steps

1. Set up database schema and connection (`database.py`)
2. Enhance `WebScraper.py` to extract game date and season
3. Modify `scrape_games()` in `app.py` to save to database
4. Create referee statistics calculation functions (`referee_stats.py`)
5. Add new API endpoints to `app.py`
6. Create backfill script (`backfill.py`)
7. Create daily update script (`daily_update.py`)
8. Update UI to display referee statistics
9. Add database to requirements.txt

## Technical Decisions

- **MySQL** chosen for hosting compatibility
- **On-the-fly calculation** for stats (more flexible than pre-calculated averages)
- **Junction table** for many-to-many relationship (games ↔ referees)
- **Season-based filtering** for organizing data and filtering pre-season games
- **Per-season and lifetime stats** - calculate stats per season and overall career

