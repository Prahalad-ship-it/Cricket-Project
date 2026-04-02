import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich import box
from datetime import datetime, timedelta, timezone
import time
import csv
import os
import logging   # ✅ NEW

console = Console()

# ✅ LOGGING (NEW)
logging.basicConfig(
    filename="cricket_dashboard.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

AUTO_EXPORT = False   # ✅ NEW toggle

LEAGUES = {
    "IPL": 6039, "ICC": 8050, "BBL": 6048, "T20 Blast": 6590,
    "Int'l": 7975, "PSL": 6386, "CPL": 6404, "SA20": 9551,
}

FIXTURE_DAYS_AHEAD = 7
CSV_OUTPUT_DIR = "cricket_exports"

FEATURED_PLAYERS = {
    "Virat Kohli": 253802, "Rohit Sharma": 34102,
    "MS Dhoni": 28081, "Jasprit Bumrah": 625371,
}

# ─────────────────────────────────────────
# INTERNET CHECK (NEW)
# ─────────────────────────────────────────

def check_internet():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def _date_range(days: int):
    today = datetime.now(timezone.utc)
    return [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(days + 1)]

def _fetch_scoreboard(lid=None, date_str=None):
    try:
        base = "https://site.api.espn.com/apis/site/v2/sports/cricket"
        if lid:
            base += f"/{lid}"
        url = f"{base}/scoreboard"
        if date_str:
            url += f"?dates={date_str}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        return r.json().get("events", []) if r.status_code == 200 else []
    except Exception as e:
        logging.error(e)
        return []

def _fetch_match_summary(lid, eid):
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/cricket/{lid}/summary?event={eid}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        return r.json() if r.status_code == 200 else {}
    except Exception as e:
        logging.error(e)
        return {}

# ─────────────────────────────────────────
# CORE FUNCTIONS (same logic, safer)
# ─────────────────────────────────────────

def get_live_scores():
    matches = []
    seen = set()

    for event in _fetch_scoreboard():
        try:
            eid = event.get("id")
            if eid in seen:
                continue
            seen.add(eid)

            comp = (event.get("competitions") or [{}])[0]
            state = event.get("status", {}).get("type", {}).get("state", "unknown")
            if state == "pre":
                continue

            league = comp.get("league", {}).get("shortName") or comp.get("league", {}).get("displayName")
            league = league or event.get("leagues", [{}])[0].get("shortName") or "Unknown"

            teams = [c.get("team", {}).get("abbreviation", "?") for c in comp.get("competitors", [])]
            scores = [c.get("score", "—") for c in comp.get("competitors", [])]

            matches.append({
                "league": league,
                "name": event.get("shortName", event.get("name")),
                "teams": teams,
                "scores": scores,
                "status": event.get("status", {}).get("type", {}).get("shortDetail"),
                "state": state
            })
        except Exception as e:
            logging.error(e)

    return matches

def get_schedule():
    fixtures = []
    for d in _date_range(FIXTURE_DAYS_AHEAD):
        for e in _fetch_scoreboard(None, d):
            try:
                if e.get("status", {}).get("type", {}).get("state") != "pre":
                    continue

                comp = (e.get("competitions") or [{}])[0]
                league = comp.get("league", {}).get("shortName") or comp.get("league", {}).get("displayName")
                league = league or e.get("leagues", [{}])[0].get("shortName") or "Unknown"
                teams = [c.get("team", {}).get("displayName", "?") for c in comp.get("competitors", [])]

                fixtures.append({
                    "league": league,
                    "match": " vs ".join(teams),
                    "date": e.get("date")
                })
            except Exception as ex:
                logging.error(ex)

    return fixtures[:30]

def get_player_stats():
    players = []
    for name, pid in FEATURED_PLAYERS.items():
        try:
            url = f"https://www.espncricinfo.com/cricketers/{name.lower().replace(' ','-')}-{pid}"
            r = requests.get(url, headers=HEADERS, timeout=8)
            soup = BeautifulSoup(r.text, "html.parser")

            runs = soup.find(text="Runs")
            players.append({"name": name, "runs": "—" if not runs else "✔"})
        except Exception as e:
            logging.error(e)
            players.append({"name": name, "runs": "—"})
    return players

# ─────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────

def export_to_csv(matches):
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    path = f"{CSV_OUTPUT_DIR}/live.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["League", "Match", "Score"])
        for m in matches:
            w.writerow([m["league"], m["name"], str(m["scores"])])
    return path

# ─────────────────────────────────────────
# UI
# ─────────────────────────────────────────

def build_dashboard(matches):
    table = Table(box=box.SIMPLE)
    table.add_column("League")
    table.add_column("Match")
    table.add_column("Score")

    for m in matches:
        score = " vs ".join(m["teams"])
        table.add_row(m["league"], m["name"], score)

    return Panel(table, title="🏏 Cricket Dashboard")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def fetch_all():
    if not check_internet():
        console.print("[bold red]No Internet![/bold red]")
        return []

    return get_live_scores()

def main():
    while True:
        matches = fetch_all()

        console.clear()
        console.print(build_dashboard(matches))

        print("\nDEBUG:", matches)  # 👈 IMPORTANT

        time.sleep(10)

if __name__ == "__main__":
    main()