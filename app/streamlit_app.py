from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

PHASE_LABELS = {
    "group": "Group stage",
    "knockout": "Knockout stage",
}
ROUND_ORDER = [
    "Round of 32",
    "Round of 16",
    "Quarter-final",
    "Semi-final",
    "Final",
    "Third-place playoff",
]
PALETTE = {
    "ink": "#0f172a",
    "muted": "#64748b",
    "border": "#e2e8f0",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "cyan": "#14b8a6",
    "orange": "#f97316",
    "amber": "#f59e0b",
    "rose": "#dc2626",
    "surface": "#ffffff",
    "subtle": "#f8fafc",
}
PLOT_CONFIG = {"displayModeBar": False}
PROJECT_PILLARS = [
    (
        "Data product",
        "Published BI layer",
        "A public dashboard reads committed BI extracts, while raw files and the DuckDB warehouse stay local.",
        "Separates stakeholder consumption from private source files.",
    ),
    (
        "dbt ownership",
        "Auditable SQL transformations",
        "dbt handles source cleanup, point-in-time feature engineering, marts, BI contracts, and quality checks.",
        "Keeps the transformation layer out of ad hoc notebook logic.",
    ),
    (
        "Model discipline",
        "Consistent predictions",
        "Python trains expected-goal and outcome models, then reconciles them through calibrated score grids.",
        "Keeps the final scoreline, winner, and bracket in agreement.",
    ),
    (
        "Competition realism",
        "Conservative scorelines",
        "The final scoring mix favors common tournament scorelines such as 1-0, 1-1, and 2-1.",
        "Exact scores are noisy, so realism matters alongside confidence.",
    ),
]
PIPELINE_STEPS = [
    (
        "1",
        "Raw sources",
        "DataCamp fixtures, Kaggle international results, FIFA rankings, squads, corners, and cards.",
    ),
    (
        "2",
        "dbt staging",
        "Normalize names, parse dates, preserve source fields, and resolve 2026 playoff placeholders.",
    ),
    (
        "3",
        "dbt marts",
        "Publish team strength, latest rankings, squad strength, event profiles, and fixture tables.",
    ),
    (
        "4",
        "Feature layer",
        "Build historical training rows and 2026 scoring rows with point-in-time feature integrity.",
    ),
    (
        "5",
        "Python model",
        "Train goal and outcome models, calibrate scorelines, simulate groups, and resolve the bracket.",
    ),
    (
        "6",
        "BI contracts",
        "Export dashboard snapshots, model metrics, quality checks, and DataCamp-ready submission files.",
    ),
]
MODEL_LAYERS = [
    (
        "Expected goals",
        "Poisson regression predicts home and away goals from dbt-built form, ranking, Elo, and host features.",
    ),
    (
        "Direct outcome",
        "A classifier estimates home, draw, and away probabilities with stronger player aggregate signals.",
    ),
    (
        "Reconciled scoreline",
        "A Poisson score grid is reweighted by outcome probability so the submitted score and winner agree.",
    ),
    (
        "Tournament simulator",
        "Group tables drive knockout participants, and tied knockout scorelines are resolved as penalties.",
    ),
]
TARGET_RATIONALE = [
    (
        "Blended outcome",
        "Primary",
        "This is the cleanest final-answer metric because the competition submission is an exact scoreline, but that scoreline must still imply the right winner or draw.",
    ),
    (
        "Direct outcome",
        "Benchmark",
        "This isolates the winner-picking model from score rounding. Around 62% is a realistic public-data target for international soccer without betting odds or live injury news.",
    ),
    (
        "Exact score",
        "High-value",
        "Exact scores are volatile but heavily rewarded. The model intentionally keeps many results near common low-scoring outcomes such as 1-0 and 1-1.",
    ),
    (
        "Goals MAE",
        "Guardrail",
        "MAE prevents the model from gaming exact-score frequency by predicting the same conservative result everywhere.",
    ),
]

px.defaults.template = "plotly_white"


