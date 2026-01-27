# Logo Caching System

This system allows you to download and cache team logos locally once, eliminating the need to fetch them from the API on every request. Once cached, logos are accessed directly from the filesystem with zero runtime overhead.

## How It Works

1. **Initial Setup**: Run `cache_logos.py` once per league/season to download all team logos
2. **Storage**: Logos are stored in `static/logos/{league}/{season_id}/` organized by team abbreviation
3. **Runtime Access**: `app.py` retrieves logos directly from the static folder using `get_logo_path()`—no API calls needed

## Directory Structure

```
static/logos/
├── kijhl/
│   ├── 65/              # Season ID directory
│   │   ├── CGY.png      # Team logos named by abbreviation
│   │   ├── EDM.png
│   │   ├── ...
│   │   └── mapping.json # Reference mapping (auto-generated)
│   └── 63/
│       └── ...
└── whl/
    ├── 289/             # WHL season 289 (2025-26)
    │   ├── BDN.png
    │   ├── CGY.png
    │   ├── EDM.png
    │   └── ... (23 teams total)
    └── 288/             # WHL season 288 (2024-25)
        └── ...
```

## One-Time Setup: Download Logos

Use `cache_logos.py` to download all team logos for a league and season:

```bash
# Download KIJHL season 65 (default)
python cache_logos.py

# Download specific league and season
python cache_logos.py --league kijhl --season 65
python cache_logos.py --league whl --season 289

# View all options
python cache_logos.py --help
```

**What it does:**
- ✓ Fetches team logos using the HockeyTech API
- ✓ Downloads and caches logos locally by team abbreviation
- ✓ Generates a `mapping.json` reference file
- ✓ Skips already-downloaded logos (resume-friendly)

## Supported Leagues & Seasons

Both KIJHL and WHL are fully supported:

**KIJHL:**
- 2025-26 (Reg): 65 | (Playoffs): 66
- 2024-25 (Reg): 61 | (Playoffs): 63
- 2023-24 (Reg): 56 | (Playoffs): 59
- And earlier seasons...

**WHL:**
- 2025-26 (Reg): 289 | (Playoffs): 292
- 2024-25 (Reg): 285 | (Playoffs): 288
- 2023-24 (Reg): 281 | (Playoffs): 284
- And earlier seasons...

## Runtime Access in app.py

The `get_logo_path()` function retrieves cached logos directly from disk:

```python
def get_logo_path(league: str, season_id: int, team_abbrev: str) -> str:
    """Returns path to cached logo or None if not found"""
```

**Example:**
```python
logo = get_logo_path('kijhl', 65, 'CGY')
# Returns: "static/logos/kijhl/65/CGY.png" if file exists, None otherwise
```

## Benefits

✓ **Performance** - No API calls needed for logos on runtime (zero network latency)
✓ **Reliability** - No dependency on external API availability
✓ **Organization** - Logos stored by league and season for easy management
✓ **Simplicity** - Direct filesystem access, no caching layers
✓ **Easy Updates** - Simply re-run the script to refresh logos for a season

## Adding New Seasons

To cache logos for a new season:

```bash
python cache_logos.py --league kijhl --season 63
python cache_logos.py --league whl --season 288
```

That's it! The app will automatically use the cached logos.
