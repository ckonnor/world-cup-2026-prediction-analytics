# FIFA World Cup 2026 Prediction Analytics

This project started as a DataCamp competition entry and grew into an analytics engineering portfolio project. The goal was to predict every match in the 2026 FIFA World Cup, then build the kind of tested data pipeline and reporting layer that would make those predictions explainable.

The final project combines dbt, DuckDB, and Python to turn raw soccer data into model-ready features, tournament predictions, validation checks, and dashboard-ready datasets.

## What This Project Does

The competition asks for predictions across all 104 World Cup matches:

- exact scorelines
- match winners
- knockout matchups
- penalty shootout flags
- total corners
- yellow cards
- red cards

Instead of filling those values manually, this project builds a full pipeline around them:

1. Clean and standardize the raw competition fixtures.
2. Add external soccer data: historical international results, FIFA rankings, squad data, player-strength proxies, and event data for cards/corners.
3. Use dbt to build tested staging, intermediate, mart, feature, and BI models.
4. Train Python models for goals and outcomes.
5. Simulate the group stage and knockout bracket.
6. Export validated competition files and dashboard-ready CSVs.

## Why dbt Matters Here

The core analytics engineering work is in dbt. The project is intentionally layered so each step has a clear purpose:

- **Staging models** clean source files and standardize names, dates, and types.
- **Intermediate models** reshape raw match data into reusable concepts, such as team-match rows and rolling form.
- **Mart models** publish analyst-facing tables like team strength, squad strength, FIFA rankings, and event profiles.
- **Feature models** produce model-ready training and scoring tables.
- **BI models** reshape the final outputs into dashboard-friendly tables.

This separation keeps the modeling code from becoming a tangle of raw CSV joins. Python consumes tested dbt outputs instead of raw source files.

## Data Sources

The project uses a mix of competition data and public soccer datasets:

- DataCamp World Cup group fixtures and knockout slots
- historical international match results
- FIFA men's ranking history
- current squad/player tables where available
- international match-event data for corners and cards
- club player discipline data
- external country-level player aggregate features

One important modeling choice is point-in-time feature engineering. Historical training rows only use information that would have been available before each match. That matters because future rankings or future form would make the model look better than it really is.

## Modeling Approach

The prediction layer uses a blend of statistical modeling and tournament simulation:

- Poisson regression estimates home and away expected goals.
- A direct outcome classifier estimates home/draw/away probabilities.
- A calibrated scoreline selector blends exact-score likelihood with outcome probabilities.
- A conservative squad overlay adjusts expected goals based on available squad strength.
- Corners and cards come from dbt-built team event profiles.
- Knockout rounds are resolved sequentially from predicted group standings.

The final scoreline drives the published winner labels, so the output stays internally consistent. For example, a predicted `1-1` group-stage match is always labeled as a draw.

## Current Model Results

The latest stable validation metrics are:

| Metric | Result |
| --- | ---: |
| Direct outcome accuracy | 62.4% |
| Blended scoreline outcome accuracy | 62.4% |
| Exact score accuracy | 14.7% |
| Average goals MAE | 0.907 |

Those numbers are not betting-grade, but they are realistic for a public-data international soccer forecast without market odds. Exact score prediction is especially hard, so the model is intentionally conservative with scorelines.

The current simulated tournament winner is Spain over Argentina, with France finishing third.

## Validation And Quality Checks

The project includes both dbt tests and Python tests.

dbt checks cover things like:

- expected row counts for fixtures and BI tables
- uniqueness of match/team keys
- missing values in important feature columns
- accepted values for categorical fields
- resolved playoff placeholders
- point-in-time ranking coverage
- training-feature leakage checks

Python tests cover:

- tournament standings logic
- scoreline/outcome consistency
- DataCamp submission validation
- BI export shaping
- model helper functions
- dashboard snapshot contracts

At the time of the latest commit:

```text
dbt build: PASS=272 WARN=0 ERROR=0
pytest: 22 passed
```

GitHub Actions also parses the dbt project, validates Python and Streamlit syntax, runs the test suite, and uploads dbt parse artifacts for lineage inspection.

## Dashboard Layer

The project also includes an interactive Streamlit dashboard and dashboard-ready extracts for a BI tool such as Looker Studio. The dashboard layer is separate from the model-training layer because dashboard tables should be easy to explain, filter, and visualize.

The BI exports include:

- match predictions
- predicted group standings
- team profile comparisons
- match feature context
- model metric targets
- data quality checks
- historical competition summaries

The intended dashboard tells the story behind the predictions: who advances, why certain teams are favored, where the model sees close matches, and how complete the underlying data is.

The Streamlit app lives in:

```text
app/streamlit_app.py
```

It reads a committed dashboard snapshot from `app/data/`, which makes it lightweight enough to host on Streamlit Community Cloud without rebuilding the full DuckDB/dbt/modeling pipeline.

## Repository Guide

Useful places to start:

- `dbt_world_cup/models/`: dbt transformations
- `app/streamlit_app.py`: interactive dashboard app
- `src/train_model.py`: model training and tournament simulation
- `src/export_datacamp_submission.py`: final competition export validation
- `src/export_bi_assets.py`: BI/dashboard export generation
- `docs/architecture.md`: system architecture and layer responsibilities
- `docs/metrics_and_contracts.md`: metric definitions and dashboard data contracts
- `docs/operations_and_deployment.md`: CI, refresh, and deployment operating model
- `docs/dbt_docs_and_lineage.md`: dbt docs and lineage guidance
- `docs/dbt_learning_notes.md`: walkthrough of the dbt layers
- `docs/model_training_notes.md`: modeling notes and metrics
- `docs/dashboard_guide.md`: dashboard plan and BI export definitions
- `docs/resume_project_positioning.md`: portfolio framing

Raw source files, the local DuckDB warehouse, and generated CSV outputs are not committed to the repo. The repository focuses on the pipeline, transformations, tests, documentation, and modeling logic.

## Production Readiness

The project is still a portfolio project, but it now includes the operating pieces expected in a professional analytics workflow:

- layered dbt transformations with model tests and custom assertions
- point-in-time feature engineering to avoid historical leakage
- CI validation for dbt parsing, Python tests, dashboard contracts, and Streamlit syntax
- committed dashboard snapshots for lightweight public hosting
- architecture, lineage, metric, contract, and deployment documentation
- a stakeholder-facing Streamlit dashboard that explains the forecast rather than only exposing tables

## Portfolio Framing

The resume story for this project is not just "I predicted soccer matches." It is:

> Built a reproducible analytics engineering pipeline for FIFA World Cup forecasting using Python, DuckDB, and dbt; integrated multiple public soccer datasets; created tested marts and feature tables; trained calibrated prediction models; validated competition-ready outputs; and produced dashboard-ready BI extracts for analysis and storytelling.

That is the shape of the work: data engineering, analytics modeling, quality checks, machine learning, and BI presentation in one cohesive project.
