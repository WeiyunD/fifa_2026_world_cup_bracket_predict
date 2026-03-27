# FIFA 2026 World Cup Bracket Predictor

## Purpose

Buying tickets to a World Cup knockout match is tricky — you don't know which teams will be playing until the group stage is over. This tool helps you make a more informed decision by **simulating the entire tournament** and predicting the most likely matchups for every knockout game, so you can identify which matches are worth attending before purchasing tickets.

## How It Works

1. **FIFA World Ranking scores** (not just positions) are used to measure the true strength gap between teams. A logistic (sigmoid) function converts score differences into win probabilities — so the gap between rank #1 and #10 is treated as much larger than #50 vs #60.
2. **Group stage** is simulated with draws allowed when two teams are closely matched (win probability between 35–65%).
3. **32 teams advance**: top 2 from each of the 12 groups, plus the best 8 third-place teams.
4. **Knockout rounds** (Round of 32 → Round of 16 → Quarterfinals → Semifinals → Final) are simulated with no draws. When two teams are very close (40–60%), both are listed as possible winners so you can see the uncertainty.
5. Results are written to `results.md` in a clean Markdown format with match dates, venues, win probabilities, and predicted winners.

## Data Files

| File | Description |
|------|-------------|
| `data/fifa_world_rank_20260327.html` | FIFA World Rankings page (downloaded Mar 27, 2026) |
| `data/worldcup.json` | Full 2026 World Cup match schedule (104 matches) |

## How to Run

Make sure you have **Python 3.10+** installed, then:

```bash
python predictor.py
```

The predictions will be printed to the console and saved to **`results.md`**.

## Output Format

```
# Group Stage
## Group A
| Date       | Venue      | Team 1  | %    | Team 2       | %    | Result      |
|------------|------------|---------|------|--------------|------|-------------|
| Thu Jun 11 | Mexico City | Mexico | 77.8%| South Africa | 22.2%| Mexico wins |
...

# Round of 32
## M73 — Sun Jun 28 | Los Angeles (Inglewood)
- 🏅 ⚠️ **South Korea** 55.0%  vs  **Canada** 45.0%

# Final
## Sun Jul 19 | New York/New Jersey (East Rutherford)
- 🏅 ⚠️ **France / Spain** 52.7%  vs  **England / Argentina** 47.3%
```

## Configuration

You can tune the prediction sensitivity in `predictor.py`:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `K` | `200` | Logistic scale — lower = more upsets, higher = stronger teams always win |
| `GROUP_DRAW_LOW / HIGH` | `0.35 / 0.65` | Probability range that results in a group stage draw |
| `KO_UNCERTAIN_LOW / HIGH` | `0.40 / 0.60` | Probability range that marks a knockout match as uncertain |

---

## ⚠️ Disclaimer

- This tool is for **entertainment and ticket-planning purposes only**.
- Predictions are based solely on FIFA World Ranking scores and a simple statistical model. They do **not** account for injuries, team form, tactics, home advantage, or any other real-world factors.
- **This is not gambling advice.** Do not use these predictions for betting or wagering of any kind.
- Actual match results may differ significantly from predictions. The World Cup is famously unpredictable — that's what makes it great!
- FIFA ranking data is a snapshot from March 27, 2026 and may not reflect the latest standings.
