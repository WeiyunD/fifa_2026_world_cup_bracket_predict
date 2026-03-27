#!/usr/bin/env python3
"""
FIFA 2026 World Cup Bracket Predictor
Simulates the full tournament using FIFA World Ranking scores.
"""

import json
import math
import re
from collections import defaultdict
from datetime import datetime
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
K = 200          # Logistic scaling factor
GROUP_DRAW_LOW  = 0.35   # Below this → away team wins in group stage
GROUP_DRAW_HIGH = 0.65   # Above this → home team wins in group stage
KO_UNCERTAIN_LOW  = 0.40  # Below this → away team advances in knockout
KO_UNCERTAIN_HIGH = 0.60  # Above this → home team advances in knockout

# ---------------------------------------------------------------------------
# Name normalisation: FIFA ranking name → worldcup.json name
# ---------------------------------------------------------------------------
FIFA_TO_WC = {
    "IR Iran":          "Iran",
    "Côte d'Ivoire":    "Ivory Coast",
    "Korea Republic":   "South Korea",
    "Cabo Verde":       "Cape Verde",
    "Türkiye":          "Turkey",          # not in WC but keep for completeness
    "USA":              "USA",
}

# Playoff path winners (resolved by higher FIFA score)
# UEFA Path D: Czechia (1492) vs Denmark (1624) → Denmark
# UEFA Path A: Bosnia and Herzegovina (1373) vs Italy (1707) → Italy
# UEFA Path C: Kosovo (1325) vs Türkiye (1592) → Türkiye
# UEFA Path B: Sweden (1501) vs Poland (1541) → Poland
# IC Path 2: Iraq (1437) vs Bolivia (1340) → Iraq
# IC Path 1: [Jamaica/New Caledonia] vs DR Congo (1468) → DR Congo
PLAYOFF_WINNERS = {
    "UEFA Path D winner": "Denmark",
    "UEFA Path A winner": "Italy",
    "UEFA Path C winner": "Türkiye",
    "UEFA Path B winner": "Poland",
    "IC Path 2 winner":   "Iraq",
    "IC Path 1 winner":   "DR Congo",
}

# Default FIFA score for teams not in the ranking list (playoff winners etc.)
DEFAULT_SCORE = 1400.0

# ---------------------------------------------------------------------------
# Step 1 – Parse FIFA rankings from HTML
# ---------------------------------------------------------------------------

class _RankParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = []
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(self._cell.strip())
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data


def load_rankings(html_path: str) -> dict[str, float]:
    """Return {team_name: fifa_score} from the downloaded HTML table."""
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    parser = _RankParser()
    parser.feed(content)

    rankings: dict[str, float] = {}
    for row in parser.rows[1:]:          # skip header
        if len(row) < 6:
            continue
        rank_str = row[0].strip()
        if not re.match(r"^\d+", rank_str):
            continue
        raw_name = row[1].strip()
        score_str = row[5].strip()
        try:
            score = float(score_str)
        except ValueError:
            continue
        # Normalise name
        name = FIFA_TO_WC.get(raw_name, raw_name)
        rankings[name] = score

    return rankings


# ---------------------------------------------------------------------------
# Step 2 – Load schedule
# ---------------------------------------------------------------------------

def load_schedule(json_path: str) -> list[dict]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    matches = data["matches"]
    # Substitute playoff path winners with actual team names
    for m in matches:
        m["team1"] = PLAYOFF_WINNERS.get(m["team1"], m["team1"])
        m["team2"] = PLAYOFF_WINNERS.get(m["team2"], m["team2"])
    return matches


# ---------------------------------------------------------------------------
# Step 3 – Probability helpers
# ---------------------------------------------------------------------------

