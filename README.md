# KIJHL Referee Statistics Tracker

**Live Application**: [**KIJHL Game Scraper and Referee Stats Tracker**](https://kijhl-img-135337671384.us-west1.run.app)

A comprehensive web scraping and analytics platform for tracking referee performance statistics in the Kootenay International Junior Hockey League (KIJHL). This application collects game data, calculates penalty minutes per game metrics for officials, and provides an intuitive web interface for querying historical and real-time statistics.

## 🎯 Project Overview

This project demonstrates full-stack development and cloud deployment skills by combining web scraping, a serverless architecture, NoSQL database design, and a modern web UI. The system tracks referee performance metrics across multiple seasons, and provides both per-season and career statistics.

### Key Features

- **Live & Automated**: Deployed on Google Cloud Run and automatically updated daily via Google Cloud Scheduler.
- **Automated Data Collection**: Scrapes game data from KIJHL's HockeyTech API with concurrent processing for optimal performance.
- **Referee Performance Analytics**: Calculates PIMs (Penalty Minutes) per game statistics for referees and linesmen.
- **Season & Career Tracking**: Supports queries by season, role, and various sorting metrics.
- **Historical Backfill**: A script to populate the database with historical data from multiple seasons.
- **Modern Web Interface**: Responsive, user-friendly UI built with vanilla JavaScript and modern CSS.
- **RESTful API**: Clean API endpoints for programmatic access to statistics.

## 🛠️ Tech Stack

### Backend & Cloud Infrastructure
- **Python 3.x**: Core programming language.
- **Flask**: Web framework for API and server-side logic.
- **Google Cloud Run**: Serverless container platform for hosting the application.
- **Docker**: For containerizing the Flask application for deployment.
- **Google Firebase (Firestore)**: NoSQL database for flexible and scalable data storage.
- **Google Cloud Scheduler**: For triggering automated daily data updates.
- **ThreadPoolExecutor**: For concurrent API requests to improve scraping performance.

### Frontend
- **HTML5/CSS3**: Modern, responsive design with CSS Grid and Flexbox.
- **Vanilla JavaScript**: Client-side interactivity and API communication.
- **Responsive Design**: Mobile-friendly interface.

## 🚀 Getting Started

The application is live at [**kijhl-img-135337671384.us-west1.run.app**](https://kijhl-img-135337671384.us-west1.run.app)

## 🔌 API Endpoints

### Game Scraping
- `POST /api/scrape` - Scrape games for a specific date
  - Body: `{"date": "YYYY-MM-DD"}`

### Leaderboard
- `GET /leaderboard` - Renders the leaderboard page with optional query parameters.
  - Query parameters:
    - `role` (optional): `all`, `referee`, `linesman`
    - `sort` (optional): `pims`, `avg`
    - `order` (optional): `desc`, `asc`
    - `season` (optional): Season ID (e.g., `65`)
    - `games_called` (optional): Minimum games called threshold (integer)

## 💡 Key Technical Achievements

1.  **Serverless Deployment**: Successfully containerized and deployed a Python web application on Google Cloud Run, enabling auto-scaling and high availability.
2.  **Concurrent Processing**: Implemented `ThreadPoolExecutor` to process multiple API requests simultaneously, reducing scraping time significantly.
3.  **NoSQL Database Design**: Designed a Firestore schema to efficiently store and query game and official data by season.
4.  **Full Automation**: Used Google Cloud Scheduler to create a fully automated, hands-off daily data pipeline.
5.  **API Integration**: Reverse-engineered and integrated with HockeyTech's undocumented API to source data.

## 🎓 Skills Demonstrated

- **Cloud & DevOps**: Google Cloud Run, Firebase/Firestore, Google Cloud Scheduler, Docker.
- **Web Scraping**: API integration and concurrent data fetching.
- **Backend Development**: Flask RESTful API design.
- **Database Design**: NoSQL data modeling and querying.
- **Frontend Development**: Modern HTML/CSS/JavaScript.
- **Software Architecture**: Modular design, separation of concerns.
- **Automation**: Scheduled tasks and batch processing.

## 🔮 Future Enhancements

- [ ] User authentication and personalized dashboards
- [ ] Advanced analytics and visualization (charts, trends)
- [ ] Export functionality (CSV, PDF reports)
- [ ] Comparison tools (compare multiple officials)
- [ ] Unit and integration testing suite

## 📝 License

This project is for educational and personal use. Please respect the terms of service of the KIJHL website and HockeyTech API when using this application.

## 👤 Author

Developed as a personal project to demonstrate full-stack development, cloud deployment, and data analysis skills.

## 🙏 Acknowledgments

- KIJHL for providing public game statistics
- HockeyTech for the game data API

---

**Note**: This project is not affiliated with or endorsed by KIJHL or HockeyTech. It is an independent tool for statistical analysis.
