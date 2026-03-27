# Design Document: FIFA 2026 World Cup Bracket Predictor

## 1. Overview

This tool predicts the outcomes of all FIFA 2026 World Cup knockout stage matches by simulating the entire tournament from the group stage onward. Since the actual knockout bracket depends on group stage results, the tool first simulates the group stage, then propagates winners through the knockout rounds. Predictions are based on FIFA World Rankings (using ranking scores, not just positions).

---

## 2. Background & Motivation

The user wants to purchase tickets for the 2026 FIFA World Cup knockout stage matches but cannot know in advance which teams will play in which match. This tool simulates the full tournament to predict the most likely matchups, helping the user decide which games to attend.

---

## 3. Goals

- Simulate all 2026 FIFA World Cup group stage matches and determine group standings.
- Simulate all knockout stage matches (Round of 32, Round of 16, Quarterfinals, Semifinals, Final).
- Use FIFA World Ranking **scores** (not just rank positions) to compute win probabilities.
- Handle ties appropriately:
  - **Group stage**: draws are allowed; close matches result in a draw (1 point each).
  - **Knockout stage**: no draws; close matches result in both teams being listed as possible winners.
- Output results in a clean, readable Markdown format.

---

## 4. Non-Goals

- Real-time data fetching (FIFA ranking data will be embedded or loaded from a local file).
- Accounting for injuries, form, home advantage, or other non-ranking factors.
- Providing betting odds or financial advice.

---

## 5. Data Sources

### 5.1 FIFA World Rankings