def fmt_date(date_str: str) -> str:
    """Convert '2026-06-28' → 'Mon Jun 28' (weekday + month + day)."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%a %b %d")   # e.g. 'Sun Jun 28'
    except ValueError:
        return date_str


def win_prob(score_a: float, score_b: float) -> float:
    """P(team A beats team B) using logistic function on score difference."""
    delta = score_a - score_b
    return 1.0 / (1.0 + math.exp(-delta / K))


def get_score(team: str, rankings: dict[str, float]) -> float:
    return rankings.get(team, DEFAULT_SCORE)


# ---------------------------------------------------------------------------
# Step 4 – Group stage simulation
# ---------------------------------------------------------------------------

def simulate_group_stage(matches: list[dict], rankings: dict[str, float]):
    """
    Returns:
        group_results  – {group: [match_result, ...]}
        standings      – {group: [team_dict sorted by rank]}
    """
    # Collect teams per group
    group_teams: dict[str, set] = defaultdict(set)
    group_matches: list[dict] = []
    for m in matches:
        if m.get("group"):
            group_teams[m["group"]].add(m["team1"])
            group_teams[m["group"]].add(m["team2"])
            group_matches.append(m)

    # Initialise points / goal-diff proxy
    stats: dict[str, dict] = {}
    for group, teams in group_teams.items():
        for t in teams:
            stats[t] = {"team": t, "group": group, "pts": 0, "gd": 0.0, "gf": 0.0}

    group_results: dict[str, list] = defaultdict(list)

    for m in group_matches:
        t1, t2 = m["team1"], m["team2"]
        s1 = get_score(t1, rankings)
        s2 = get_score(t2, rankings)
        p1 = win_prob(s1, s2)
        p2 = 1.0 - p1

        if p1 > GROUP_DRAW_HIGH:
            result = f"{t1} wins"
            stats[t1]["pts"] += 3
            stats[t1]["gd"]  += (p1 - 0.5) * 4
            stats[t1]["gf"]  += (p1 - 0.5) * 4
            stats[t2]["gd"]  -= (p1 - 0.5) * 4
        elif p1 < GROUP_DRAW_LOW:
            result = f"{t2} wins"
            stats[t2]["pts"] += 3
            stats[t2]["gd"]  += (p2 - 0.5) * 4
            stats[t2]["gf"]  += (p2 - 0.5) * 4
            stats[t1]["gd"]  -= (p2 - 0.5) * 4
        else:
            result = "Draw"
            stats[t1]["pts"] += 1
            stats[t2]["pts"] += 1

        group_results[m["group"]].append({
            "match_num": m.get("num"),
            "date": m.get("date", ""),
            "ground": m.get("ground", ""),
            "team1": t1,
            "team2": t2,
            "prob1": round(p1 * 100, 1),
            "prob2": round(p2 * 100, 1),
            "result": result,
        })

    # Build standings per group
    standings: dict[str, list] = {}
    for group in sorted(group_teams.keys()):
        teams_in_group = list(group_teams[group])
        sorted_teams = sorted(
            teams_in_group,
            key=lambda t: (stats[t]["pts"], stats[t]["gd"], get_score(t, rankings)),
            reverse=True,
        )
        standings[group] = [
            {
                "team": t,
                "pts": stats[t]["pts"],
                "gd": round(stats[t]["gd"], 2),
                "fifa_score": round(get_score(t, rankings), 2),
            }
            for t in sorted_teams
        ]

    return group_results, standings


# ---------------------------------------------------------------------------
# Step 5 – Determine advancing teams
# ---------------------------------------------------------------------------

def get_advancing_teams(standings: dict[str, list]) -> dict[str, str]:
    """
    Returns a mapping of slot → team name.
    Slots: '1A', '2A', ... '1L', '2L', and '3X' for best third-place teams.
    """
    slot_map: dict[str, str] = {}
    third_place: list[dict] = []

    for group, table in standings.items():
        letter = group.split()[-1]   # 'A', 'B', ...
        slot_map[f"1{letter}"] = table[0]["team"]
        slot_map[f"2{letter}"] = table[1]["team"]
        if len(table) >= 3:
            third_place.append({
                "slot_letter": letter,
                "team": table[2]["team"],
                "pts": table[2]["pts"],
                "gd": table[2]["gd"],
                "fifa_score": table[2]["fifa_score"],
            })

    # Best 8 third-place teams advance
    third_place.sort(
        key=lambda x: (x["pts"], x["gd"], x["fifa_score"]),
        reverse=True,
    )
    best_third = third_place[:8]
    for i, t in enumerate(best_third):
        slot_map[f"3{t['slot_letter']}"] = t["team"]

    return slot_map, best_third


# ---------------------------------------------------------------------------
# Step 6 – Knockout stage simulation
# ---------------------------------------------------------------------------

def simulate_knockout(matches: list[dict], rankings: dict[str, float],
                      slot_map: dict[str, str]) -> tuple[dict, dict]:
    """
    Simulate all knockout rounds.
    Returns:
        ko_results  – {match_num: result_dict}
        winner_map  – {match_num: team_or_list}  (list when uncertain)
    """
    ko_rounds = ["Round of 32", "Round of 16", "Quarter-final",
                 "Semi-final", "Match for third place", "Final"]
    ko_matches = [m for m in matches if m.get("round") in ko_rounds]

    # winner_map: match_num → winning team (or list of two if uncertain)
    winner_map: dict[int, object] = {}
    # loser_map for third-place match
    loser_map: dict[int, object] = {}
    ko_results: dict[str, list] = defaultdict(list)

    # Pre-resolve best-third slots: each '3X/Y/Z' reference gets a unique team.
    # We assign the best available third-place team from the listed groups,
    # consuming each team exactly once (highest-ranked first).
    # Build a pool of available best-third teams sorted best→worst.
    third_pool: list[tuple[str, str]] = []   # [(group_letter, team_name), ...]
    for key, team in slot_map.items():
        if re.match(r"^3[A-L]$", key):
            third_pool.append((key[1], team))   # ('A', 'Egypt'), etc.
    # Sort by FIFA score descending so best teams get assigned first
    third_pool.sort(key=lambda x: rankings.get(x[1], DEFAULT_SCORE), reverse=True)

    # Map each '3X/Y/Z' reference in Round of 32 to a specific team
    third_ref_map: dict[str, str] = {}
    used_letters: set[str] = set()

    # Collect all third-place references from Round of 32 matches
    r32_third_refs = []
    for m in ko_matches:
        if m.get("round") == "Round of 32":
            for ref in [m["team1"], m["team2"]]:
                if re.match(r"^3[A-L]", ref) and "/" in ref:
                    r32_third_refs.append(ref)

    # Assign best available team from each reference's allowed groups
    for ref in r32_third_refs:
        if ref in third_ref_map:
            continue
        allowed_letters = set()
        parts = ref.split("/")
        for p in parts:
            # Each part is like 'A', 'B', 'C/D/F' → take last char
            allowed_letters.add(p[-1])
        # Find best available team whose group letter is in allowed_letters
        for letter, team in third_pool:
            if letter in allowed_letters and letter not in used_letters:
                third_ref_map[ref] = team
                used_letters.add(letter)
                break
        else:
            # Fallback: pick any unused team
            for letter, team in third_pool:
                if letter not in used_letters:
                    third_ref_map[ref] = team
                    used_letters.add(letter)
                    break

    def resolve(ref: str) -> object:
        """Resolve a team reference like '1A', 'W73', 'L101', or a plain name."""
        if ref.startswith("W"):
            num = int(ref[1:])
            return winner_map.get(num, f"W{num}(TBD)")
        if ref.startswith("L"):
            num = int(ref[1:])
            return loser_map.get(num, f"L{num}(TBD)")
        # Best-third multi-group reference like '3A/B/C/D/F'
        if re.match(r"^3[A-L]", ref) and "/" in ref:
            return third_ref_map.get(ref, ref)
        # Simple slot like '1A', '2B', '3A'
        if re.match(r"^[123][A-L]$", ref):
            return slot_map.get(ref, ref)
        return slot_map.get(ref, ref)

    def team_score(team_or_list) -> float:
        if isinstance(team_or_list, list):
            return sum(get_score(t, rankings) for t in team_or_list) / len(team_or_list)
        return get_score(team_or_list, rankings)

    def team_label(team_or_list) -> str:
        if isinstance(team_or_list, list):
            return " / ".join(team_or_list)
        return team_or_list

    for m in ko_matches:
        t1_raw = m["team1"]
        t2_raw = m["team2"]
        t1 = resolve(t1_raw)
        t2 = resolve(t2_raw)

        s1 = team_score(t1)
        s2 = team_score(t2)
        p1 = win_prob(s1, s2)
        p2 = 1.0 - p1

        num = m.get("num")

        if p1 > KO_UNCERTAIN_HIGH:
            winner = t1
            loser  = t2
            result_str = f"{team_label(t1)} advances"
        elif p1 < KO_UNCERTAIN_LOW:
            winner = t2
            loser  = t1
            result_str = f"{team_label(t2)} advances"
        else:
            # Uncertain – list both
            if isinstance(t1, list) and isinstance(t2, list):
                winner = t1 + t2
            elif isinstance(t1, list):
                winner = t1 + [t2]
            elif isinstance(t2, list):
                winner = [t1] + t2
            else:
                winner = [t1, t2]
            loser = winner   # both could lose too
            result_str = f"⚠️ Uncertain: {team_label(t1)} ({p1*100:.1f}%) vs {team_label(t2)} ({p2*100:.1f}%)"

        if num:
            winner_map[num] = winner
            loser_map[num]  = loser

        # Compute intra-slot breakdown for uncertain multi-team slots
        def slot_breakdown(team_or_list) -> str | None:
            """Return 'TeamA X% / TeamB Y%' if slot has multiple teams."""
            if not isinstance(team_or_list, list) or len(team_or_list) < 2:
                return None
            total = sum(get_score(t, rankings) for t in team_or_list)
            parts = [f"{t} {get_score(t, rankings)/total*100:.0f}%" for t in team_or_list]
            return " / ".join(parts)

        ko_results[m["round"]].append({
            "num": num,
            "date": m.get("date", ""),
            "ground": m.get("ground", ""),
            "team1": team_label(t1),
            "team2": team_label(t2),
            "prob1": round(p1 * 100, 1),
            "prob2": round(p2 * 100, 1),
            "result": result_str,
            "winner": team_label(winner),
            "uncertain": p1 > KO_UNCERTAIN_LOW and p1 < KO_UNCERTAIN_HIGH,
            "t1_breakdown": slot_breakdown(t1),
            "t2_breakdown": slot_breakdown(t2),
        })

    return ko_results, winner_map


# ---------------------------------------------------------------------------
# Step 7 – Markdown renderer
# ---------------------------------------------------------------------------

def render_markdown(group_results, standings, best_third,
                    ko_results, winner_map) -> str:
    lines = []
    lines.append("# 🏆 FIFA 2026 World Cup Predictions\n")
    lines.append(f"> Predictions based on FIFA World Rankings scores (logistic model, k={K})\n")

    # ---- Group Stage ----
    lines.append("---\n")
    lines.append("# Group Stage\n")

    for group in sorted(group_results.keys()):
        lines.append(f"## {group}\n")
        lines.append("| # | Date | Venue | Team 1 | % | Team 2 | % | Result |")
        lines.append("|---|------|-------|--------|---|--------|---|--------|")
        for r in group_results[group]:
            num = r.get("match_num") or ""
            lines.append(
                f"| {num} | {fmt_date(r['date'])} | {r['ground']} "
                f"| **{r['team1']}** | {r['prob1']}% "
                f"| **{r['team2']}** | {r['prob2']}% "
                f"| {r['result']} |"
            )
        lines.append("")

        # Standings table
        lines.append("**Standings:**\n")
        lines.append("| Pos | Team | Pts | GD (est.) | FIFA Score |")
        lines.append("|-----|------|-----|-----------|------------|")
        table = standings[group]
        for i, row in enumerate(table):
            adv = " ✅" if i < 2 else (" 🔶" if i == 2 else "")
            lines.append(
                f"| {i+1} | {row['team']}{adv} | {row['pts']} "
                f"| {row['gd']} | {row['fifa_score']} |"
            )
        lines.append("")
        adv1 = table[0]["team"]
        adv2 = table[1]["team"]
        lines.append(f"> **Advance:** {adv1} (1st ✅), {adv2} (2nd ✅)\n")

    # Best third-place
    lines.append("## Best Third-Place Teams (advancing)\n")
    lines.append("| Pos | Group | Team | Pts | GD (est.) | FIFA Score |")
    lines.append("|-----|-------|------|-----|-----------|------------|")
    for i, t in enumerate(best_third):
        lines.append(
            f"| {i+1} | Group {t['slot_letter']} | {t['team']} 🔶 "
            f"| {t['pts']} | {t['gd']} | {t['fifa_score']} |"
        )
    lines.append("")

    # ---- Knockout Rounds ----
    ko_order = ["Round of 32", "Round of 16", "Quarter-final",
                "Semi-final", "Match for third place", "Final"]

    for rnd in ko_order:
        if rnd not in ko_results:
            continue
        lines.append("---\n")
        lines.append(f"# {rnd}\n")
        for r in ko_results[rnd]:
            num = r.get("num") or ""
            fd = fmt_date(r['date'])
            header = f"## M{num} — {fd} | {r['ground']}" if num else f"## {fd} | {r['ground']}"
            lines.append(header)
            # Simplified match line: icon + teams + probabilities
            if r.get("uncertain"):
                lines.append(f"- 🏅 ⚠️ **{r['team1']}** {r['prob1']}%  vs  **{r['team2']}** {r['prob2']}%")
            else:
                lines.append(f"- 🏅 **{r['team1']}** {r['prob1']}%  vs  **{r['team2']}** {r['prob2']}%  → **{r['winner']}** advances")
            # Intra-slot breakdown lines when a slot has multiple teams
            if r.get("t1_breakdown"):
                lines.append(f"  - *(slot 1 breakdown: {r['t1_breakdown']})*")
            if r.get("t2_breakdown"):
                lines.append(f"  - *(slot 2 breakdown: {r['t2_breakdown']})*")
            lines.append("")

    # Champion
    final_results = ko_results.get("Final", [])
    if final_results:
        champion = final_results[0]["winner"]
        lines.append("---\n")
        lines.append(f"# 🥇 Predicted Champion: **{champion}**\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    html_path  = os.path.join(base, "data", "fifa_world_rank_20260327.html")
    json_path  = os.path.join(base, "data", "worldcup.json")
    output_path = os.path.join(base, "results.md")

    print("Loading FIFA rankings...")
    rankings = load_rankings(html_path)
    print(f"  Loaded {len(rankings)} teams.")

    print("Loading match schedule...")
    matches = load_schedule(json_path)
    print(f"  Loaded {len(matches)} matches.")

    print("Simulating group stage...")
    group_results, standings = simulate_group_stage(matches, rankings)

    print("Determining advancing teams...")
    slot_map, best_third = get_advancing_teams(standings)

    print("Simulating knockout stage...")
    ko_results, winner_map = simulate_knockout(matches, rankings, slot_map)

    print("Rendering Markdown...")
    md = render_markdown(group_results, standings, best_third, ko_results, winner_map)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n✅ Done! Results written to: {output_path}")

    # Also print to stdout
    print("\n" + "="*60 + "\n")
    print(md)


if __name__ == "__main__":
    main()
