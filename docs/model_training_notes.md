# Model Training Notes

The current trained model is version 2 of the scoring pipeline. It is still intentionally explainable, but it is stronger than the first pass because it combines dbt-built form features with a Python-computed Elo rating system.

## How dbt Fits In

dbt is responsible for preparing clean, tested analytics tables:

- `main_features.features_historical_match_training`: one historical match per row, with prior-form features and target scores.
- `main_marts.mart_team_strength`: one row per team, with recent form as of the 2026 tournament start.
- `main_staging.stg_group_fixtures`: the 72 known group matches, with stale DataCamp playoff placeholders resolved.
- `main_staging.stg_knockout_slots`: the 32 bracket slots.
- `main_staging.stg_international_results`: historical results used by the Python Elo pass.
- `main_marts.mart_squad_strength`: one row per team with current squad experience and international-pedigree scores when a squad table has been published.
- `main_marts.mart_team_event_profile`: one row per team with corners and card-risk features.
- `main_marts.mart_latest_fifa_rankings`: the latest FIFA ranking snapshot for 2026 scoring.
- `main_staging.stg_international_match_features`: external historical match features with Elo, form, and player aggregate signals.
- `main_marts.mart_external_player_strength`: latest external country-level player aggregate rating for 2026 scoring.

Python then reads those dbt outputs from DuckDB. This is the usual analytics engineering pattern: dbt owns reproducible feature preparation, while Python owns model training and prediction logic.

## Model

Run:

```powershell
.\.venv\Scripts\python.exe src\train_model.py
```

The script trains separate home-goal and away-goal models. It compares two candidate model families:

- Poisson regression with scaled numeric features.
- Histogram gradient boosting with Poisson loss.

The selected model is the candidate with the lowest holdout average goal MAE.

## Features

The model uses:

- Elo opponent-adjusted prior-10-match points and goal difference for both teams
- home minus away differences for those adjusted-form features
- prior-10-match goals for and goals against for both teams
- neutral-site flag, including host advantage for Canada, Mexico, and the United States
- point-in-time FIFA rank and FIFA ranking points for both teams
- FIFA rank and points differences
- pre-match Elo rating for both teams
- Elo difference and the Elo expected home result
- external match-feature signals for the direct outcome model only: external Elo, EA Sports/FIFA-style player aggregate ratings, star-power differentials, and external form fields

Raw recent form is still visible in the dbt marts, but the trained goal and outcome models now use the Elo-adjusted version instead. Adjusted form is calculated as actual recent performance above or below the expected result implied by the opponent's pre-match Elo. This prevents a team from receiving the same form credit for beating weak opposition that it would receive for beating an elite opponent.

After the trained model estimates expected goals, Python applies a small capped squad overlay for 2026 matches. This overlay compares each team's international-pedigree z-scores:

- overall international pedigree
- attacking production from goals and top scorers
- defensive experience from goalkeeper and defender caps
- total squad experience

This is deliberately a post-model adjustment, not a trained feature, because we do not have historical squad snapshots for every past match. Teams without published squad tables receive no squad adjustment until the source page adds their roster.

dbt resolves known playoff placeholders before prediction and exposes model team names for joins to the historical source. Python keeps a small fallback alias layer for names that can still differ between display and historical data, such as `USA`, `Cabo Verde`, and `Cote d'Ivoire`.

The pipeline now trains a separate direct outcome model for `home`, `draw`, and `away`. This outcome model gets the external player aggregate match features and three dbt-built star-power differentials: overall star power, superstar gap, and attacking star power. The goal models keep the cleaner dbt/FIFA/Elo feature set. The final scoreline comes from a blended score grid: Python builds independent Poisson probabilities for every plausible scoreline, then reweights each score by the direct outcome probability for that scoreline's result. The selected score determines the final group-stage `winning_team`, so the output stays internally consistent without letting the classifier force an implausible winner by itself.

The star-power feature was only promoted after an A/B pass. Adding the three summary differentials lifted holdout direct outcome accuracy from about `62.4%` to `62.8%`, blended scoreline outcome accuracy from about `62.4%` to `62.6%`, and exact score accuracy from about `14.7%` to `14.9%`. Larger star-power bundles were not used because they became redundant with the existing raw player aggregate fields.

For current 2026 scoring, dbt now replaces the older country-level star proxy with a roster-level top-league player signal where the squad can be matched. This signal uses post-2022-World-Cup appearances in covered top leagues, league-adjusted goal contribution per 90, sample reliability, current market value, peak market value, and reliable international goal rate. This changed the current prediction set slightly without changing the historical holdout metrics, because the historical training fold still uses the original point-in-time external match-feature source.

The external match-feature source includes context flags such as `is_neutral`, but those flags behaved like fixture-order leakage for neutral tournament matches. The outcome model therefore uses the external strength and form fields, but excludes those external context flags. Model selection and calibration use a 2018-2021 tournament-focused validation slice made from World Cups, continental championships, Nations League-style competitions, and their qualifiers. The direct outcome draw threshold and the blended scoreline weight both use a minimum predicted draw-rate guardrail, which sacrifices a small amount of pure accuracy to avoid unrealistic no-draw tournament forecasts.

