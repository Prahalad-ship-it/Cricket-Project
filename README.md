# 🏏 Cricket Dashboard

A live cricket dashboard built with Python that fetches real-time match data, upcoming fixtures, and player statistics from ESPN Cricket API. View live scores, man-of-match awards, player-of-series, and export data to CSV.

---

## ✨ Features

- **Live Scores**: Display current & recently finished cricket matches with real-time updates
- **Match Details**: Shows scores, winner/loser, man-of-match, player-of-series, and venue
- **Upcoming Fixtures**: See next 7 days of scheduled matches with dates and venues
- **Player Stats**: Career batting statistics for 15 featured cricketers (Virat Kohli, Joe Root, Steve Smith, etc.)
- **Auto-Refresh**: Dashboard updates every 30 seconds automatically
- **CSV Export**: Export all data (live scores, fixtures, player stats) to timestamped CSV files
- **Multi-League Support**: Tracks 8 major cricket leagues simultaneously
  - IPL (Indian Premier League)
  - ICC Events (World Cups, World T20)
  - BBL (Big Bash League - Australia)
  - T20 Blast (England)
  - International Matches
  - PSL (Pakistan Super League)
  - CPL (Caribbean Premier League)
  - SA20 (South Africa)

---

## 📋 Requirements

- **Python 3.10+** (uses modern type hints)
- **Dependencies:**
  - `requests` - HTTP requests to ESPN API
  - `beautifulsoup4` - Web scraping ESPN Cricinfo
  - `rich` - Terminal UI with colors and tables

---

## 🚀 Installation

