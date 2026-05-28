from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
PALETTE = {
    "home": "#2563eb",
    "away": "#f97316",
    "draw": "#14b8a6",
    "group": "#2563eb",
    "knockout": "#f97316",
    "guardrail": "#f59e0b",
    "target": "#16a34a",
    "stretch": "#0f766e",
    "below_guardrail": "#dc2626",
}
px.defaults.template = "plotly_white"


st.set_page_config(
    page_title="World Cup 2026 Prediction Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            background: #ffffff;
        }
        div[data-testid="stMetric"] * {
            color: #0f172a !important;
        }
        div[data-testid="stMetricLabel"] {
            color: #475569;
        }
        .small-note {
            color: #64748b;
            font-size: 0.92rem;
            margin-top: -0.4rem;
        }
        .metric-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.85rem 0.95rem;
            min-height: 6.15rem;
            margin-bottom: 0.75rem;
        }
        .metric-card-label {
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.2;
            margin-bottom: 0.7rem;
        }
        .metric-card-value {
            color: #0f172a;
            font-size: 1.75rem;
            font-weight: 500;
            line-height: 1.1;
            overflow-wrap: anywhere;
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
    data["matches"]["date_utc"] = pd.to_datetime(data["matches"]["date_utc"])
    data["context"]["match_date_utc"] = pd.to_datetime(data["context"]["match_date_utc"])
    return data


def metric_value(metrics: pd.DataFrame, metric_name: str) -> float:
    row = metrics.loc[metrics["metric_name"] == metric_name]
    if row.empty:
        return float("nan")
    return float(row.iloc[0]["current_value"])


def pct(value: float) -> str:
    return f"{value:.1%}"


def metric_card(label: str, value: object) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card-label">{label}</div>
            <div class="metric-card-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def selected_team_matches(matches: pd.DataFrame, team: str) -> pd.DataFrame:
    if team == "All teams":
        return matches
    return matches[
        (matches["predicted_home_team"] == team)
        | (matches["predicted_away_team"] == team)
        | (matches["home_team"] == team)
        | (matches["away_team"] == team)
    ].copy()


def apply_global_filters(
    matches: pd.DataFrame,
    phase: str,
    group: str,
    team: str,
) -> pd.DataFrame:
    filtered = matches.copy()
    if phase != "All phases":
        filtered = filtered[filtered["competition_phase"] == phase]
    if group != "All groups":
        filtered = filtered[filtered["group"] == group]
    return selected_team_matches(filtered, team)


def clean_table(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame[columns].copy()


def outcome_distribution(matches: pd.DataFrame) -> pd.DataFrame:
    result = (
        matches.groupby(["competition_phase", "winner_label"], dropna=False)
        .size()
        .reset_index(name="matches")
    )
    result["winner_label"] = result["winner_label"].str.title()
    return result


def final_match(matches: pd.DataFrame) -> pd.Series:
    return matches.loc[matches["match_id"] == 104].iloc[0]


def third_place_match(matches: pd.DataFrame) -> pd.Series:
    return matches.loc[matches["match_id"] == 103].iloc[0]


def opponent_from_final(final_row: pd.Series) -> str:
    teams = [final_row["predicted_home_team"], final_row["predicted_away_team"]]
    return str(teams[1] if final_row["predicted_winner_team"] == teams[0] else teams[0])


def render_header() -> None:
    st.title("FIFA World Cup 2026 Prediction Analytics")
    st.markdown(
        '<p class="small-note">A dbt + Python forecasting project with validated competition outputs and dashboard-ready marts.</p>',
        unsafe_allow_html=True,
    )


def render_overview(matches: pd.DataFrame, metrics: pd.DataFrame) -> None:
    final_row = final_match(matches)
    third_row = third_place_match(matches)
    champion = final_row["predicted_winner_team"]
    runner_up = opponent_from_final(final_row)
    third_place = third_row["predicted_winner_team"]

    metric_cols = st.columns(3)
    with metric_cols[0]:
        metric_card("Champion", champion)
    with metric_cols[1]:
        metric_card("Runner-up", runner_up)
    with metric_cols[2]:
        metric_card("Third place", third_place)
    metric_cols = st.columns(2)
    with metric_cols[0]:
        metric_card("Total goals", int(matches["total_goals"].sum()))
    with metric_cols[1]:
        metric_card("Penalty matches", int(matches["penalties"].sum()))

    chart_cols = st.columns([1.1, 0.9])
    with chart_cols[0]:
        distribution = outcome_distribution(matches)
        fig = px.bar(
            distribution,
            x="competition_phase",
            y="matches",
            color="winner_label",
            barmode="group",
            labels={
                "competition_phase": "Phase",
                "winner_label": "Result",
                "matches": "Matches",
            },
            color_discrete_map={
                "Home": PALETTE["home"],
                "Away": PALETTE["away"],
                "Draw": PALETTE["draw"],
            },
        )
        fig.update_layout(height=360, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

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
            color_continuous_scale=["#fef3c7", "#f97316"],
        )
        fig.update_layout(height=360, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Final Four")
    final_four = matches[matches["match_id"].isin([101, 102, 103, 104])].copy()
    st.dataframe(
        clean_table(
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
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Model Snapshot")
    quality_cols = st.columns(4)
    quality_cols[0].metric(
        "Direct outcome accuracy",
        pct(metric_value(metrics, "direct_outcome_accuracy")),
    )
    quality_cols[1].metric(
        "Blended outcome accuracy",
        pct(metric_value(metrics, "blended_scoreline_outcome_accuracy")),
    )
    quality_cols[2].metric(
        "Exact score accuracy",
        pct(metric_value(metrics, "reconciled_scoreline_exact_accuracy")),
    )
    quality_cols[3].metric("Average goals MAE", "0.907")


def render_group_stage(
    matches: pd.DataFrame,
    standings: pd.DataFrame,
    selected_group: str,
) -> None:
    groups = sorted(standings["group_letter"].dropna().unique())
    group = selected_group if selected_group != "All groups" else groups[0]
    group_standings = standings[standings["group_letter"] == group].copy()
    group_matches = matches[matches["group"] == group].copy()

    st.subheader(f"Group {group}")
    col_left, col_right = st.columns([0.95, 1.05])
    with col_left:
        st.dataframe(
            clean_table(
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
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col_right:
        fig = px.bar(
            group_standings.sort_values("group_rank"),
            x="team_name",
            y="points",
            color="goal_difference",
            labels={
                "team_name": "Team",
                "points": "Points",
                "goal_difference": "Goal difference",
            },
            color_continuous_scale=["#f97316", "#f8fafc", "#14b8a6"],
        )
        fig.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Group Matches")
    st.dataframe(
        clean_table(
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
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_team_profiles(teams: pd.DataFrame, selected_team: str) -> None:
    teams_for_chart = teams.copy()
    team = (
        selected_team
        if selected_team != "All teams"
        else teams.sort_values("fifa_rank").iloc[0]["team_name"]
    )
    profile = teams.loc[teams["team_name"] == team].iloc[0]

    st.subheader(team)
    profile_cols = st.columns(5)
    profile_cols[0].metric("FIFA rank", int(profile["fifa_rank"]))
    profile_cols[1].metric("FIFA points", f"{profile['fifa_points']:.0f}")
    profile_cols[2].metric("Last 10 PPM", f"{profile['last_10_points_per_match']:.2f}")
    profile_cols[3].metric("Squad players", int(profile["squad_players"]))
    profile_cols[4].metric("Data completeness", f"{profile['profile_completeness_score']:.0%}")

    chart_cols = st.columns([1.05, 0.95])
    with chart_cols[0]:
        fig = px.scatter(
            teams_for_chart,
            x="fifa_rank",
            y="overall_star_power_z",
            color="confederation",
            size="last_10_points_per_match",
            hover_name="team_name",
            labels={
                "fifa_rank": "FIFA rank",
                "overall_star_power_z": "Squad star power z-score",
                "confederation": "Confederation",
                "last_10_points_per_match": "Last 10 PPM",
            },
        )
        fig.update_xaxes(autorange="reversed")
        fig.update_layout(height=420, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    with chart_cols[1]:
        top_form = teams_for_chart.nlargest(12, "last_10_points_per_match")
        fig = px.bar(
            top_form.sort_values("last_10_points_per_match"),
            x="last_10_points_per_match",
            y="team_name",
            orientation="h",
            labels={
                "team_name": "Team",
                "last_10_points_per_match": "Last 10 points per match",
            },
            color="overall_star_power_z",
            color_continuous_scale=["#f97316", "#f8fafc", "#14b8a6"],
        )
        fig.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Team Profile Table")
    st.dataframe(
        clean_table(
            teams_for_chart.sort_values("fifa_rank"),
            [
                "team_name",
                "group_letter",
                "fifa_rank",
                "last_10_points_per_match",
                "last_10_goal_diff_per_match",
                "overall_star_power_z",
                "attacking_star_power_z",
                "avg_corners_for",
                "blended_yellow_cards_for",
                "profile_completeness_score",
            ],
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_match_explorer(
    matches: pd.DataFrame,
    context: pd.DataFrame,
    phase: str,
    group: str,
    team: str,
) -> None:
    filtered = apply_global_filters(matches, phase, group, team)
    st.subheader("Match Predictions")
    st.dataframe(
        clean_table(
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
        ),
        use_container_width=True,
        hide_index=True,
    )

    group_context = context.copy()
    if group != "All groups":
        group_context = group_context[group_context["group_letter"] == group]
    if team != "All teams":
        group_context = group_context[
            (group_context["home_team"] == team) | (group_context["away_team"] == team)
        ]

    st.subheader("Group Match Feature Context")
    st.dataframe(
        clean_table(
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
        ),
        use_container_width=True,
        hide_index=True,
    )


def render_model_quality(metrics: pd.DataFrame, quality: pd.DataFrame, history: pd.DataFrame) -> None:
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
        long_metrics = metric_frame.melt(
            id_vars=["metric_label", "status"],
            value_vars=["current_display", "target_display"],
            var_name="series",
            value_name="value",
        )
        fig = px.bar(
            long_metrics,
            x="metric_label",
            y="value",
            color="series",
            barmode="group",
            labels={"metric_label": "Metric", "value": "Value", "series": ""},
            color_discrete_map={
                "current_display": "#2563eb",
                "target_display": "#14b8a6",
            },
        )
        fig.update_layout(height=380, xaxis_tickangle=-20, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    with chart_cols[1]:
        quality_summary = quality.copy()
        fig = px.bar(
            quality_summary,
            x="check_value",
            y="check_name",
            color="check_group",
            orientation="h",
            labels={"check_value": "Value", "check_name": "Check", "check_group": ""},
        )
        fig.update_layout(height=380, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Metric Targets")
    st.dataframe(metric_frame, use_container_width=True, hide_index=True)

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
    fig.update_traces(line_color="#f97316")
    fig.update_layout(height=330)
    st.plotly_chart(fig, use_container_width=True)


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

    groups = ["All groups", *sorted(standings["group_letter"].dropna().unique())]
    team_names = ["All teams", *sorted(teams["team_name"].dropna().unique())]
    phases = ["All phases", *sorted(matches["competition_phase"].dropna().unique())]

    with st.sidebar:
        st.header("Filters")
        selected_phase = st.selectbox("Phase", phases)
        selected_group = st.selectbox("Group", groups)
        selected_team = st.selectbox("Team", team_names)

    tab_overview, tab_groups, tab_teams, tab_matches, tab_quality = st.tabs(
        ["Overview", "Group Stage", "Team Profiles", "Match Explorer", "Model Quality"]
    )

    with tab_overview:
        render_overview(matches, metrics)
    with tab_groups:
        render_group_stage(matches, standings, selected_group)
    with tab_teams:
        render_team_profiles(teams, selected_team)
    with tab_matches:
        render_match_explorer(
            matches,
            context,
            selected_phase,
            selected_group,
            selected_team,
        )
    with tab_quality:
        render_model_quality(metrics, quality, history)


if __name__ == "__main__":
    main()
