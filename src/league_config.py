LEAGUES = {
    'kijhl': {
        'name': 'Kootenay International Junior Hockey League',
        'abbreviation': 'KIJHL',
        'client_code': 'kijhl',
        'api_key': '2589e0f644b1bb71',
        'base_url': 'https://lscluster.hockeytech.com/feed/index.php?feed=statviewfeed&view=gameSummary&game_id={game_id}&key=2589e0f644b1bb71&site_id=2&client_code=kijhl&lang=en&league_id=&callback=angular.callbacks._4',
        'season_ids': { 
            '2021-2022 (Reg Season)': 49,
            '2021-2022 (Playoffs)'  : 51,
            '2022-2023 (Reg Season)': 52,
            '2022-2023 (Playoffs)'  : 54,
            '2023-2024 (Reg Season)': 56,
            '2023-2024 (Playoffs)'  : 59,
            '2024-2025 (Reg Season)': 61,
            '2024-2025 (Playoffs)'  : 63,
            '2025-2026 (Reg Season)': 65,
            '2025-2026 (Playoffs)'  : 66,
        },
        'season_start_dates': {
            '2025-2026 (Playoffs)': '2026-03-01',
            '2025-2026 (Reg Season)': '2025-09-19',
            '2024-2025 (Playoffs)': '2025-02-28',
            '2024-2025 (Reg Season)': '2024-09-20',
            '2023-2024 (Playoffs)': '2024-02-23',
            '2023-2024 (Reg Season)': '2023-09-22',
            '2022-2023 (Playoffs)': '2023-02-17',
            '2022-2023 (Reg Season)': '2022-09-23',
            '2021-2022 (Playoffs)': '2022-02-22',
            '2021-2022 (Reg Season)': '2021-10-01'
        },
        'color_scheme': {
            'primary': '#cc0000',      # Red
            'secondary': '#1a1a1a',    # Black
            'accent': '#ffffff'        # White
        },
        'firebase_path': 'leagues/kijhl'
    },
    'whl': {
        'name': 'Western Hockey League',
        'abbreviation': 'WHL',
        'client_code': 'whl',
        'api_key': 'f1aa699db3d81487',
        'base_url': 'https://lscluster.hockeytech.com/feed/?feed=gc&key=f1aa699db3d81487&game_id={game_id}&client_code=whl&tab=gamesummary&lang_code=en&fmt=json&callback=jsonp_1769465924711_51167',
        'season_ids': {
            # Pre-season is +1 from regular season
            # Playoffs is +3 from regular season
    
            '2020-2021 (Regular Season)': 257,
            '2020-2021 (Playoffs)': 260,
            '2021-2022 (Regular Season)': 261,
            '2021-2022 (Playoffs)': 264,
            '2022-2023 (Regular Season)': 265,
            '2022-2023 (Playoffs)': 268,
            '2023-2024 (Regular Season)': 281,
            '2023-2024 (Playoffs)': 284,
            '2024-2025 (Regular Season)': 285,
            '2024-2025 (Playoffs)': 288,
            '2025-2026 (Regular Season)': 289,
            '2025-2026 (Playoffs)': 292,
        },
        'season_start_dates': {
            '2025-2026 (Playoffs)': '2026-02-19',
            '2025-2026 (Regular Season)': '2025-09-01',
            '2024-2025 (Playoffs)': '2025-02-28',
            '2024-2025 (Regular Season)': '2024-09-01',
            '2023-2024 (Playoffs)': '2024-02-23',
            '2023-2024 (Regular Season)': '2023-09-01',
            '2022-2023 (Playoffs)': '2023-02-17',
            '2022-2023 (Regular Season)': '2022-09-01',
            '2021-2022 (Playoffs)': '2022-02-22',
            '2021-2022 (Regular Season)': '2021-09-01',
            '2020-2021 (Playoffs)': '2021-02-19',
            '2020-2021 (Regular Season)': '2020-09-01',
        },
        'color_scheme': {
            'primary': '#FF8C00',      # Orange
            'secondary': '#1a1a1a',    # Black
            'accent': '#ffffff'        # White
        },
        'firebase_path': 'leagues/whl'
    }        
}