### 1. Install Python 3.10+
Download from [python.org](https://www.python.org/downloads/)

### 2. Clone/Download the Project
```bash
cd Chess-Game-1
```

### 3. Install Dependencies
```bash
pip install requests beautifulsoup4 rich
```

Or use the requirements file (if available):
```bash
pip install -r requirements.txt
```

---

## 📖 How to Use

### **Option 1: Live Interactive Dashboard**
```bash
python cricket.py
```

This starts an interactive terminal dashboard that:
- Displays live & recent cricket matches in a formatted table
- Shows upcoming fixtures for the next 7 days
- Displays top player career statistics
- Updates automatically every 30 seconds
- Runs until you press `Ctrl+C`

**Dashboard Layout:**
```
┌─ Header with timestamp
├─ 🏏 Live & Recent Scores (top 10 matches)
│  ├─ League | Match | Score | Winner | MoM | PoS | Status | Venue
│  └─ Color-coded: Green=Live, White=Finished, Yellow=Scheduled
├─ Bottom Section (split):
│  ├─ 📅 Upcoming Fixtures (next 7 days)
│  └─ 📊 Top Player Stats (Career Batting)
└─ Footer with info & refresh timing
```

### **Option 2: Export Data Only**
```bash
python cricket.py --export
```

This runs once and creates three CSV files in the `cricket_exports/` folder:
- `live_scores_YYYYMMDD_HHMMSS.csv` - Match data with winner, loser, MoM, PoS
- `fixtures_YYYYMMDD_HHMMSS.csv` - Upcoming fixtures
- `player_stats_YYYYMMDD_HHMMSS.csv` - Player career statistics

**Note:** Use this mode if you don't need the interactive dashboard or want to batch-process data.

---

## 🔄 How It Works (Step-by-Step)

### **A. Data Fetching Flow**

#### **1. Live Scores (_`get_live_scores()`_)**
```
Strategy: League-First Approach
│
├─ For each league in LEAGUES dictionary:
│  ├─ Call ESPN API: /cricket/{league_id}/scoreboard
│  ├─ Filter results:
│  │  ├─ Skip scheduled matches (state="pre")
│  │  └─ Keep live (state="in") & finished (state="post")
│  │
│  ├─ Parse match data:
│  │  ├─ Teams: Extract team abbreviations (MI, CSK, etc.)
│  │  ├─ Scores: Get current run totals
│  │  ├─ Innings: Parse scorecard line scores (first innings, second innings)
│  │  └─ Venue: Extract ground/stadium name
│  │
│  └─ For finished/live matches only:
│     ├─ Fetch match summary: /cricket/{league_id}/summary?event={match_id}
│     ├─ Extract awards:
│     │  ├─ Man of Match (MoM) - Best player of the match
│     │  └─ Player of Series (PoS) - Tournament MVP
│     ├─ Winner/Loser: Identify winning & losing teams
│     └─ Top Stats:
│        ├─ Top Batter: Highest scorer (runs + balls faced)
│        └─ Top Bowler: Most wickets (with economy rate tiebreaker)
│
└─ Sort by match state: Live → Finished → Scheduled
```

**Data Structure Example:**
```python
{
    "league": "IPL",
    "name": "MI vs CSK",
    "score": "MI 165  |  CSK 142",
    "winner": "MI",
    "loser": "CSK",
    "mom": "Suryakumar Yadav",
    "player_series": "Virat Kohli",
    "status": "Final",
    "venue": "Wankhede Stadium",
    "teams": ["MI", "CSK"],
    "state": "post"  # in, post, or pre
}
```

#### **2. Upcoming Fixtures (_`get_schedule()`_)**
```
Strategy: Date-Range Scanning
│
├─ Generate next 7 days of dates: [today, today+1, ..., today+7]
│
├─ For each date:
│  └─ Call ESPN API: /cricket/scoreboard?dates=YYYYMMDD
│     ├─ Filter: state="pre" (scheduled only)
│     ├─ Extract:
│     │  ├─ Teams: Team1 vs Team2
│     │  ├─ Date/Time: Match start time in UTC
│     │  ├─ League: Which competition
│     │  └─ Venue: Where it's being played
│     └─ Store in fixtures list
│
└─ Return first 30 matches (cap)
```

#### **3. Player Statistics (_`get_player_stats()`_)**
```
Strategy: Web Scraping from ESPN Cricinfo
│
├─ For each featured player (15 total):
│  ├─ Build URL: https://www.espncricinfo.com/cricketers/{player-name}-{player-id}
│  ├─ Fetch HTML page
│  ├─ Parse career batting table:
│  │  ├─ Career Runs: Total runs scored
│  │  ├─ Batting Average: Runs per dismissal
│  │  └─ Centuries: Number of 100+ run innings
│  └─ Store in player stats list
│
└─ Return all 15 players with stats
```

---

### **B. API Endpoints Used**

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `/sports/cricket/{league_id}/scoreboard` | Fetch live/finished matches | Returns current IPL matches |
| `/sports/cricket/{league_id}/summary?event={match_id}` | Get detailed match stats | Retrieves MoM, boxscore, awards |
| `espncricinfo.com/cricketers/{name}-{id}` | Player career stats | Web scraping (not API) |

---

### **C. Dashboard Refresh Cycle**

```
Start Application
│
├─ Fetch All Data:
│  ├─ get_live_scores()      → 8 API calls (1 per league)
│  ├─ get_schedule()         → 8 API calls (7 dates × leagues)
│  ├─ get_match_summary()    → N API calls (for each live/finished match)
│  └─ get_player_stats()     → 15 web scrapes (1 per player)
│
├─ Build Dashboard:
│  ├─ Top 10 matches (sorted by state)
│  ├─ Upcoming 30 fixtures
│  └─ 15 player career stats
│
├─ Display in Terminal
│
├─ Start Live Loop:
│  └─ Every 1 second:
│     ├─ Check if 30 seconds elapsed
│     ├─ If yes → Fetch all data again
│     └─ Update dashboard on screen
│
└─ Continue until user presses Ctrl+C
```

---

### **D. CSV Export Format**

#### **live_scores_{timestamp}.csv**
| League | Match | Team 1 | Score 1 | Team 2 | Score 2 | Winner | Loser | MoM | PoS | Top Batter | Top Bowler | Status | Venue |
|--------|-------|--------|---------|--------|---------|--------|-------|-----|-----|-------------|------------|--------|-------|
| IPL | MI vs CSK | MI | 165 | CSK | 142 | MI | CSK | Suryakumar Yadav | — | Ishan Kishan 42(28) | Jasprit Bumrah 3/28 | Final | Wankhede |

#### **fixtures_{timestamp}.csv**
| League | Match | Date (UTC) | Venue |
|--------|-------|-----------|-------|
| IPL | MI vs RCB | 02 Apr 2026  19:30 UTC | Wankhede Stadium |

#### **player_stats_{timestamp}.csv**
| Player | Career Runs | Batting Avg | Centuries |
|--------|-------------|-------------|-----------|
| Virat Kohli | 13000+ | 55.40 | 45 |

---

## ⚙️ Configuration

### **Add/Remove Leagues**
Edit the `LEAGUES` dictionary in `cricket.py`:
```python
LEAGUES = {
    "IPL":          6039,   # Keep this
    "ICC Events":   8050,   # Keep this
    "BBL":          6048,   # Comment out or remove to skip
    # Add new leagues by finding their ESPN Cricket API ID
}
```

### **Add/Remove Featured Players**
Edit the `FEATURED_PLAYERS` dictionary:
```python
FEATURED_PLAYERS = {
    "Virat Kohli":      253802,      # Keep
    "Your Player Name": 999999,      # Add (find ID on espncricinfo.com)
}
```

### **Change CSV Export Location**
Edit the `CSV_OUTPUT_DIR` variable:
```python
CSV_OUTPUT_DIR = "cricket_exports"  # Change to your preferred path
```

---

## 🔌 API Details

### **ESPN Cricket API (Free, No Key Required)**
- Base URL: `https://site.api.espn.com/apis/site/v2/sports/cricket`
- Rate Limit: Reasonable limits (no official docs, but generally good)
- Data: Live scores, match details, awards, boxscores
- No authentication needed

### **ESPN Cricinfo (Web Scraping)**
- URL Pattern: `https://www.espncricinfo.com/cricketers/{name}-{id}`
- Method: BeautifulSoup HTML parsing
- Data: Player career statistics
- Rate Limit: Respectful delays (8-second timeout per request)

---

## 📊 Example Output

### **Terminal Dashboard**
```
┌───────────────────────────────────────────────────────────────────┐
│              🏏  CRICKET DASHBOARD                                 │
│  Live scores · Fixtures · Player stats | Last updated: 02 Apr... │
└───────────────────────────────────────────────────────────────────┘

🏏 Live & Recent Scores
┌─────────┬──────────────┬──────────────────────┬────────┬─────────┐
│ League  │ Match        │ Score                │ Winner │ MoM     │
├─────────┼──────────────┼──────────────────────┼────────┼─────────┤
│ IPL     │ MI vs CSK    │ MI 165 | CSK 142    │ MI     │ Surya   │
│ IPL     │ DC vs GT     │ GT 178 | DC 165     │ GT     │ Rashid  │
└─────────┴──────────────┴──────────────────────┴────────┴─────────┘

┌─ 📅 Upcoming Fixtures          ┬─────── 📊 Top Players ────────┐
│ IPL | MI vs RCB | 02 Apr 19:30 │ Virat Kohli: 13000 @ 55.40   │
│ IPL | CSK vs RR  | 03 Apr 19:30 │ Joe Root: 12000 @ 50.00      │
└────────────────────────────────┴──────────────────────────────┘

Data: ESPN Cricinfo | Press Ctrl+C to exit | Refreshes every 30s
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `SyntaxError: invalid syntax` | Update Python to 3.10+ (script uses `Type \| None` syntax) |
| `ModuleNotFoundError: requests` | Run `pip install requests beautifulsoup4 rich` |
| No matches showing | ESPN API may return empty results; script falls back to league-specific queries |
| Slow player stats | Web scraping espncricinfo takes ~8 seconds per player (15 players = 2 mins total) |
| No CSV files created | Check write permissions in `cricket_exports/` folder |

---

## 📝 License

This project uses free, public APIs and data from ESPN Cricket. Use responsibly and respect rate limits.

---

## 🤝 Contributing

To modify:
1. Edit `LEAGUES` or `FEATURED_PLAYERS` dictionaries for configuration
2. Modify dashboard columns in `build_scores_panel()` function
3. Change refresh interval (default 30s) in `main()` function
4. Add new data sources by extending `fetch_all()` function

---

## 📧 Questions?

- Check ESPN API documentation at `site.api.espn.com`
- Find player IDs on `espncricinfo.com`
- View repo for latest updates

**Enjoy live cricket scores! 🏏✨**
