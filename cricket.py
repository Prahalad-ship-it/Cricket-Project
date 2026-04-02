import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich import box
from datetime import datetime, timedelta
import time
import csv
import os

console = Console()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}



# ESPN Cricket API League IDs
# Comment out any leagues you don't want tracked
LEAGUES = {
    "IPL":          6039,   # Indian Premier League
    "ICC Events":   8050,   # ICC World Cups / global events
    "BBL":          6048,   # Big Bash League (Australia)
    "T20 Blast":    6590,   # Vitality T20 Blast (England)
    "Int'l":        7975,   # International matches
    "PSL":          6386,   # Pakistan Super League
    "CPL":          6404,   # Caribbean Premier League
    "SA20":         9551,   # SA20 (South Africa)
}


def _date_range(days: int) -> list[str]:
    start = datetime.utcnow()
    return [(start + timedelta(days=i)).strftime("%Y%m%d") for i in range(days + 1)]


def _fetch_match_summary(lid: int, eid: str) -> dict:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/cricket/{lid}/summary?event={eid}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

# CSV output folder — exports will be saved here
CSV_OUTPUT_DIR = "cricket_exports"

# Featured players: "Full Name" -> ESPN Cricinfo player ID
# Add / remove players freely — find IDs on espncricinfo.com (last number in the URL)
FEATURED_PLAYERS = {
    # India
    "Virat Kohli":      253802,
    "Rohit Sharma":     34102,
    "MS Dhoni":         28081,
    "Jasprit Bumrah":   625371,
    "Shubman Gill":     931581,
    # England
    "Joe Root":         303669,
    "Ben Stokes":       311158,
    "Jos Buttler":      308967,
    # Australia
    "Steve Smith":      267192,
    "Pat Cummins":      326016,
    "David Warner":     219889,
    # Pakistan
    "Babar Azam":       348144,
    "Shaheen Afridi":   714045,
    # West Indies / Others
    "Kane Williamson":  277906,
    "Kagiso Rabada":    550215,
}


# ─────────────────────────────────────────
# SCRAPERS
# ─────────────────────────────────────────

def _fetch_match_summary(lid: int, eid: str) -> dict:
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/cricket/{lid}/summary?event={eid}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def get_live_scores() -> list[dict]:
    """Fetch live/recent scores from ESPN Cricket API."""
    matches = []
    seen = set()
    url = "https://site.api.espn.com/apis/site/v2/sports/cricket/scoreboard"

    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json()

        for event in data.get("events", []):
            eid = event.get("id")
            if eid in seen:
                continue
            seen.add(eid)

            competitions = event.get("competitions", [{}])
            comp = competitions[0] if competitions else {}
            competitors = comp.get("competitors", [])
            status_type = event.get("status", {}).get("type", {})

            league = event.get("leagues", [{}])[0].get("shortName")
            if not league:
                league = comp.get("league", {}).get("shortName")
            if not league:
                league = event.get("leagues", [{}])[0].get("name") or "Unknown"

            teams, scores, innings = [], [], []
            for c in competitors:
                teams.append(c.get("team", {}).get("abbreviation", "???"))
                scores.append(c.get("score", "—"))
                linescores = c.get("linescores", [])
                inn = " / ".join(
                    ls.get("displayValue", "") for ls in linescores if ls.get("displayValue")
                )
                innings.append(inn or "—")

            if len(teams) == 2:
                left = f"{teams[0]} {scores[0]}" + (f" ({innings[0]})" if innings[0] != "—" else "")
                right = f"{teams[1]} {scores[1]}" + (f" ({innings[1]})" if innings[1] != "—" else "")
                score_line = f"{left}  |  {right}"
            else:
                score_line = "  |  ".join(
                    f"{teams[i]} {scores[i]}" for i in range(len(teams))
                ) if teams else "—"

            mom = "—"
            top_batter = "—"
            top_bowler = "—"
            best_runs = -1
            best_wkts = -1
            best_econ = 999.0

            lid = event.get("leagues", [{}])[0].get("id") or comp.get("league", {}).get("id")
            if lid and status_type.get("state") in {"in", "post"}:
                summary = _fetch_match_summary(lid, eid)

                for award in summary.get("awards", []):
                    if "match" in award.get("type", {}).get("text", "").lower():
                        mom = award.get("athlete", {}).get("displayName", "—")
                        break

                boxscore = summary.get("boxscore", {})
                for team_data in boxscore.get("players", []):
                    for stat_group in team_data.get("statistics", []):
                        sg_name = stat_group.get("type", {}).get("displayName", "").lower()
                        if "bat" in sg_name:
                            for athlete in stat_group.get("athletes", []):
                                stats = {s.get("name"): s.get("displayValue") for s in athlete.get("stats", [])}
                                runs = stats.get("runs", "0") or "0"
                                try:
                                    runs_int = int(runs.replace("*", ""))
                                except Exception:
                                    runs_int = 0
                                if runs_int > best_runs:
                                    best_runs = runs_int
                                    name = athlete.get("athlete", {}).get("displayName", "?")
                                    balls = stats.get("balls", "?")
                                    top_batter = f"{name} {runs} ({balls}b)" if balls != "?" else f"{name} {runs}"
                        if "bowl" in sg_name:
                            for athlete in stat_group.get("athletes", []):
                                stats = {s.get("name"): s.get("displayValue") for s in athlete.get("stats", [])}
                                wickets = stats.get("wickets", "0") or "0"
                                econ = stats.get("economy", "99") or "99"
                                runs_conceded = stats.get("runsConceded", "?")
                                overs = stats.get("overs", "?")
                                try:
                                    wkts_int = int(wickets)
                                except Exception:
                                    wkts_int = -1
                                try:
                                    econ_val = float(econ)
                                except Exception:
                                    econ_val = 99.0
                                if wkts_int > best_wkts or (wkts_int == best_wkts and econ_val < best_econ):
                                    best_wkts = wkts_int
                                    best_econ = econ_val
                                    name = athlete.get("athlete", {}).get("displayName", "?")
                                    top_bowler = f"{name} {wickets}/{runs_conceded} ({overs}ov)"

            matches.append({
                "league":    league,
                "name":      event.get("shortName", event.get("name", "Unknown")),
                "status":    status_type.get("shortDetail", status_type.get("description", "—")),
                "state":     status_type.get("state", "pre"),   # pre / in / post
                "score":     score_line,
                "top_batter": top_batter,
                "top_bowler": top_bowler,
                "mom":       mom,
                "teams":     teams,
                "scores":    scores,
                "innings":   innings,
                "venue":     comp.get("venue", {}).get("fullName", "—"),
            })
    except Exception:
        return []

    # Sort: live first, then recent, then upcoming
    order = {"in": 0, "post": 1, "pre": 2}
    matches.sort(key=lambda m: order.get(m["state"], 3))
    return matches