st.set_page_config(
    page_title="World Cup 2026 Prediction Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
        :root {
            --ink: #0f172a;
            --muted: #64748b;
            --border: #e2e8f0;
            --surface: #ffffff;
            --subtle: #f8fafc;
            --blue: #2563eb;
            --teal: #0f766e;
            --cyan: #14b8a6;
            --orange: #f97316;
            --amber: #f59e0b;
            --rose: #dc2626;
        }
        .block-container {
            padding-top: 1.15rem;
            padding-bottom: 2.5rem;
            max-width: 1260px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        div[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--border);
        }
        div[data-testid="stTabs"] button p {
            font-size: 0.92rem;
            font-weight: 560;
        }
        .app-header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
            margin-bottom: 1rem;
        }
        .eyebrow {
            color: var(--teal);
            font-size: 0.78rem;
            font-weight: 760;
            letter-spacing: 0.08em;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
        }
        .title-row {
            display: flex;
            justify-content: space-between;
            gap: 1.25rem;
            align-items: flex-end;
        }
        .app-title {
            color: var(--ink);
            font-size: 2.35rem;
            font-weight: 760;
            line-height: 1.05;
            margin: 0;
            max-width: 45rem;
        }
        .app-subtitle {
            color: var(--muted);
            font-size: 0.98rem;
            line-height: 1.48;
            margin: 0.7rem 0 0;
            max-width: 58rem;
        }
        .stack-pills {
            display: flex;
            gap: 0.4rem;
            justify-content: flex-end;
            flex-wrap: wrap;
            min-width: 15rem;
        }
        .pill {
            border: 1px solid var(--border);
            border-radius: 999px;
            color: #334155;
            background: var(--subtle);
            font-size: 0.75rem;
            font-weight: 660;
            padding: 0.28rem 0.58rem;
            white-space: nowrap;
        }
        .section-head {
            margin: 1.25rem 0 0.75rem;
        }
        .section-title {
            color: var(--ink);
            font-size: 1.28rem;
            font-weight: 730;
            line-height: 1.2;
            margin: 0;
        }
        .section-copy {
            color: var(--muted);
            font-size: 0.94rem;
            line-height: 1.45;
            margin: 0.35rem 0 0;
            max-width: 62rem;
        }
        .metric-card, .insight-card, .leader-card, .profile-card, .prediction-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface);
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .metric-card {
            min-height: 6.25rem;
            padding: 0.85rem 0.95rem;
            margin-bottom: 0.75rem;
        }
        .metric-label {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 650;
            line-height: 1.2;
            margin-bottom: 0.55rem;
            text-transform: uppercase;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.58rem;
            font-weight: 740;
            line-height: 1.1;
            overflow-wrap: anywhere;
        }
        .metric-detail {
            color: var(--muted);
            font-size: 0.78rem;
            line-height: 1.25;
            margin-top: 0.45rem;
        }
        .leader-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            min-height: 14.1rem;
            padding: 1rem 1.1rem;
            margin-bottom: 0.75rem;
        }
        .leader-label {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 660;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }
        .leader-title {
            color: var(--ink);
            font-size: 2.05rem;
            font-weight: 790;
            line-height: 1.05;
            margin-bottom: 0.7rem;
        }
        .leader-detail {
            color: #334155;
            font-size: 0.96rem;
            line-height: 1.45;
            margin-bottom: 0.8rem;
        }
        .leader-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.5rem;
        }
        .leader-mini {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.55rem;
        }
        .leader-mini-label {
            color: var(--muted);
            font-size: 0.7rem;
            margin-bottom: 0.2rem;
            text-transform: uppercase;
        }
        .leader-mini-value {
            color: var(--ink);
            font-size: 0.94rem;
            font-weight: 720;
            overflow-wrap: anywhere;
        }
        .insight-card {
            min-height: 7.6rem;
            padding: 0.9rem 1rem;
            margin-bottom: 0.75rem;
        }
        .insight-kicker {
            color: var(--teal);
            font-size: 0.75rem;
            font-weight: 760;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }
        .insight-title {
            color: var(--ink);
            font-size: 1rem;
            font-weight: 730;
            line-height: 1.25;
            margin-bottom: 0.35rem;
        }
        .insight-body {
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.42;
        }
        .story-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.75rem 0 1rem;
        }
        .story-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface);
            padding: 0.95rem 1rem;
            min-height: 12.5rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .story-kicker {
            color: var(--teal);
            font-size: 0.72rem;
            font-weight: 760;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }
        .story-title {
            color: var(--ink);
            font-size: 1.08rem;
            font-weight: 760;
            line-height: 1.22;
            margin-bottom: 0.45rem;
        }
        .story-body {
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.42;
        }
        .story-note {
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 0.8rem;
            line-height: 1.35;
            margin-top: 0.75rem;
            padding-top: 0.65rem;
        }
        .pipeline-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.65rem;
            margin: 0.75rem 0 1.1rem;
        }
        .pipeline-step {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #ffffff;
            min-height: 11.8rem;
            padding: 0.85rem;
            position: relative;
        }
        .pipeline-number {
            align-items: center;
            background: #e0f2fe;
            border-radius: 999px;
            color: #075985;
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 780;
            height: 1.65rem;
            justify-content: center;
            margin-bottom: 0.65rem;
            width: 1.65rem;
        }
        .pipeline-title {
            color: var(--ink);
            font-size: 0.95rem;
            font-weight: 760;
            line-height: 1.2;
            margin-bottom: 0.4rem;
        }
        .pipeline-body {
            color: #475569;
            font-size: 0.8rem;
            line-height: 1.35;
        }
        .method-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.75rem 0 1rem;
        }
        .method-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.9rem 1rem;
        }
        .method-title {
            color: var(--ink);
            font-size: 1rem;
            font-weight: 760;
            line-height: 1.2;
            margin-bottom: 0.4rem;
        }
        .method-body {
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.42;
        }
        .priority-badge {
            border-radius: 999px;
            background: var(--subtle);
            border: 1px solid var(--border);
            color: #334155;
            display: inline-flex;
            font-size: 0.7rem;
            font-weight: 760;
            margin-bottom: 0.45rem;
            padding: 0.22rem 0.5rem;
            text-transform: uppercase;
        }
        .status-badge {
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.72rem;
            font-weight: 760;
            padding: 0.25rem 0.52rem;
            text-transform: uppercase;
        }
        .status-target, .status-stretch {
            color: #065f46;
            background: #d1fae5;
        }
        .status-guardrail {
            color: #92400e;
            background: #fef3c7;
        }
        .status-below {
            color: #991b1b;
            background: #fee2e2;
        }
        .bracket-shell {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.85rem;
            overflow-x: auto;
        }
        .bracket-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(128px, 1fr));
            gap: 0.6rem;
            min-width: 760px;
            align-items: start;
        }
        .round-column {
            min-width: 0;
        }
        .round-title {
            color: #334155;
            font-size: 0.82rem;
            font-weight: 760;
            margin-bottom: 0.5rem;
        }
        .match-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #ffffff;
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .match-card.focus {
            border: 2px solid var(--blue);
            background: #eff6ff;
        }
        .match-meta {
            color: var(--muted);
            font-size: 0.69rem;
            margin-bottom: 0.3rem;
        }
        .team-line {
            display: flex;
            justify-content: space-between;
            gap: 0.4rem;
            color: #334155;
            font-size: 0.76rem;
            line-height: 1.28;
            margin: 0.12rem 0;
        }
        .team-line.winner {
            color: var(--ink);
            font-weight: 760;
        }
        .winner-note {
            color: var(--teal);
            font-size: 0.68rem;
            font-weight: 700;
            line-height: 1.25;
            margin-top: 0.34rem;
        }
        .profile-card {
            padding: 0.85rem 0.95rem;
            margin-bottom: 0.75rem;
        }
        .profile-label {
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 680;
            text-transform: uppercase;
        }
        .profile-value {
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 760;
            line-height: 1.12;
            margin-top: 0.35rem;
        }
        .profile-detail {
            color: #475569;
            font-size: 0.82rem;
            margin-top: 0.35rem;
        }
        .prediction-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.7rem;
            margin-bottom: 1rem;
        }
        .prediction-card {
            padding: 0.75rem 0.85rem;
            min-height: 8.5rem;
        }
        .prediction-card.focus {
            border: 2px solid var(--blue);
            background: #eff6ff;
        }
        .prediction-meta {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 650;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
        }
        .prediction-main {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: center;
        }
        .prediction-team {
            color: var(--ink);
            font-size: 0.94rem;
            font-weight: 720;
            line-height: 1.2;
            max-width: 5.8rem;
        }
        .prediction-score {
            color: var(--ink);
            font-size: 1.55rem;
            font-weight: 780;
            line-height: 1;
            white-space: nowrap;
        }
        .prediction-detail {
            color: #475569;
            font-size: 0.8rem;
            line-height: 1.35;
            margin-top: 0.55rem;
        }
        .sidebar-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--subtle);
            padding: 0.75rem;
            margin-top: 0.75rem;
        }
        .sidebar-kicker {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 720;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
        }
        .sidebar-title {
            color: var(--ink);
            font-size: 1.05rem;
            font-weight: 760;
            line-height: 1.15;
            margin-bottom: 0.45rem;
        }
        .sidebar-row {
            color: #475569;
            display: flex;
            font-size: 0.8rem;
            justify-content: space-between;
            padding: 0.12rem 0;
        }
        @media (max-width: 1000px) {
            .title-row {
                display: block;
            }
            .stack-pills {
                justify-content: flex-start;
                margin-top: 0.75rem;
            }
            .leader-strip, .prediction-grid, .story-grid, .pipeline-grid, .method-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    data = {
        "matches": pd.read_csv(DATA_DIR / "dashboard_match_predictions.csv"),
        "standings": pd.read_csv(DATA_DIR / "dashboard_group_standings.csv"),
        "teams": pd.read_csv(DATA_DIR / "dashboard_team_profiles.csv"),
        "context": pd.read_csv(DATA_DIR / "dashboard_match_feature_context.csv"),
        "metrics": pd.read_csv(DATA_DIR / "dashboard_model_metrics.csv"),
        "quality": pd.read_csv(DATA_DIR / "dashboard_data_quality.csv"),
        "history": pd.read_csv(DATA_DIR / "dashboard_historical_competition_summary.csv"),
    }
    data["matches"]["date_utc"] = pd.to_datetime(data["matches"]["date_utc"], utc=True)
    data["context"]["match_date_utc"] = pd.to_datetime(data["context"]["match_date_utc"], utc=True)
    data["teams"] = add_strength_index(data["teams"])
    return data


def safe(value: object) -> str:
    if pd.isna(value):
        return ""
    return html.escape(str(value))


def pct(value: float) -> str:
    return f"{value:.1%}"


def signed(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}"


def title_label(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).replace("_", " ").title()


def normalize_series(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    minimum = clean.min()
    maximum = clean.max()
    if pd.isna(minimum) or pd.isna(maximum) or minimum == maximum:
        return pd.Series(50.0, index=series.index)
    return ((clean - minimum) / (maximum - minimum) * 100).fillna(50.0)


def add_strength_index(teams: pd.DataFrame) -> pd.DataFrame:
    enriched = teams.copy()
    text_defaults = {
        "confederation": "Unknown",
        "group_letter": "",
        "squad_status": "unknown",
    }
    numeric_defaults = {
        "fifa_points": 1500.0,
        "fifa_rank": 999.0,
        "current_elo": 1500.0,
        "last_10_adjusted_points_per_match": 0.0,
        "last_10_adjusted_goal_diff_per_match": 0.0,
        "overall_star_power_z": 0.0,
        "attacking_star_power_z": 0.0,
        "avg_corners_for": 0.0,
        "blended_yellow_cards_for": 0.0,
        "profile_completeness_score": 0.0,
    }
    for column, default in text_defaults.items():
        if column not in enriched.columns:
            enriched[column] = default
        enriched[column] = enriched[column].fillna(default).astype(str)
    for column, default in numeric_defaults.items():
        if column not in enriched.columns:
            enriched[column] = default
        enriched[column] = pd.to_numeric(enriched[column], errors="coerce").fillna(default)
    enriched["current_elo"] = enriched["current_elo"].clip(lower=1.0)
    fifa_points_score = normalize_series(enriched["fifa_points"])
    rank_score = 100 - normalize_series(enriched["fifa_rank"])
    elo_score = normalize_series(enriched["current_elo"])
    star_score = normalize_series(enriched["overall_star_power_z"])
    adjusted_form_score = normalize_series(enriched["last_10_adjusted_points_per_match"])
    enriched["dashboard_strength_index"] = (
        0.30 * fifa_points_score
        + 0.24 * rank_score
        + 0.22 * elo_score
        + 0.14 * star_score
        + 0.10 * adjusted_form_score
    ).round(1)
    return enriched


def available_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def metric_value(metrics: pd.DataFrame, metric_name: str) -> float:
    row = metrics.loc[metrics["metric_name"] == metric_name]
    if row.empty:
        return float("nan")
    return float(row.iloc[0]["current_value"])


def metric_row(metrics: pd.DataFrame, metric_name: str) -> pd.Series:
    row = metrics.loc[metrics["metric_name"] == metric_name]
    if row.empty:
        raise ValueError(f"Missing metric: {metric_name}")
    return row.iloc[0]


def metric_display(row: pd.Series) -> str:
    value = float(row["current_value"])
    if row["direction"] == "higher":
        return pct(value)
    return f"{value:.3f}"


def status_class(status: str) -> str:
    normalized = status.lower().replace("_", "-").replace(" ", "-")
    if normalized.startswith("below"):
        return "status-below"
    return f"status-{normalized}"


def metric_card(label: str, value: object, detail: str | None = None) -> None:
    detail_html = f'<div class="metric-detail">{safe(detail)}</div>' if detail else ""
    st.markdown(
        "\n".join(
            [
                '<div class="metric-card">',
                f'<div class="metric-label">{safe(label)}</div>',
                f'<div class="metric-value">{safe(value)}</div>',
                detail_html,
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def insight_card(kicker: str, title: str, body: str) -> None:
    st.markdown(
        "\n".join(
            [
                '<div class="insight-card">',
                f'<div class="insight-kicker">{safe(kicker)}</div>',
                f'<div class="insight-title">{safe(title)}</div>',
                f'<div class="insight-body">{safe(body)}</div>',
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def story_card(kicker: str, title: str, body: str, note: str | None = None) -> str:
    note_html = f'<div class="story-note">{safe(note)}</div>' if note else ""
    return "\n".join(
        [
            '<div class="story-card">',
            f'<div class="story-kicker">{safe(kicker)}</div>',
            f'<div class="story-title">{safe(title)}</div>',
            f'<div class="story-body">{safe(body)}</div>',
            note_html,
            "</div>",
        ]
    )


def method_card(title: str, body: str, badge: str | None = None) -> str:
    badge_html = f'<div class="priority-badge">{safe(badge)}</div>' if badge else ""
    return "\n".join(
        [
            '<div class="method-card">',
            badge_html,
            f'<div class="method-title">{safe(title)}</div>',
            f'<div class="method-body">{safe(body)}</div>',
            "</div>",
        ]
    )


def section_header(title: str, copy: str | None = None) -> None:
    copy_html = f'<p class="section-copy">{safe(copy)}</p>' if copy else ""
    st.markdown(
        "\n".join(
            [
                '<div class="section-head">',
                f'<h2 class="section-title">{safe(title)}</h2>',
                copy_html,
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def profile_card(label: str, value: object, detail: str | None = None) -> None:
    detail_html = f'<div class="profile-detail">{safe(detail)}</div>' if detail else ""
    st.markdown(
        "\n".join(
            [
                '<div class="profile-card">',
                f'<div class="profile-label">{safe(label)}</div>',
                f'<div class="profile-value">{safe(value)}</div>',
                detail_html,
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def display_table(
    frame: pd.DataFrame,
    columns: list[str],
    labels: dict[str, str],
    height: int | None = None,
    column_help: dict[str, str] | None = None,
) -> None:
    display_columns = available_columns(frame, columns)
    if not display_columns:
        st.info("No display columns are available for this table.")
        return
    table = frame.loc[:, display_columns].rename(columns=labels).copy()
    for column in table.select_dtypes(include=["datetime64[ns, UTC]", "datetime64[ns]"]).columns:
        table[column] = table[column].dt.strftime("%b %d, %Y")
    for column in table.select_dtypes(include=["float"]).columns:
        table[column] = table[column].round(3)
    table = table.where(pd.notna(table), "")
    dataframe_args = {
        "use_container_width": True,
        "hide_index": True,
    }
    if height is not None:
        dataframe_args["height"] = height
    if column_help:
        dataframe_args["column_config"] = {
            labels.get(column, column): st.column_config.Column(help=help_text)
            for column, help_text in column_help.items()
            if column in display_columns
        }
    st.dataframe(table, **dataframe_args)


def polish_figure(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=24, b=10),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color=PALETTE["ink"], size=12),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#e5e7eb", zeroline=False)
    return fig


def team_group(teams: pd.DataFrame, team: str) -> str | None:
    if team == "All teams":
        return None
    row = teams.loc[teams["team_name"] == team]
    if row.empty:
        return None
    return str(row.iloc[0]["group_letter"])


def effective_group(selected_group: str, selected_team: str, teams: pd.DataFrame) -> str:
    if selected_group != "All groups":
        return selected_group
    team_group_letter = team_group(teams, selected_team)
    if team_group_letter:
        return team_group_letter
    return "A"


def team_matches(matches: pd.DataFrame, team: str) -> pd.DataFrame:
    if team == "All teams":
        return matches.copy()
    return matches[
        (matches["predicted_home_team"] == team)
        | (matches["predicted_away_team"] == team)
        | (matches["home_team"] == team)
        | (matches["away_team"] == team)
    ].copy()


def match_team_names(row: pd.Series) -> tuple[str, str]:
    return str(row["predicted_home_team"]), str(row["predicted_away_team"])


def final_match(matches: pd.DataFrame) -> pd.Series:
    return matches.loc[matches["match_id"] == 104].iloc[0]


def third_place_match(matches: pd.DataFrame) -> pd.Series:
    return matches.loc[matches["match_id"] == 103].iloc[0]


def runner_up_from_final(final_row: pd.Series) -> str:
    home_team, away_team = match_team_names(final_row)
    return away_team if final_row["predicted_winner_team"] == home_team else home_team


def final_description(final_row: pd.Series) -> str:
    home_team, away_team = match_team_names(final_row)
    winner = str(final_row["predicted_winner_team"])
    loser = away_team if winner == home_team else home_team
    penalties = " after penalties" if bool(final_row["penalties"]) else ""
    return f"{winner} over {loser}, {final_row['scoreline']}{penalties}"


def team_journey(matches: pd.DataFrame, team: str) -> pd.DataFrame:
    rows = []
    for row in team_matches(matches, team).sort_values("match_id").itertuples(index=False):
        row_dict = row._asdict()
        home_team = row_dict["predicted_home_team"]
        away_team = row_dict["predicted_away_team"]
        is_home = home_team == team
        opponent = away_team if is_home else home_team
        goals_for = row_dict["predicted_home_goals"] if is_home else row_dict["predicted_away_goals"]
        goals_against = row_dict["predicted_away_goals"] if is_home else row_dict["predicted_home_goals"]

        if row_dict["competition_phase"] == "group":
            if goals_for > goals_against:
                result = "Win"
            elif goals_for < goals_against:
                result = "Loss"
            else:
                result = "Draw"
        else:
            result = "Win" if row_dict["predicted_winner_team"] == team else "Loss"
            if row_dict["penalties"]:
                result = f"{result} on penalties"

        rows.append(
            {
                "Match": int(row_dict["match_id"]),
                "Stage": row_dict["round"],
                "Opponent": opponent,
                "Score": f"{int(goals_for)}-{int(goals_against)}",
                "Result": result,
            }
        )
    return pd.DataFrame(rows)


def group_qualifiers(standings: pd.DataFrame) -> pd.DataFrame:
    qualifiers = standings.loc[standings["group_rank"] <= 2].copy()
    pivot = qualifiers.pivot(index="group_letter", columns="group_rank", values="team_name")
    pivot = pivot.rename(columns={1: "Winner", 2: "Runner-up"}).reset_index()
    return pivot.rename(columns={"group_letter": "Group"})


def outcome_distribution(matches: pd.DataFrame) -> pd.DataFrame:
    result = (
        matches.groupby(["competition_phase", "winner_label"], dropna=False)
        .size()
        .reset_index(name="matches")
    )
    result["winner_label"] = result["winner_label"].str.title()
    result["phase_label"] = result["competition_phase"].map(PHASE_LABELS)
    return result


def filtered_match_explorer(
    matches: pd.DataFrame,
    selected_phase: str,
    selected_group: str,
    selected_team: str,
) -> pd.DataFrame:
    filtered = matches.copy()
    if selected_phase != "All matches":
        phase_key = "group" if selected_phase == "Group stage" else "knockout"
        filtered = filtered[filtered["competition_phase"] == phase_key]
    if selected_group != "All groups" and selected_phase != "Knockout stage":
        filtered = filtered[filtered["group"] == selected_group]
    if selected_team != "All teams":
        filtered = team_matches(filtered, selected_team)
    return filtered.sort_values("match_id")


def percentile_score(series: pd.Series, value: float, higher_better: bool = True) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or pd.isna(value):
        return 50.0
    if higher_better:
        return float((clean <= value).mean() * 100)
    return float((clean >= value).mean() * 100)


def team_signal_scores(teams: pd.DataFrame, team: str) -> pd.DataFrame:
    row = teams.loc[teams["team_name"] == team].iloc[0]
    signals = [
        ("FIFA points", "fifa_points", True),
        ("Elo rating", "current_elo", True),
        ("Adjusted form", "last_10_adjusted_points_per_match", True),
        ("Adjusted goal difference", "last_10_adjusted_goal_diff_per_match", True),
        ("Squad star power", "overall_star_power_z", True),
        ("Attack profile", "attacking_star_power_z", True),
    ]
    return pd.DataFrame(
        {
            "Signal": label,
            "Percentile": percentile_score(teams[column], row[column], higher_better),
        }
        for label, column, higher_better in signals
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="app-header">
            <div class="title-row">
                <div>
                    <div class="eyebrow">Analytics Engineering Portfolio Case Study</div>
                    <h1 class="app-title">FIFA World Cup 2026 Prediction Analytics</h1>
                    <p class="app-subtitle">
                        A senior-level forecasting data product built from dbt feature marts, FIFA rankings,
                        international results, squad profiles, event signals, and calibrated Python simulation logic.
                    </p>
                </div>
                <div class="stack-pills">
                    <span class="pill">dbt</span>
                    <span class="pill">DuckDB</span>
                    <span class="pill">Python</span>
                    <span class="pill">Streamlit</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(
    teams: pd.DataFrame,
    standings: pd.DataFrame,
) -> tuple[str, str]:
    groups = ["All groups", *sorted(standings["group_letter"].dropna().unique())]
    team_names = ["All teams", *sorted(teams["team_name"].dropna().unique())]

    with st.sidebar:
        st.header("Focus")
        selected_team = st.selectbox(
            "Team",
            team_names,
            help="Highlights the team across bracket, group, team, and match views.",
        )
        selected_group = st.selectbox(
            "Group",
            groups,
            help="Narrows group-stage standings and match context.",
        )

        if selected_team == "All teams":
            top_team = teams.sort_values("dashboard_strength_index", ascending=False).iloc[0]
            sidebar_card(
                "Field leader",
                top_team["team_name"],
                [
                    ("Strength index", f"{top_team['dashboard_strength_index']:.1f}"),
                    ("FIFA rank", int(top_team["fifa_rank"])),
                    ("Group", top_team["group_letter"]),
                ],
            )
        else:
            row = teams.loc[teams["team_name"] == selected_team].iloc[0]
            sidebar_card(
                "Focused team",
                selected_team,
                [
                    ("Group", row["group_letter"]),
                    ("FIFA rank", int(row["fifa_rank"])),
                    ("Strength index", f"{row['dashboard_strength_index']:.1f}"),
                ],
            )

    return selected_team, selected_group


def sidebar_card(kicker: str, title: str, rows: list[tuple[str, object]]) -> None:
    row_html = "\n".join(
        f'<div class="sidebar-row"><span>{safe(label)}</span><strong>{safe(value)}</strong></div>'
        for label, value in rows
    )
    st.markdown(
        "\n".join(
            [
                '<div class="sidebar-card">',
                f'<div class="sidebar-kicker">{safe(kicker)}</div>',
                f'<div class="sidebar-title">{safe(title)}</div>',
                row_html,
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_leader_card(matches: pd.DataFrame) -> None:
    final_row = final_match(matches)
    third_row = third_place_match(matches)
    champion = final_row["predicted_winner_team"]
    runner_up = runner_up_from_final(final_row)
    third_place = third_row["predicted_winner_team"]
    st.markdown(
        "\n".join(
            [
                '<div class="leader-card">',
                '<div class="leader-label">Tournament forecast</div>',
                f'<div class="leader-title">{safe(champion)} win the World Cup</div>',
                f'<div class="leader-detail">{safe(final_description(final_row))}. '
                f'{safe(third_place)} are projected to finish third.</div>',
                '<div class="leader-strip">',
                f'<div class="leader-mini"><div class="leader-mini-label">Champion</div>'
                f'<div class="leader-mini-value">{safe(champion)}</div></div>',
                f'<div class="leader-mini"><div class="leader-mini-label">Runner-up</div>'
                f'<div class="leader-mini-value">{safe(runner_up)}</div></div>',
                f'<div class="leader-mini"><div class="leader-mini-label">Third place</div>'
                f'<div class="leader-mini-value">{safe(third_place)}</div></div>',
                "</div>",
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_project_story(
    matches: pd.DataFrame,
    metrics: pd.DataFrame,
    quality: pd.DataFrame,
    history: pd.DataFrame,
) -> None:
    section_header(
        "Project Story",
        "This dashboard is designed as an analytics engineering case study: a tested dbt warehouse feeds a calibrated Python forecast, then publishes a stakeholder-ready BI layer.",
    )
    st.markdown(
        '<div class="story-grid">'
        + "".join(story_card(kicker, title, body, note) for kicker, title, body, note in PROJECT_PILLARS)
        + "</div>",
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    with metric_cols[0]:
        metric_card(
            "Blended outcome",
            pct(metric_value(metrics, "blended_scoreline_outcome_accuracy")),
            "Final scoreline result accuracy",
        )
    with metric_cols[1]:
        metric_card(
            "Exact score",
            pct(metric_value(metrics, "reconciled_scoreline_exact_accuracy")),
            "Stretch target cleared",
        )
    with metric_cols[2]:
        metric_card(
            "Average goals MAE",
            f"{metric_value(metrics, 'average_goals_mae'):.3f}",
            "Lower is better",
        )
    with metric_cols[3]:
        valid_check = quality.loc[
            (quality["check_group"] == "submission_validation")
            & (quality["check_name"] == "valid"),
            "check_value",
        ]
        metric_card(
            "Submission checks",
            "Passed" if valid_check.tolist() == [1] else "Review",
            "104 predicted matches",
        )

    section_header(
        "Analytics Engineering Pipeline",
        "The main design choice is separation of concerns: dbt prepares trusted data products, Python handles model state, and Streamlit consumes a stable BI snapshot.",
    )
    step_html = []
    for number, title, body in PIPELINE_STEPS:
        step_html.append(
            "\n".join(
                [
                    '<div class="pipeline-step">',
                    f'<div class="pipeline-number">{safe(number)}</div>',
                    f'<div class="pipeline-title">{safe(title)}</div>',
                    f'<div class="pipeline-body">{safe(body)}</div>',
                    "</div>",
                ]
            )
        )
    st.markdown(f'<div class="pipeline-grid">{"".join(step_html)}</div>', unsafe_allow_html=True)

    section_header(
        "Model Design",
        "The final submission is not one model pretending to solve every task. It is a reconciled system that keeps score, outcome, bracket, corners, and cards consistent.",
    )
    st.markdown(
        '<div class="method-grid">'
        + "".join(method_card(title, body) for title, body in MODEL_LAYERS)
        + "</div>",
        unsafe_allow_html=True,
    )

    section_header(
        "Why These Targets Matter",
        "The targets are practical contracts for a low-scoring sport. They reward the exact-score competition objective without ignoring whether the forecast tells a believable tournament story.",
    )
    st.markdown(
        '<div class="method-grid">'
        + "".join(
            method_card(title, body, priority) for title, priority, body in TARGET_RATIONALE
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    chart_cols = st.columns([0.95, 1.05])
    with chart_cols[0]:
        scorelines = (
            matches["scoreline"]
            .value_counts()
            .head(8)
            .rename_axis("scoreline")
            .reset_index(name="matches")
        )
        fig = px.bar(
            scorelines,
            x="matches",
            y="scoreline",
            orientation="h",
            labels={"matches": "Predicted matches", "scoreline": "Scoreline"},
            color="matches",
            color_continuous_scale=["#dbeafe", "#2563eb"],
        )
        fig = polish_figure(fig, 330)
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="story_scoreline_distribution",
        )

    with chart_cols[1]:
        recent_history = history[history["match_year"] >= 1992].copy()
        history_summary = (
            recent_history.groupby("match_year", as_index=False)
            .agg(matches=("matches", "sum"), avg_total_goals=("avg_total_goals", "mean"))
            .tail(35)
        )
        fig = px.line(
            history_summary,
            x="match_year",
            y="avg_total_goals",
            markers=True,
            labels={"match_year": "Year", "avg_total_goals": "Average total goals"},
        )
        fig.update_traces(line_color=PALETTE["orange"])
        fig = polish_figure(fig, 330)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="story_goal_environment",
        )


def render_executive_view(
    matches: pd.DataFrame,
    metrics: pd.DataFrame,
    teams: pd.DataFrame,
    selected_team: str,
) -> None:
    section_header(
        "Executive Summary",
        "The forecast balances conservative scorelines with team strength signals, then resolves the knockout bracket from the simulated group stage.",
    )
    left, right = st.columns([1.12, 0.88])
    with left:
        render_leader_card(matches)
    with right:
        metric_cols = st.columns(2)
        with metric_cols[0]:
            metric_card("Tournament goals", int(matches["total_goals"].sum()), "Across 104 matches")
        with metric_cols[1]:
            metric_card("Penalty matches", int(matches["penalties"].sum()), "Knockout decisions")
        with metric_cols[0]:
            metric_card(
                "Outcome accuracy",
                pct(metric_value(metrics, "blended_scoreline_outcome_accuracy")),
                "Blended scoreline result",
            )
        with metric_cols[1]:
            metric_card(
                "Exact score accuracy",
                pct(metric_value(metrics, "reconciled_scoreline_exact_accuracy")),
                "Historical validation",
            )

    insight_cols = st.columns(4)
    with insight_cols[0]:
        insight_card(
            "Champion path",
            "Spain survive two penalty decisions",
            "The model projects close knockout margins, with Spain advancing through Brazil and Argentina after 1-1 draws.",
        )
    with insight_cols[1]:
        insight_card(
            "Scoring profile",
            "1-0 and 1-1 are common outputs",
            "The calibration intentionally favors realistic tournament scorelines over high-variance goal totals.",
        )
    with insight_cols[2]:
        insight_card(
            "Model health",
            "Direct outcome sits near target",
            f"Direct outcome validation is {pct(metric_value(metrics, 'direct_outcome_accuracy'))}, essentially at the 62% target.",
        )
    with insight_cols[3]:
        insight_card(
            "Data layer",
            "Feature marts are dashboard-ready",
            "dbt produces tested team, match, standings, quality, and model metric outputs for this app.",
        )

    if selected_team != "All teams":
        section_header(f"{selected_team} Tournament Path")
        journey = team_journey(matches, selected_team)
        if journey.empty:
            st.info("This team does not appear in the predicted tournament path.")
        else:
            display_table(journey, ["Match", "Stage", "Opponent", "Score", "Result"], {})

    chart_cols = st.columns([1.05, 0.95])
    with chart_cols[0]:
        contenders = teams.nlargest(12, "dashboard_strength_index").sort_values(
            "dashboard_strength_index"
        )
        fig = px.bar(
            contenders,
            x="dashboard_strength_index",
            y="team_name",
            orientation="h",
            labels={"dashboard_strength_index": "Strength index", "team_name": ""},
            color="confederation",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hover_data=available_columns(
                contenders,
                [
                    "fifa_rank",
                    "current_elo",
                    "last_10_adjusted_points_per_match",
                    "overall_star_power_z",
                ],
            ),
        )
        fig = polish_figure(fig, 360)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="executive_strength_index",
        )

    with chart_cols[1]:
        scorelines = (
            matches["scoreline"]
            .value_counts()
            .head(8)
            .rename_axis("scoreline")
            .reset_index(name="matches")
        )
        fig = px.bar(
            scorelines,
            x="matches",
            y="scoreline",
            orientation="h",
            labels={"matches": "Matches", "scoreline": "Scoreline"},
            color="matches",
            color_continuous_scale=["#dbeafe", "#2563eb"],
        )
        fig = polish_figure(fig, 360)
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="executive_scoreline_distribution",
        )


def team_line(team: str, goals: int, winner: str) -> str:
    winner_class = " winner" if team == winner else ""
    return "\n".join(
        [
            f'<div class="team-line{winner_class}">',
            f"<span>{safe(team)}</span>",
            f"<span>{int(goals)}</span>",
            "</div>",
        ]
    )


def bracket_card(row: pd.Series, selected_team: str) -> str:
    home_team, away_team = match_team_names(row)
    winner = str(row["predicted_winner_team"])
    focus = selected_team != "All teams" and selected_team in {home_team, away_team}
    penalties = " on penalties" if bool(row["penalties"]) else ""
    return "\n".join(
        [
            f'<div class="match-card{" focus" if focus else ""}">',
            f'<div class="match-meta">Match {int(row["match_id"])}</div>',
            team_line(home_team, row["predicted_home_goals"], winner),
            team_line(away_team, row["predicted_away_goals"], winner),
            f'<div class="winner-note">{safe(winner)} wins{safe(penalties)}</div>',
            "</div>",
        ]
    )


def render_bracket(matches: pd.DataFrame, selected_team: str) -> None:
    section_header(
        "Predicted Knockout Bracket",
        "All 32 knockout predictions are shown by round. Close matches that go to penalties remain tied on the scoreline.",
    )
    knockout = matches[matches["competition_phase"] == "knockout"].copy()
    columns = []
    for round_name in ROUND_ORDER:
        round_matches = knockout[knockout["round"] == round_name].sort_values("match_id")
        cards = "\n".join(bracket_card(row, selected_team) for _, row in round_matches.iterrows())
        columns.append(
            "\n".join(
                [
                    '<div class="round-column">',
                    f'<div class="round-title">{safe(round_name)}</div>',
                    cards,
                    "</div>",
                ]
            )
        )
    st.markdown(
        "\n".join(
            [
                '<div class="bracket-shell">',
                f'<div class="bracket-grid">{"".join(columns)}</div>',
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )

    section_header("Final Four Detail")
    final_four = knockout[knockout["match_id"].isin([101, 102, 103, 104])]
    display_table(
        final_four,
        [
            "match_id",
            "round",
            "predicted_home_team",
            "predicted_away_team",
            "scoreline",
            "predicted_winner_team",
            "penalties",
        ],
        {
            "match_id": "Match",
            "round": "Round",
            "predicted_home_team": "Home",
            "predicted_away_team": "Away",
            "scoreline": "Score",
            "predicted_winner_team": "Winner",
            "penalties": "Penalties",
        },
    )


def render_groups(
    matches: pd.DataFrame,
    standings: pd.DataFrame,
    teams: pd.DataFrame,
    selected_group: str,
    selected_team: str,
) -> None:
    group = effective_group(selected_group, selected_team, teams)
    section_header(
        "Group Stage",
        "The group view starts with projected qualifiers across the field, then drills into the focused group.",
    )

    summary_cols = st.columns([0.9, 1.1])
    with summary_cols[0]:
        display_table(group_qualifiers(standings), ["Group", "Winner", "Runner-up"], {}, 460)
    with summary_cols[1]:
        group_points = standings.sort_values(["group_letter", "group_rank"])
        fig = px.bar(
            group_points,
            x="group_letter",
            y="points",
            color="group_rank",
            labels={"group_letter": "Group", "points": "Points", "group_rank": "Rank"},
            color_continuous_scale=["#0f766e", "#dbeafe", "#f97316"],
            hover_data=["team_name", "goal_difference"],
        )
        fig = polish_figure(fig, 460)
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="group_points_summary",
        )

    section_header(f"Group {group} Detail")
    group_standings = standings[standings["group_letter"] == group].copy()
    group_matches = matches[matches["group"] == group].copy()

    display_table(
        group_standings,
        [
            "group_rank",
            "team_name",
            "points",
            "wins",
            "draws",
            "losses",
            "goals_for",
            "goals_against",
            "goal_difference",
        ],
        {
            "group_rank": "Rank",
            "team_name": "Team",
            "points": "Pts",
            "wins": "W",
            "draws": "D",
            "losses": "L",
            "goals_for": "GF",
            "goals_against": "GA",
            "goal_difference": "GD",
        },
    )

    fig = px.bar(
        group_standings.sort_values("group_rank"),
        x="team_name",
        y="points",
        color="goal_difference",
        labels={"team_name": "Team", "points": "Points", "goal_difference": "GD"},
        color_continuous_scale=["#f97316", "#f8fafc", "#14b8a6"],
    )
    fig = polish_figure(fig, 280)
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=PLOT_CONFIG,
        key="group_detail_points",
    )

    section_header("Focused Group Matches")
    display_table(
        group_matches,
        [
            "match_id",
            "date_utc",
            "venue",
            "predicted_home_team",
            "predicted_away_team",
            "scoreline",
            "predicted_winner_team",
            "corners",
            "yellow_cards",
        ],
        {
            "match_id": "Match",
            "date_utc": "Date",
            "venue": "Venue",
            "predicted_home_team": "Home",
            "predicted_away_team": "Away",
            "scoreline": "Score",
            "predicted_winner_team": "Winner",
            "corners": "Corners",
            "yellow_cards": "Yellows",
        },
    )


def render_team_lens(
    teams: pd.DataFrame,
    matches: pd.DataFrame,
    selected_team: str,
) -> None:
    if selected_team == "All teams":
        section_header(
            "Team Lens",
            "The field view compares ranking, Elo, opponent-adjusted form, squad signal, and the dashboard composite strength index.",
        )
        chart_cols = st.columns([1.05, 0.95])
        with chart_cols[0]:
            fig = px.scatter(
                teams,
                x="fifa_points",
                y="overall_star_power_z",
                color="confederation",
                size="current_elo",
                hover_name="team_name",
                labels={
                    "fifa_points": "FIFA points",
                    "overall_star_power_z": "Squad star power",
                    "confederation": "Confederation",
                    "current_elo": "Elo",
                },
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig = polish_figure(fig, 430)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config=PLOT_CONFIG,
                key="team_lens_field_scatter",
            )

        with chart_cols[1]:
            display_table(
                teams.nlargest(14, "dashboard_strength_index"),
                [
                    "team_name",
                    "group_letter",
                    "fifa_rank",
                    "current_elo",
                    "dashboard_strength_index",
                    "last_10_adjusted_points_per_match",
                    "overall_star_power_z",
                ],
                {
                    "team_name": "Team",
                    "group_letter": "Group",
                    "fifa_rank": "Rank",
                    "current_elo": "Elo",
                    "dashboard_strength_index": "Strength",
                    "last_10_adjusted_points_per_match": "Adj Form",
                    "overall_star_power_z": "Star",
                },
                430,
            )
    else:
        profile = teams.loc[teams["team_name"] == selected_team].iloc[0]
        section_header(
            f"{selected_team} Team Lens",
            "Percentile scores compare the selected team with the rest of the tournament field.",
        )
        cards = st.columns(5)
        with cards[0]:
            profile_card("Group", profile["group_letter"], "Opening path")
        with cards[1]:
            profile_card("FIFA rank", int(profile["fifa_rank"]), f"{profile['fifa_points']:.0f} points")
        with cards[2]:
            profile_card(
                "Adjusted form",
                signed(profile["last_10_adjusted_points_per_match"]),
                "Points above Elo expectation",
            )
        with cards[3]:
            profile_card("Strength", f"{profile['dashboard_strength_index']:.1f}", "Composite index")
        with cards[4]:
            profile_card(
                "Data coverage",
                f"{profile['profile_completeness_score']:.0%}",
                title_label(profile["squad_status"]),
            )

        lens_cols = st.columns([0.95, 1.05])
        with lens_cols[0]:
            signals = team_signal_scores(teams, selected_team)
            fig = px.bar(
                signals.sort_values("Percentile"),
                x="Percentile",
                y="Signal",
                orientation="h",
                range_x=[0, 100],
                color="Percentile",
                color_continuous_scale=["#fee2e2", "#fef3c7", "#14b8a6"],
                labels={"Percentile": "Field percentile", "Signal": ""},
            )
            fig = polish_figure(fig, 350)
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config=PLOT_CONFIG,
                key=f"team_lens_signals_{selected_team}",
            )

        with lens_cols[1]:
            journey = team_journey(matches, selected_team)
            if journey.empty:
                st.info("This team does not appear in the predicted tournament path.")
            else:
                display_table(journey, ["Match", "Stage", "Opponent", "Score", "Result"], {}, 350)

    section_header("Team Profile Table")
    team_profile_table = teams.sort_values("dashboard_strength_index", ascending=False).copy()
    team_profile_table["profile_coverage_pct"] = (
        team_profile_table["profile_completeness_score"] * 100
    ).round(0).astype(int).astype(str) + "%"
    full_coverage_count = int((team_profile_table["profile_completeness_score"] == 1).sum())
    partial_coverage_count = int((team_profile_table["profile_completeness_score"] < 1).sum())
    display_table(
        team_profile_table,
        [
            "team_name",
            "group_letter",
            "fifa_rank",
            "current_elo",
            "fifa_points",
            "last_10_adjusted_points_per_match",
            "last_10_adjusted_goal_diff_per_match",
            "overall_star_power_z",
            "attacking_star_power_z",
            "avg_corners_for",
            "blended_yellow_cards_for",
            "dashboard_strength_index",
            "profile_coverage_pct",
        ],
        {
            "team_name": "Team",
            "group_letter": "Group",
            "fifa_rank": "Rank",
            "current_elo": "Elo",
            "fifa_points": "FIFA Points",
            "last_10_adjusted_points_per_match": "Adj Form",
            "last_10_adjusted_goal_diff_per_match": "Adj GD",
            "overall_star_power_z": "Star",
            "attacking_star_power_z": "Attack",
            "avg_corners_for": "Corners For",
            "blended_yellow_cards_for": "Yellows",
            "dashboard_strength_index": "Strength",
            "profile_coverage_pct": "Coverage",
        },
        460,
        {
            "current_elo": "Current team Elo after historical international results. Elo adjusts for opponent strength and match result surprise.",
            "fifa_points": "Latest FIFA ranking points. Higher values indicate stronger recent official FIFA performance.",
            "last_10_adjusted_points_per_match": "Average points above or below Elo expectation across the team's ten most recent international matches.",
            "last_10_adjusted_goal_diff_per_match": "Average goal difference above or below an Elo-implied expectation across the team's ten most recent international matches.",
            "overall_star_power_z": "Squad star-power z-score across the tournament field. Positive values are above field average.",
            "attacking_star_power_z": "Attacking squad-strength z-score, weighted toward goals and top attacking contributors.",
            "dashboard_strength_index": "Dashboard composite index combining FIFA points, FIFA rank, recent form, and squad star power.",
            "profile_coverage_pct": "Share of the five expected team-profile inputs present: form, FIFA ranking, squad, event profile, and external player profile.",
        },
    )
    st.caption(
        f"Coverage is a data-completeness check, not a performance score: "
        f"{full_coverage_count} teams have all five profile inputs and "
        f"{partial_coverage_count} teams are missing one input."
    )


def prediction_card(row: pd.Series, selected_team: str) -> str:
    home_team, away_team = match_team_names(row)
    focus = selected_team != "All teams" and selected_team in {home_team, away_team}
    penalties = " Penalties projected." if bool(row["penalties"]) else ""
    group = "" if pd.isna(row["group"]) else f"Group {row['group']} | "
    return "\n".join(
        [
            f'<div class="prediction-card{" focus" if focus else ""}">',
            f'<div class="prediction-meta">Match {int(row["match_id"])} | {group}{safe(row["round"])}</div>',
            '<div class="prediction-main">',
            f'<div class="prediction-team">{safe(home_team)}</div>',
            f'<div class="prediction-score">{int(row["predicted_home_goals"])}-{int(row["predicted_away_goals"])}</div>',
            f'<div class="prediction-team">{safe(away_team)}</div>',
            "</div>",
            f'<div class="prediction-detail">Winner: {safe(row["predicted_winner_team"])}. '
            f'Corners: {int(row["corners"])}. Cards: {int(row["total_cards"])}.{safe(penalties)}</div>',
            "</div>",
        ]
    )


def render_match_cards(matches: pd.DataFrame, selected_team: str) -> None:
    preview = matches.head(12)
    cards = "\n".join(prediction_card(row, selected_team) for _, row in preview.iterrows())
    st.markdown(f'<div class="prediction-grid">{cards}</div>', unsafe_allow_html=True)


def render_matches(
    matches: pd.DataFrame,
    context: pd.DataFrame,
    selected_group: str,
    selected_team: str,
) -> None:
    section_header(
        "Match Detail",
        "Prediction cards keep the current filter readable; the table below preserves the full submission-level detail.",
    )
    selected_phase = st.radio(
        "Phase",
        ["All matches", "Group stage", "Knockout stage"],
        horizontal=True,
    )
    filtered = filtered_match_explorer(matches, selected_phase, selected_group, selected_team)
    if filtered.empty:
        st.info("No matches match the current focus.")
    else:
        render_match_cards(filtered, selected_team)
        display_table(
            filtered,
            [
                "match_id",
                "competition_phase",
                "group",
                "round",
                "venue",
                "predicted_home_team",
                "predicted_away_team",
                "scoreline",
                "predicted_winner_team",
                "corners",
                "yellow_cards",
                "red_cards",
                "penalties",
            ],
            {
                "match_id": "Match",
                "competition_phase": "Phase",
                "group": "Group",
                "round": "Round",
                "venue": "Venue",
                "predicted_home_team": "Home",
                "predicted_away_team": "Away",
                "scoreline": "Score",
                "predicted_winner_team": "Winner",
                "corners": "Corners",
                "yellow_cards": "Yellows",
                "red_cards": "Reds",
                "penalties": "Pens",
            },
            420,
        )

    group_context = context.copy()
    if selected_group != "All groups":
        group_context = group_context[group_context["group_letter"] == selected_group]
    if selected_team != "All teams":
        group_context = group_context[
            (group_context["home_team"] == selected_team)
            | (group_context["away_team"] == selected_team)
        ]

    section_header(
        "Group-Stage Feature Context",
        "Positive difference values favor the listed home team. Knockout matchups are generated after group simulation.",
    )
    if group_context.empty:
        st.info("No group-stage feature context matches the current focus.")
    else:
        display_table(
            group_context.sort_values("match_id"),
            [
                "match_id",
                "group_letter",
                "home_team",
                "away_team",
                "last_10_points_per_match_diff",
                "fifa_rank_diff",
                "fifa_points_diff",
                "overall_star_power_diff",
                "expected_total_corners",
                "expected_total_yellow_cards",
                "expected_total_red_cards",
            ],
            {
                "match_id": "Match",
                "group_letter": "Group",
                "home_team": "Home",
                "away_team": "Away",
                "last_10_points_per_match_diff": "Form Diff",
                "fifa_rank_diff": "Rank Diff",
                "fifa_points_diff": "FIFA Points Diff",
                "overall_star_power_diff": "Star Diff",
                "expected_total_corners": "Corners",
                "expected_total_yellow_cards": "Yellows",
                "expected_total_red_cards": "Reds",
            },
            360,
        )


def render_metric_cards(metrics: pd.DataFrame) -> None:
    metric_labels = {
        "rounded_scoreline_outcome_accuracy": "Rounded outcome",
        "direct_outcome_accuracy": "Direct outcome",
        "blended_scoreline_outcome_accuracy": "Blended outcome",
        "reconciled_scoreline_exact_accuracy": "Exact score",
        "average_goals_mae": "Goals MAE",
    }
    cols = st.columns(5)
    for index, (metric_name, label) in enumerate(metric_labels.items()):
        row = metric_row(metrics, metric_name)
        status = str(row["status"])
        with cols[index]:
            st.markdown(
                "\n".join(
                    [
                        '<div class="metric-card">',
                        f'<div class="metric-label">{safe(label)}</div>',
                        f'<div class="metric-value">{safe(metric_display(row))}</div>',
                        f'<div class="metric-detail">Target: {safe(metric_display(pd.Series({**row.to_dict(), "current_value": row["target"]})))} '
                        f'<span class="status-badge {status_class(status)}">{safe(status)}</span></div>',
                        "</div>",
                    ]
                ),
                unsafe_allow_html=True,
            )


def render_model_evidence(
    metrics: pd.DataFrame,
    quality: pd.DataFrame,
    history: pd.DataFrame,
) -> None:
    section_header(
        "Model and Data Evidence",
        "This page connects dashboard outputs back to validation targets, modeling choices, and dbt data-quality checks.",
    )
    render_metric_cards(metrics)

    section_header(
        "Evaluation Contract",
        "The model is judged through several lenses because a World Cup submission has to predict both a believable score and a usable tournament path.",
    )
    st.markdown(
        '<div class="method-grid">'
        + "".join(
            [
                method_card(
                    "Time-based holdout",
                    "Training uses matches before 2022, while holdout validation uses later matches. That keeps the evaluation closer to a real forecasting workflow.",
                    "Validation",
                ),
                method_card(
                    "Tournament calibration",
                    "A 2018-2021 tournament-focused slice tuned draw behavior and the scoreline/outcome blend so the model does not overfit ordinary friendlies.",
                    "Calibration",
                ),
                method_card(
                    "Exact score emphasis",
                    "Exact score is rare, but the competition rewards it heavily. Conservative outcomes such as 1-0 and 1-1 are common because they are both realistic and high-value.",
                    "Scoring",
                ),
                method_card(
                    "Outcome consistency",
                    "The direct outcome model can be stronger than raw rounded scores, but the final submitted scoreline is reconciled so the winner, draw, and bracket do not disagree.",
                    "Submission",
                ),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    metric_labels = {
        "rounded_scoreline_outcome_accuracy": "Rounded score outcome",
        "direct_outcome_accuracy": "Direct outcome",
        "blended_scoreline_outcome_accuracy": "Blended outcome",
        "reconciled_scoreline_exact_accuracy": "Exact score",
        "average_goals_mae": "Average goals MAE",
    }
    metric_frame = metrics.copy()
    metric_frame["metric_label"] = metric_frame["metric_name"].map(metric_labels)
    metric_frame["current_display"] = metric_frame.apply(
        lambda row: row["current_value"]
        if row["direction"] == "lower"
        else row["current_value"] * 100,
        axis=1,
    )
    metric_frame["target_display"] = metric_frame.apply(
        lambda row: row["target"] if row["direction"] == "lower" else row["target"] * 100,
        axis=1,
    )

    chart_cols = st.columns([1.05, 0.95])
    with chart_cols[0]:
        accuracy_metrics = metric_frame[metric_frame["direction"] == "higher"].copy()
        long_metrics = accuracy_metrics.melt(
            id_vars=["metric_label", "status"],
            value_vars=["current_display", "target_display"],
            var_name="series",
            value_name="value",
        )
        long_metrics["series"] = long_metrics["series"].map(
            {"current_display": "Current", "target_display": "Target"}
        )
        fig = px.bar(
            long_metrics,
            x="value",
            y="metric_label",
            color="series",
            orientation="h",
            barmode="group",
            labels={"metric_label": "", "value": "Accuracy (%)", "series": ""},
            color_discrete_map={
                "Current": PALETTE["blue"],
                "Target": PALETTE["cyan"],
            },
        )
        fig = polish_figure(fig, 360)
        fig.update_xaxes(range=[0, 70])
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="model_metrics_accuracy",
        )

    with chart_cols[1]:
        quality_summary = quality.copy()
        quality_summary["check_label"] = quality_summary["check_name"].map(title_label)
        quality_summary["group_label"] = quality_summary["check_group"].map(title_label)
        fig = px.bar(
            quality_summary,
            x="check_value",
            y="check_label",
            color="group_label",
            orientation="h",
            labels={"check_value": "Value", "check_label": "Check", "group_label": ""},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig = polish_figure(fig, 360)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config=PLOT_CONFIG,
            key="model_quality_checks",
        )

    display_table(
        metric_frame,
        [
            "metric_label",
            "current_value",
            "guardrail",
            "target",
            "stretch",
            "status",
        ],
        {
            "metric_label": "Metric",
            "current_value": "Current",
            "guardrail": "Guardrail",
            "target": "Target",
            "stretch": "Stretch",
            "status": "Status",
        },
    )

    section_header(
        "dbt Usage in the Project",
        "dbt is the analytics engineering backbone. It turns raw soccer files into trustworthy feature tables and dashboard marts before Python ever trains a model.",
    )
    st.markdown(
        '<div class="method-grid">'
        + "".join(
            [
                method_card(
                    "Staging models",
                    "Clean raw fixtures, rankings, results, squads, and event files into predictable names, types, and source-aware fields.",
                    "Clean",
                ),
                method_card(
                    "Feature models",
                    "Build features_historical_match_training and 2026 scoring rows with rolling form, point-in-time ranking joins, Elo, squad, and event signals.",
                    "Model",
                ),
                method_card(
                    "Marts and BI models",
                    "Publish team profiles, fixture schedules, group standings, model context, and dashboard-ready tables at stable grains.",
                    "Serve",
                ),
                method_card(
                    "Tests and contracts",
                    "Protect row counts, uniqueness, accepted values, playoff-team resolution, feature coverage, and leakage prevention.",
                    "Trust",
                ),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    section_header("Historical Goal Environment")
    recent_history = history[history["match_year"] >= 1992].copy()
    history_summary = (
        recent_history.groupby("match_year", as_index=False)
        .agg(matches=("matches", "sum"), avg_total_goals=("avg_total_goals", "mean"))
        .tail(35)
    )
    fig = px.line(
        history_summary,
        x="match_year",
        y="avg_total_goals",
        markers=True,
        labels={"match_year": "Year", "avg_total_goals": "Average total goals"},
    )
    fig.update_traces(line_color=PALETTE["orange"])
    fig = polish_figure(fig, 330)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=PLOT_CONFIG,
        key="model_goal_environment",
    )


def main() -> None:
    data = load_data()
    matches = data["matches"]
    standings = data["standings"]
    teams = data["teams"]
    context = data["context"]
    metrics = data["metrics"]
    quality = data["quality"]
    history = data["history"]

    render_header()
    selected_team, selected_group = render_sidebar(teams, standings)

    tabs = st.tabs(
        [
            "Project Story",
            "Executive",
            "Bracket",
            "Groups",
            "Team Lens",
            "Matches",
            "Model Evidence",
        ]
    )

    with tabs[0]:
        render_project_story(matches, metrics, quality, history)
    with tabs[1]:
        render_executive_view(matches, metrics, teams, selected_team)
    with tabs[2]:
        render_bracket(matches, selected_team)
    with tabs[3]:
        render_groups(matches, standings, teams, selected_group, selected_team)
    with tabs[4]:
        render_team_lens(teams, matches, selected_team)
    with tabs[5]:
        render_matches(matches, context, selected_group, selected_team)
    with tabs[6]:
        render_model_evidence(metrics, quality, history)


if __name__ == "__main__":
    main()
