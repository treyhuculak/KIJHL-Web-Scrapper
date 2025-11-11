# KIJHL Referee Statistics Tracker

A comprehensive web scraping and analytics platform for tracking referee performance statistics in the Kootenay International Junior Hockey League (KIJHL). This application collects game data, calculates penalty minutes per game metrics for referees, and provides an intuitive web interface for querying historical and real-time statistics.

## 🎯 Project Overview

This project demonstrates full-stack development skills by combining web scraping, database design, RESTful API development, and modern web UI. The system tracks referee performance metrics across multiple seasons, filtering out pre-season games to ensure data accuracy, and provides both per-season and lifetime statistics.

### Key Features

- **Automated Data Collection**: Scrapes game data from KIJHL's HockeyTech API with concurrent processing for optimal performance
- **Referee Performance Analytics**: Calculates PIMs (Penalty Minutes) per game statistics for referees
- **Season & Career Tracking**: Supports queries by season or custom date ranges, with lifetime statistics
- **Pre-Season Filtering**: Automatically excludes pre-season games to maintain data integrity
- **Historical Backfill**: One-time script to populate database with 10 years of historical data
- **Daily Updates**: Automated daily synchronization to keep statistics current
- **Modern Web Interface**: Responsive, user-friendly UI built with vanilla JavaScript and modern CSS
- **RESTful API**: Clean API endpoints for programmatic access to statistics

## 🛠️ Tech Stack

### Backend
- **Python 3.x**: Core programming language
- **Flask**: Web framework for API and server-side logic
- **Selenium**: Web scraping and browser automation
- **BeautifulSoup4**: HTML parsing and data extraction
- **MySQL**: Relational database for persistent data storage
- **ThreadPoolExecutor**: Concurrent API requests for improved performance

### Frontend
- **HTML5/CSS3**: Modern, responsive design with CSS Grid and Flexbox
- **Vanilla JavaScript**: Client-side interactivity and API communication
- **Responsive Design**: Mobile-friendly interface

### DevOps & Tools
- **Database Design**: Normalized schema with proper indexing for performance
- **API Integration**: RESTful endpoints with JSON responses
- **Error Handling**: Comprehensive error handling and logging

## 📊 Database Schema

The application uses a normalized MySQL database with the following structure:

- **games**: Stores game information (date, teams, PIMs, season)
- **referees**: Referee information (names, unique identifiers)
- **game_referees**: Junction table linking games to referees (many-to-many)
- **seasons**: Season metadata (season ID, name, date ranges)

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- MySQL Server 5.7 or higher
- Chrome/Chromium browser (for Selenium)
- ChromeDriver (compatible with your Chrome version)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/treyhuculak/kijhl-web-scraper.git
   cd kijhl-web-scraper
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MySQL database**
   - Create a MySQL database
   - Update database credentials in `database.py` or use environment variables
   - Run the database initialization:
   ```bash
   python database.py
   ```

5. **Configure database connection**
   - Update database connection settings in `database.py`:
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'your_username',
       'password': 'your_password',
       'database': 'kijhl_referees'
   }
   ```

### Running the Application

1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **Access the web interface**
   - Open your browser and navigate to `http://localhost:5000`

3. **Initial Data Population (Optional)**
   - Run the backfill script to populate historical data:
   ```bash
   python backfill.py
   ```

4. **Set up Daily Updates (Optional)**
   - Configure a cron job (Linux/Mac) or Task Scheduler (Windows) to run:
   ```bash
   python daily_update.py
   ```

## 📁 Project Structure

```
KIJHL Web Scraper/
├── app.py                 # Flask application and API endpoints
├── WebScraper.py          # Web scraping logic and API integration
├── database.py             # Database connection and CRUD operations
├── referee_stats.py        # Statistics calculation functions
├── backfill.py            # Historical data backfill script
├── daily_update.py        # Daily update automation script
├── requirements.txt       # Python dependencies
├── plan.md                # Project planning and architecture documentation
├── templates/
│   └── index.html         # Web interface
└── README.md              # This file
```

## 🔌 API Endpoints

### Game Scraping
- `POST /api/scrape` - Scrape games for a specific date
  - Body: `{"date": "YYYY-MM-DD"}`

### Referee Statistics
- `GET /api/referees` - List all referees
- `GET /api/referees/<referee_id>/stats` - Get referee statistics
  - Query parameters:
    - `season_id` (optional): Filter by season
    - `start_date` (optional): Start date for range (YYYY-MM-DD)
    - `end_date` (optional): End date for range (YYYY-MM-DD)
    - If no parameters: Returns lifetime statistics

### Seasons
- `GET /api/seasons` - List all seasons in database

## 💡 Key Technical Achievements

1. **Concurrent Processing**: Implemented ThreadPoolExecutor to process multiple API requests simultaneously, reducing scraping time by up to 20x
2. **Database Design**: Created normalized schema with proper indexing for efficient queries across large datasets
3. **Error Handling**: Robust error handling for network issues, API failures, and data inconsistencies
4. **Data Quality**: Pre-season game filtering ensures statistical accuracy
5. **Scalability**: Architecture supports historical backfill of 10+ years of data
6. **API Integration**: Reverse-engineered and integrated with HockeyTech's undocumented API

## 🎓 Skills Demonstrated

- **Web Scraping**: Selenium automation and API integration
- **Backend Development**: Flask RESTful API design
- **Database Design**: MySQL schema design, normalization, and optimization
- **Frontend Development**: Modern HTML/CSS/JavaScript
- **Software Architecture**: Modular design, separation of concerns
- **Data Processing**: Statistical calculations and data aggregation
- **Automation**: Scheduled tasks and batch processing
- **Problem Solving**: Reverse engineering API endpoints

## 🔮 Future Enhancements

- [ ] User authentication and personalized dashboards
- [ ] Advanced analytics and visualization (charts, trends)
- [ ] Export functionality (CSV, PDF reports)
- [ ] Comparison tools (compare multiple referees)
- [ ] Real-time notifications for new game data
- [ ] Docker containerization for easy deployment
- [ ] Unit and integration testing suite

## 📝 License

This project is for educational and personal use. Please respect the terms of service of the KIJHL website and HockeyTech API when using this application.

## 👤 Author

Developed as a personal project to demonstrate full-stack development capabilities and data analysis skills.

## 🙏 Acknowledgments

- KIJHL for providing public game statistics
- HockeyTech for the game data API

---

**Note**: This project is not affiliated with or endorsed by KIJHL or HockeyTech. It is an independent tool for statistical analysis.