def get_schedule() -> list[dict]:
    """Fetch upcoming fixtures from ESPN Cricket API."""
    fixtures = []
    seen = set()

    for date_str in _date_range(7):
        url = f"https://site.api.espn.com/apis/site/v2/sports/cricket/scoreboard?dates={date_str}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()

            for event in data.get("events", []):
                eid = event.get("id")
                if eid in seen:
                    continue
                seen.add(eid)

                status_type = event.get("status", {}).get("type", {})
                if status_type.get("state") != "pre":
                    continue

                competitions = event.get("competitions", [{}])
                comp = competitions[0] if competitions else {}
                league = event.get("leagues", [{}])[0].get("shortName")
                if not league:
                    league = comp.get("league", {}).get("shortName")
                if not league:
                    league = event.get("leagues", [{}])[0].get("name") or "Unknown"

                teams = [
                    c.get("team", {}).get("displayName", "?")
                    for c in comp.get("competitors", [])
                ]

                try:
                    dt = datetime.fromisoformat(event.get("date", "").replace("Z", "+00:00"))
                    formatted = dt.strftime("%d %b %Y  %H:%M UTC")
                except Exception:
                    formatted = event.get("date", "—")

                fixtures.append({
                    "league": league,
                    "match":  " vs ".join(teams) if teams else event.get("name", "—"),
                    "date":   formatted,
                    "venue":  comp.get("venue", {}).get("fullName", "—"),
                })
        except Exception:
            continue

    return fixtures[:30]   # cap at 30 upcoming fixtures

    return fixtures[:12]   # cap at 12


def get_player_stats() -> list[dict]:
    """Scrape batting stats for featured players from ESPN Cricinfo."""
    players = []

    for name, pid in FEATURED_PLAYERS.items():
        url = f"https://www.espncricinfo.com/cricketers/{name.lower().replace(' ', '-')}-{pid}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            soup = BeautifulSoup(r.text, "html.parser")

            # Grab the first stats table (career batting)
            tables = soup.select("table")
            runs, avg, hundreds = "—", "—", "—"

            for table in tables:
                headers_row = table.find("tr")
                if not headers_row:
                    continue
                hdrs = [th.get_text(strip=True).lower() for th in headers_row.find_all(["th", "td"])]

                # look for a batting table
                if "runs" in hdrs and "ave" in hdrs:
                    rows = table.find_all("tr")[1:]
                    for row in rows:
                        cells = [td.get_text(strip=True) for td in row.find_all("td")]
                        if not cells:
                            continue
                        # First data row = Test or overall career
                        try:
                            ri = hdrs.index("runs")   if "runs" in hdrs else -1
                            ai = hdrs.index("ave")    if "ave"  in hdrs else -1
                            hi = hdrs.index("100")    if "100"  in hdrs else -1
                            runs     = cells[ri] if ri >= 0 and ri < len(cells) else "—"
                            avg      = cells[ai] if ai >= 0 and ai < len(cells) else "—"
                            hundreds = cells[hi] if hi >= 0 and hi < len(cells) else "—"
                        except Exception:
                            pass
                        break
                    break

            players.append({
                "name":     name,
                "runs":     runs,
                "avg":      avg,
                "hundreds": hundreds,
            })
        except Exception:
            players.append({"name": name, "runs": "—", "avg": "—", "hundreds": "—"})

    return players