- Source: [FIFA World Rankings](https://www.fifa.com/fifa-world-ranking)
- Each team has a **ranking score** (e.g., Argentina ~1900 pts, a lower-ranked team ~900 pts).
- The score difference is a better proxy for team strength gap than rank position difference.
- Data will be stored in a local Python dictionary or JSON file: `fifa_rankings.json`.

### 5.2 2026 World Cup Group Draw

- The 2026 World Cup features **48 teams** in **12 groups** (Groups A–L), with 3 or 4 teams per group.
  - Groups A–H: 4 teams each (8 groups × 4 = 32 teams)
  - Groups I–L: 4 teams each (4 groups × 4 = 16 teams)
  - Total: 48 teams across 12 groups of 4
- The actual draw results will be stored in a local data file: `groups.json`.

---

## 6. Prediction Algorithm

### 6.1 Win Probability from FIFA Scores

Given two teams with FIFA scores `S_A` and `S_B`, compute the win probability for Team A using a **logistic (sigmoid) function** on the score difference:

```
delta = S_A - S_B
P(A wins) = 1 / (1 + exp(-delta / k))
```

Where `k` is a scaling constant (e.g., `k = 200`) that controls how sensitive the probability is to score differences. This ensures:
- A large score gap → high win probability for the stronger team.
- A small score gap → probability close to 50/50.

### 6.2 Group Stage Match Prediction

For each match in the group stage:

| Condition | Result |
|---|---|
| `P(A wins) > threshold_high` (e.g., > 0.65) | Team A wins (3 pts for A, 0 for B) |
| `P(A wins) < threshold_low` (e.g., < 0.35) | Team B wins (3 pts for B, 0 for A) |
| Otherwise | Draw (1 pt each) |

### 6.3 Group Stage Standings

After simulating all matches in a group:
1. Sort teams by **points** (descending).
2. Tiebreaker: **goal difference** (approximated from win probability margin).
3. Top 2 teams advance from each group.
4. Additionally, the **best 8 third-place teams** across all 12 groups also advance (as per 2026 format), bringing the Round of 32 to 32 teams.

### 6.4 Knockout Stage Match Prediction

For each knockout match:

| Condition | Result |
|---|---|
| `P(A wins) > threshold_high` (e.g., > 0.60) | Team A advances |
| `P(A wins) < threshold_low` (e.g., < 0.40) | Team B advances |
| Otherwise | **Both teams listed** as possible winners (uncertain outcome) |

When both teams are listed as possible winners, downstream matches will branch or show both possibilities.

---

## 7. Tournament Structure (2026 Format)

### 7.1 Group Stage
- 12 groups (A–L), 4 teams each = 48 teams.
- Each team plays 3 matches (round-robin within group).
- Top 2 from each group + best 8 third-place teams = **32 teams** advance.

### 7.2 Knockout Bracket

```
Round of 32  (32 teams → 16 teams)  — 16 matches
Round of 16  (16 teams → 8 teams)   — 8 matches
Quarterfinals (8 teams → 4 teams)   — 4 matches
Semifinals   (4 teams → 2 teams)    — 2 matches
Third Place  (2 losers)             — 1 match
Final        (2 teams → 1 champion) — 1 match
```

### 7.3 Bracket Seeding (Round of 32)

The Round of 32 matchups follow the official FIFA 2026 bracket seeding rules:
- Group winners are matched against third-place teams or runners-up from specific groups.
- The exact bracket pairings will be encoded in a `bracket.json` file based on the official FIFA schedule.

---

## 8. Output Format

Results are printed to stdout (and optionally saved to `results.md`) in Markdown:

```markdown
# FIFA 2026 World Cup Predictions

## Group Stage

### Group A
| Match | Team A | Score | Team B | Result |
|-------|--------|-------|--------|--------|
| M1    | USA    | 75%   | Wales  | USA wins |
| M2    | England| 55%   | Iran   | Draw |
| ...   |        |       |        |        |

**Standings:**
1. USA — 6 pts
2. England — 4 pts
3. Iran — 1 pt
4. Wales — 0 pts

**Advance:** USA (1st), England (2nd)

...

## Round of 32

### M37 — June 28, Sun, Los Angeles
Teams: **1A (USA)** vs **2B (Netherlands)**
Prediction: USA 68% vs Netherlands 32%
**Winner: USA**

...

## Round of 16
...

## Quarterfinals
...

## Semifinals
...

## Final
...

## 🏆 Predicted Champion: [Team Name]
```

---

## 9. Module Design

```
world_cup/
├── task_intro.txt
├── design_doc.md          ← this file
├── fifa_rankings.json     ← FIFA ranking scores per team
├── groups.json            ← 2026 group draw assignments
├── bracket.json           ← knockout bracket seeding rules + match schedule
├── predictor.py           ← main script
│   ├── load_data()
│   ├── compute_win_probability(score_a, score_b, k=200)
│   ├── simulate_group_stage(groups, rankings)
│   ├── get_advancing_teams(group_results)
│   ├── simulate_knockout_round(matches, rankings)
│   ├── simulate_tournament()
│   └── render_markdown(results)
└── results.md             ← generated output
```

### Key Functions

| Function | Description |
|---|---|
| `load_data()` | Loads rankings, groups, and bracket from JSON files |
| `compute_win_probability(s_a, s_b, k)` | Returns P(A wins) using logistic function |
| `simulate_group_stage()` | Runs all group matches, returns standings |
| `get_advancing_teams()` | Selects top 2 per group + best 8 third-place |
| `simulate_knockout_round()` | Runs one knockout round, handles uncertain outcomes |
| `simulate_tournament()` | Orchestrates full tournament simulation |
| `render_markdown()` | Formats and outputs results as Markdown |

---

## 10. Configuration Parameters

| Parameter | Default | Description |
|---|---|---|
| `k` | `200` | Logistic scaling factor for score difference |
| `group_draw_threshold` | `0.35 / 0.65` | Probability range for group stage draws |
| `knockout_uncertain_threshold` | `0.40 / 0.60` | Probability range for uncertain knockout outcomes |
| `output_file` | `results.md` | Output file path |

---

## 11. Edge Cases & Considerations

1. **Ties in group standings**: Use goal difference (approximated) or head-to-head as tiebreaker.
2. **Uncertain knockout outcomes**: When two teams are very close in ranking, both are listed as possible winners. Downstream matches show both branches or use the average probability.
3. **Missing ranking data**: If a team's FIFA score is not found, fall back to a default low score (e.g., 500) and log a warning.
4. **Third-place team selection**: Rank all 12 third-place teams by points, then goal difference, then FIFA score to select the best 8.

---

## 12. Implementation Plan

| Step | Task | Notes |
|---|---|---|
| 1 | Collect FIFA ranking scores for all 48 teams | Embed in `fifa_rankings.json` |
| 2 | Encode 2026 group draw | Embed in `groups.json` |
| 3 | Encode official knockout bracket seeding | Embed in `bracket.json` |
| 4 | Implement `compute_win_probability()` | Logistic function |
| 5 | Implement `simulate_group_stage()` | Round-robin + standings |
| 6 | Implement `get_advancing_teams()` | Top 2 + best 8 third-place |
| 7 | Implement `simulate_knockout_round()` | Handle uncertain outcomes |
| 8 | Implement `render_markdown()` | Format output |
| 9 | End-to-end test | Verify output format |

---

## 13. Example Probability Calculation

**Example**: Argentina (FIFA score: 1900) vs Saudi Arabia (FIFA score: 1100)

```
delta = 1900 - 1100 = 800
k = 200
P(Argentina wins) = 1 / (1 + exp(-800/200)) = 1 / (1 + exp(-4)) ≈ 98.2%
→ Argentina wins convincingly.
```

**Example**: France (FIFA score: 1850) vs Portugal (FIFA score: 1800)

```
delta = 1850 - 1800 = 50
k = 200
P(France wins) = 1 / (1 + exp(-50/200)) = 1 / (1 + exp(-0.25)) ≈ 56.2%
→ Close match; in knockout stage, both teams listed as possible winners.
```

---

*Document version: 1.0 | Date: 2026-03-27*