Group standings use standard points, goal difference, and goals-for ordering. If teams remain tied after those fields, the prediction pipeline uses model tiebreak strength instead of alphabetical order. This is a proxy for official fair-play or drawing-lots tiebreakers that are not knowable before the tournament.

The deterministic bracket remains the submission artifact, but the pipeline also runs repeated full-tournament simulations. Each run samples group-stage scorelines from the calibrated scoreline probability grid, rebuilds the group table, resolves the dynamic knockout bracket, samples knockout scorelines, and resolves tied knockout matches as penalties. This does not change validation accuracy by itself; it quantifies uncertainty around the single submitted path.

The simulation layer also produces a route difficulty metric. For each team, Python tracks the strength of knockout opponents faced on championship-winning simulation paths, then scales that average opponent strength from 0 to 100 across the field. Higher values mean a harder projected title route.

Corners and cards now come from a separate event profile rather than fixed constants:

- Corners use weighted team-level FootyStats event rates from World Cup qualifiers and recent World Cups.
- Yellow cards blend team-level international card rates with matched squad-player club discipline from the 2025/26 top-five European leagues.
- Red cards use the same blended logic, but the final prediction is intentionally conservative because red cards are rare.

## Evaluation

The train/holdout split is time-based:

- Training rows: matches before `2022-01-01`
- Holdout rows: matches from `2022-01-01` onward

Current v2 holdout metrics:

```text
Selected model: poisson_regression
Selected outcome model: hist_gradient_boosting_classifier
Holdout rows: 4,001
Holdout home goals MAE: 0.985
Holdout away goals MAE: 0.829
Holdout average goals MAE: 0.907
Raw rounded exact score accuracy: 0.106
Raw rounded match outcome accuracy: 0.547
Direct outcome accuracy: 0.628
Blended scoreline outcome accuracy: 0.626
Blended exact score accuracy: 0.149
Selected draw threshold: 0.35
Selected scoreline/outcome blend weight: 0.30
```

For comparison, v1 had holdout match outcome accuracy of about `0.482`. Replacing raw recent form with Elo-adjusted form lifted direct outcome accuracy above the 62% target. The blended Poisson scoreline selector also clears the 62% outcome target, keeps exact-score accuracy above the stretch target, and produces a more realistic final outcome distribution than hard-forcing every scoreline to match the classifier's top result.

## Target Metrics

These are working targets for this project, not guarantees. The guardrail is the minimum rating we should try to stay above, the target is the next realistic milestone, and the stretch number is where the model would start looking genuinely strong for a public-data international soccer forecast without betting odds.

| Metric | Current | Guardrail | Target | Stretch | Direction |
| --- | ---: | ---: | ---: | ---: | --- |
| Raw rounded scoreline outcome accuracy | 54.7% | 54.5% | 57.0% | 60.0% | Higher is better |
| Direct outcome accuracy | 62.8% | 58.0% | 62.0% | 65.0% | Higher is better |
| Reconciled scoreline exact accuracy | 14.9% | 10.0% | 12.0% | 14.0% | Higher is better |
| Average goals MAE | 0.907 | 0.950 | 0.900 | 0.860 | Lower is better |

The metrics JSON includes these same target bands under `metric_targets`, with a status for each metric.

## Outputs

The model writes:

```text
data/processed/model_group_predictions_v2.csv
data/processed/model_knockout_predictions_v2.csv
data/processed/model_predictions_v2.csv
data/processed/model_team_features_v2.csv
data/processed/model_tournament_simulation_v2.csv
data/processed/model_metrics_v2.json
```

`model_group_predictions_v2.csv` and `model_knockout_predictions_v2.csv` match the two DataCamp workbook sections. `model_predictions_v2.csv` combines all 104 matches for local analysis. `model_team_features_v2.csv` publishes the Python-owned Elo and adjusted-form team features into the BI layer. `model_tournament_simulation_v2.csv` publishes team-level advancement and championship probabilities for the dashboard.

## Known Limitations

- Club player discipline coverage is strongest for countries with many players in the Premier League, La Liga, Bundesliga, Serie A, and Ligue 1.
- Corners are still team-level, not player-level, because the competition asks for total match corners and player corner attribution is much less useful for this target.
- FIFA rankings start in 1992, so the ranking-enhanced training set excludes older historical matches.
- External player aggregate ratings are a proxy from the Kaggle match-feature dataset, not official current squad ratings. Current squad star power is now improved with a Transfermarkt-style top-league roster signal, but that source still lacks EFL Championship appearances.
- The calibrated scoreline blend still underpredicts draws relative to the historical holdout distribution, but it no longer collapses the tournament forecast into almost all home wins.
- International pedigree comes from currently published squad tables, so coverage is partial until all teams announce squads.
- Knockout scores use the same goal model, then resolve tied rounded scorelines as penalty matches.
- This is a strong first modeling baseline, not a final betting-grade forecast.