# ─────────────────────────────────────────
# CSV EXPORT
# ─────────────────────────────────────────

def export_to_csv(matches: list[dict], fixtures: list[dict], players: list[dict]) -> str:
    """Export all scraped data to timestamped CSV files. Returns the output folder path."""
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # ── Live Scores ──────────────────────────────────────────────────
    scores_file = os.path.join(CSV_OUTPUT_DIR, f"live_scores_{timestamp}.csv")
    with open(scores_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["League", "Match", "Team 1", "Score 1", "Team 2", "Score 2", "Status", "Venue"])
        for m in matches:
            teams  = m.get("teams",  ["—", "—"])
            scores = m.get("scores", ["—", "—"])
            writer.writerow([
                m.get("league", "—"),
                m.get("name",   "—"),
                teams[0]  if len(teams)  > 0 else "—",
                scores[0] if len(scores) > 0 else "—",
                teams[1]  if len(teams)  > 1 else "—",
                scores[1] if len(scores) > 1 else "—",
                m.get("status", "—"),
                m.get("venue",  "—"),
            ])

    # ── Fixtures ─────────────────────────────────────────────────────
    fixtures_file = os.path.join(CSV_OUTPUT_DIR, f"fixtures_{timestamp}.csv")
    with open(fixtures_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["League", "Match", "Date (UTC)", "Venue"])
        for fx in fixtures:
            writer.writerow([fx.get("league", "—"), fx.get("match", "—"),
                             fx.get("date",   "—"), fx.get("venue", "—")])

    # ── Player Stats ─────────────────────────────────────────────────
    players_file = os.path.join(CSV_OUTPUT_DIR, f"player_stats_{timestamp}.csv")
    with open(players_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Player", "Career Runs", "Batting Avg", "Centuries"])
        for p in players:
            writer.writerow([p.get("name", "—"), p.get("runs", "—"),
                             p.get("avg",  "—"), p.get("hundreds", "—")])

    return CSV_OUTPUT_DIR


# ─────────────────────────────────────────
# DASHBOARD BUILDERS
# ─────────────────────────────────────────

def build_scores_panel(matches: list[dict]) -> Panel:
    table = Table(
        box=box.SIMPLE_HEAVY,
        expand=True,
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
    )
    table.add_column("League",      style="dim",          width=10)
    table.add_column("Match",       style="bold white",   min_width=20)
    table.add_column("Score",       style="bold yellow",  min_width=30)
    table.add_column("Top Bat",     style="green",       min_width=20)
    table.add_column("Top Bowl",    style="magenta",     min_width=20)
    table.add_column("MoM",         style="bright_cyan", min_width=20)
    table.add_column("Status",      style="green",       min_width=16)
    table.add_column("Venue",       style="dim",         min_width=18)

    if not matches:
        table.add_row("—", "No matches found", "—", "—", "—", "—", "—", "—")
    else:
        for m in matches[:10]:
            state = m["state"]
            if state == "in":
                status_style = "bold green"
            elif state == "post":
                status_style = "dim white"
            else:
                status_style = "yellow"

            table.add_row(
                m["league"],
                m["name"],
                m.get("score", "—"),
                m.get("top_batter", "—"),
                m.get("top_bowler", "—"),
                m.get("mom", "—"),
                Text(m["status"], style=status_style),
                m["venue"],
            )

    return Panel(table, title="[bold cyan]🏏 Live & Recent Scores[/bold cyan]", border_style="cyan")


def build_schedule_panel(fixtures: list[dict]) -> Panel:
    table = Table(
        box=box.SIMPLE_HEAVY,
        expand=True,
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    table.add_column("League", style="dim",         width=10)
    table.add_column("Match",  style="bold white",  min_width=26)
    table.add_column("Date",   style="bold yellow", min_width=20)
    table.add_column("Venue",  style="dim",         min_width=20)

    if not fixtures:
        table.add_row("—", "No upcoming fixtures found", "—", "—")
    else:
        for f in fixtures:
            table.add_row(f["league"], f["match"], f["date"], f["venue"])

    return Panel(table, title="[bold magenta]📅 Upcoming Fixtures[/bold magenta]", border_style="magenta")


def build_players_panel(players: list[dict]) -> Panel:
    table = Table(
        box=box.SIMPLE_HEAVY,
        expand=True,
        show_header=True,
        header_style="bold green",
        border_style="green",
    )
    table.add_column("Player",   style="bold white", min_width=18)
    table.add_column("Runs",     style="bold yellow", justify="right", width=8)
    table.add_column("Avg",      style="cyan",        justify="right", width=7)
    table.add_column("100s",     style="bold green",  justify="right", width=6)

    if not players:
        table.add_row("—", "—", "—", "—")
    else:
        for p in players:
            table.add_row(p["name"], p["runs"], p["avg"], p["hundreds"])

    return Panel(table, title="[bold green]📊 Top Player Stats (Career Batting)[/bold green]", border_style="green")


def build_header() -> Panel:
    now = datetime.utcnow().strftime("%d %b %Y  %H:%M UTC")
    title = Text("🏏  CRICKET DASHBOARD", style="bold white on dark_green", justify="center")
    sub   = Text(f"Live scores · Fixtures · Player stats  |  Last updated: {now}", style="dim", justify="center")
    return Panel(Align.center(title + "\n" + sub), border_style="green", padding=(0, 2))


def build_footer(csv_msg: str = "") -> Panel:
    base = "Data: ESPN Cricinfo  |  Press Ctrl+C to exit  |  Refreshes every 30s  |  Press E to export CSV"
    msg  = f"  ✅ {csv_msg}" if csv_msg else ""
    return Panel(
        Align.center(Text(base + msg, style="dim")),
        border_style="dim",
        padding=(0, 1),
    )


def build_dashboard(matches, fixtures, players, csv_msg: str = "") -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(build_header(),               name="header",  size=4),
        Layout(build_scores_panel(matches),  name="scores",  ratio=3),
        Layout(name="bottom",                ratio=4),
        Layout(build_footer(csv_msg),        name="footer",  size=3),
    )
    layout["bottom"].split_row(
        Layout(build_schedule_panel(fixtures), name="schedule", ratio=3),
        Layout(build_players_panel(players),   name="players",  ratio=2),
    )
    return layout


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def fetch_all():
    console.print("[dim]Fetching live scores...[/dim]")
    matches = get_live_scores()

    console.print("[dim]Fetching schedule...[/dim]")
    fixtures = get_schedule()

    console.print("[dim]Fetching player stats...[/dim]")
    players = get_player_stats()

    return matches, fixtures, players


def main():
    console.print(Panel("[bold green]🏏 Cricket Dashboard Starting...[/bold green]\n[dim]Tip: press E + Enter at any time to export data to CSV[/dim]", border_style="green"))

    matches, fixtures, players = fetch_all()
    csv_msg = ""

    with Live(build_dashboard(matches, fixtures, players, csv_msg), refresh_per_second=1, screen=True) as live:
        last_refresh = time.time()
        csv_clear_at = 0.0

        while True:
            time.sleep(1)
            now = time.time()

            # Auto-refresh data every 30 seconds
            if now - last_refresh >= 30:
                matches, fixtures, players = fetch_all()
                last_refresh = now

            # Clear the CSV status message after 5 seconds
            if csv_msg and now >= csv_clear_at:
                csv_msg = ""

            live.update(build_dashboard(matches, fixtures, players, csv_msg))


def export_prompt(matches, fixtures, players):
    """Run in a separate thread to listen for 'e' key presses."""
    while True:
        key = input().strip().lower()
        if key == "e":
            folder = export_to_csv(matches, fixtures, players)
            console.print(f"\n[bold green]✅ Exported to '{folder}/' folder[/bold green]")


if __name__ == "__main__":
    import sys

    # Run with: python cricket_dashboard.py --export
    # to instantly scrape and export CSVs without the live dashboard
    if "--export" in sys.argv:
        console.print(Panel("[bold green]🏏 Cricket Exporter — Scraping data...[/bold green]", border_style="green"))
        matches, fixtures, players = fetch_all()
        folder = export_to_csv(matches, fixtures, players)
        console.print(f"\n[bold green]✅ Done! CSVs saved to '[cyan]{folder}/[/cyan]'[/bold green]")
        console.print(f"   [dim]live_scores_*.csv · fixtures_*.csv · player_stats_*.csv[/dim]")
    else:
        try:
            main()
        except KeyboardInterrupt:
            console.print("\n[bold red]Dashboard closed.[/bold red] Thanks for watching! 🏏")