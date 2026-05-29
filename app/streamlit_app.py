from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
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
    "home": "#2563eb",
    "away": "#f97316",
    "draw": "#14b8a6",
    "target": "#16a34a",
    "guardrail": "#f59e0b",
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
            padding-top: 1.35rem;
            padding-bottom: 2.5rem;
        }
        .small-note {
            color: #64748b;
            font-size: 0.94rem;
            margin-top: -0.35rem;
            max-width: 58rem;
        }
        .section-note {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 0.75rem;
        }
        .metric-card, .story-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.9rem 1rem;
            margin-bottom: 0.75rem;
        }
        .metric-card {
            min-height: 6.05rem;
        }
        .metric-card-label {
            color: #475569;
            font-size: 0.88rem;
            line-height: 1.2;
            margin-bottom: 0.7rem;
        }
        .metric-card-value {
            color: #0f172a;
            font-size: 1.7rem;
            font-weight: 550;
            line-height: 1.1;
            overflow-wrap: anywhere;
        }
        .story-card-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 650;
            margin-bottom: 0.35rem;
        }
        .story-card-body {
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.45;
        }
        .bracket-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(112px, 1fr));
            gap: 0.55rem;
            align-items: start;
        }
        .round-column {
            min-width: 0;
        }
        .round-title {
            color: #334155;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .match-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.5rem;
            margin-bottom: 0.55rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .match-card.focus {
            border: 2px solid #2563eb;
            background: #eff6ff;
        }
        .match-meta {
            color: #64748b;
            font-size: 0.72rem;
            margin-bottom: 0.35rem;
        }
        .team-line {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            color: #334155;
            font-size: 0.78rem;
            line-height: 1.3;
            margin: 0.12rem 0;
        }
        .team-line.winner {
            color: #0f172a;
            font-weight: 750;
        }
        .winner-note {
            color: #0f766e;
            font-size: 0.7rem;
            font-weight: 650;
            margin-top: 0.35rem;
        }
        @media (max-width: 1100px) {
            .bracket-grid {
                grid-template-columns: repeat(2, minmax(150px, 1fr));
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
    data["matches"]["date_utc"] = pd.to_datetime(data["matches"]["date_utc"])
    data["context"]["match_date_utc"] = pd.to_datetime(data["context"]["match_date_utc"])
    return data


def pct(value: float) -> str:
    return f"{value:.1%}"


def metric_value(metrics: pd.DataFrame, metric_name: str) -> float:
    row = metrics.loc[metrics["metric_name"] == metric_name]
    if row.empty:
        return float("nan")
    return float(row.iloc[0]["current_value"])


def metric_card(label: str, value: object) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card-label">{html.escape(str(label))}</div>
            <div class="metric-card-value">{html.escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def story_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="story-card">
            <div class="story-card-title">{html.escape(title)}</div>
            <div class="story-card-body">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_note(text: str) -> None:
    st.markdown(
        f'<p class="section-note">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def display_table(frame: pd.DataFrame, columns: list[str], labels: dict[str, str]) -> None:
    table = frame[columns].rename(columns=labels)
    st.dataframe(table, use_container_width=True, hide_index=True)


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


def outcome_distribution(matches: pd.DataFrame) -> pd.DataFrame:
    result = (
        matches.groupby(["competition_phase", "winner_label"], dropna=False)
        .size()
        .reset_index(name="matches")
    )
    result["winner_label"] = result["winner_label"].str.title()
    result["phase_label"] = result["competition_phase"].map(PHASE_LABELS)
    return result


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
                result = f"{result} on pens"

        rows.append(
            {
                "Match": row_dict["match_id"],
                "Stage": row_dict["round"],
                "Opponent": opponent,
                "Score": f"{goals_for}-{goals_against}",
                "Result": result,
            }
        )
    return pd.DataFrame(rows)


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


def render_header() -> None:
    st.title("FIFA World Cup 2026 Prediction Analytics")
    st.markdown(
        '<p class="small-note">A portfolio dashboard for a dbt + Python forecasting project. It is meant to explain the model output, not only display the raw tables.</p>',
        unsafe_allow_html=True,
    )


def render_overview(
    matches: pd.DataFrame,
    metrics: pd.DataFrame,
    selected_team: str,
) -> None:
    final_row = final_match(matches)
    third_row = third_place_match(matches)
    champion = final_row["predicted_winner_team"]
    runner_up = runner_up_from_final(final_row)
    third_place = third_row["predicted_winner_team"]

    metric_cols = st.columns(3)
    with metric_cols[0]:
        metric_card("Predicted champion", champion)
    with metric_cols[1]:
        metric_card("Runner-up", runner_up)
    with metric_cols[2]:
        metric_card("Third place", third_place)

    metric_cols = st.columns(4)
    with metric_cols[0]:
        metric_card("Tournament goals", int(matches["total_goals"].sum()))
    with metric_cols[1]:
        metric_card("Penalty matches", int(matches["penalties"].sum()))
    with metric_cols[2]:
        metric_card(
            "Blended outcome accuracy",
            pct(metric_value(metrics, "blended_scoreline_outcome_accuracy")),
        )
    with metric_cols[3]:
        metric_card(
            "Exact score accuracy",
            pct(metric_value(metrics, "reconciled_scoreline_exact_accuracy")),
        )

    story_cols = st.columns(3)
    with story_cols[0]:
        story_card(
            "How to read this",
            "The dashboard follows the tournament story: overall forecast, bracket, groups, teams, then model quality.",
        )
    with story_cols[1]:
        story_card(
            "What the model is doing",
            "dbt prepares tested feature tables. Python estimates goals and outcomes, then simulates the bracket from the group predictions.",
        )
    with story_cols[2]:
        story_card(
            "What is uncertain",
            "Exact scores are hard to predict, so the model is conservative. Close knockout matches often become 1-1 penalty decisions.",
        )

    if selected_team != "All teams":
        st.subheader(f"{selected_team} Path")
        journey = team_journey(matches, selected_team)
        if journey.empty:
            st.info("This team does not appear in the current predicted tournament path.")
        else:
            display_table(
                journey,
                ["Match", "Stage", "Opponent", "Score", "Result"],
                {},
            )

    chart_cols = st.columns([1, 1])
    with chart_cols[0]:
        distribution = outcome_distribution(matches)
        fig = px.bar(
            distribution,
            x="phase_label",
            y="matches",
            color="winner_label",
            barmode="group",
            labels={
                "phase_label": "Phase",
                "winner_label": "Result",
                "matches": "Matches",
            },
            color_discrete_map={
                "Home": PALETTE["home"],
                "Away": PALETTE["away"],
                "Draw": PALETTE["draw"],
            },
        )
        fig.update_layout(height=340, legend_title_text="")
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
        fig.update_layout(height=340, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)


def bracket_card(row: pd.Series, selected_team: str) -> str:
    home_team, away_team = match_team_names(row)
    winner = str(row["predicted_winner_team"])
    focus = selected_team != "All teams" and selected_team in {home_team, away_team}
    penalties = " on penalties" if bool(row["penalties"]) else ""

    def team_line(team: str, goals: int) -> str:
        winner_class = " winner" if team == winner else ""
        return "\n".join(
            [
                f'<div class="team-line{winner_class}">',
                f"<span>{html.escape(team)}</span>",
                f"<span>{int(goals)}</span>",
                "</div>",
            ]
        )

    return "\n".join(
        [
            f'<div class="match-card{" focus" if focus else ""}">',
            f'<div class="match-meta">Match {int(row["match_id"])}</div>',
            team_line(home_team, row["predicted_home_goals"]),
            team_line(away_team, row["predicted_away_goals"]),
            f'<div class="winner-note">{html.escape(winner)} wins{penalties}</div>',
            "</div>",
        ]
    )


def render_bracket(matches: pd.DataFrame, selected_team: str) -> None:
    st.subheader("Predicted Knockout Bracket")
    section_note(
        "Each card shows the predicted matchup, scoreline, and advancing team. If a team is selected in the sidebar, its knockout matches are highlighted."
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
                    f'<div class="round-title">{html.escape(round_name)}</div>',
                    cards,
                    "</div>",
                ]
            )
        )
    st.markdown(
        f'<div class="bracket-grid">{"".join(columns)}</div>',
        unsafe_allow_html=True,
    )

    final_four = knockout[knockout["match_id"].isin([101, 102, 103, 104])]
    st.subheader("Final Four Detail")
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


def render_group_stage(
    matches: pd.DataFrame,
    standings: pd.DataFrame,
    teams: pd.DataFrame,
    selected_group: str,
    selected_team: str,
) -> None:
    group = effective_group(selected_group, selected_team, teams)
    if selected_group == "All groups" and selected_team != "All teams":
        section_note(f"Showing Group {group}, because {selected_team} is the selected team.")
    else:
        section_note("Use the group focus control in the sidebar to inspect a different group.")

    group_standings = standings[standings["group_letter"] == group].copy()
    group_matches = matches[matches["group"] == group].copy()

    st.subheader(f"Group {group}")
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
        labels={
            "team_name": "Team",
            "points": "Points",
            "goal_difference": "Goal difference",
        },
        color_continuous_scale=["#f97316", "#f8fafc", "#14b8a6"],
    )
    fig.update_layout(height=300, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Group Matches")
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


def render_team_profiles(
    teams: pd.DataFrame,
    matches: pd.DataFrame,
    selected_team: str,
) -> None:
    if selected_team == "All teams":
        st.subheader("Team Comparison")
        section_note("Select a team in the sidebar for a focused profile. This view compares the field.")
        chart_cols = st.columns([1.05, 0.95])
        with chart_cols[0]:
            fig = px.scatter(
                teams,
                x="fifa_rank",
                y="overall_star_power_z",
                color="confederation",
                size="last_10_points_per_match",
                hover_name="team_name",
                labels={
                    "fifa_rank": "FIFA rank",
                    "overall_star_power_z": "Squad star power",
                    "confederation": "Confederation",
                    "last_10_points_per_match": "Last 10 PPM",
                },
            )
            fig.update_xaxes(autorange="reversed")
            fig.update_layout(height=420, legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)

        with chart_cols[1]:
            top_form = teams.nlargest(12, "last_10_points_per_match")
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

    else:
        profile = teams.loc[teams["team_name"] == selected_team].iloc[0]
        st.subheader(selected_team)
        cols = st.columns(5)
        cols[0].metric("Group", profile["group_letter"])
        cols[1].metric("FIFA rank", int(profile["fifa_rank"]))
        cols[2].metric("Last 10 PPM", f"{profile['last_10_points_per_match']:.2f}")
        cols[3].metric("Squad players", int(profile["squad_players"]))
        cols[4].metric("Data complete", f"{profile['profile_completeness_score']:.0%}")

        st.subheader("Predicted Path")
        journey = team_journey(matches, selected_team)
        if journey.empty:
            st.info("This team does not appear in the current predicted tournament path.")
        else:
            display_table(journey, ["Match", "Stage", "Opponent", "Score", "Result"], {})

    st.subheader("Team Table")
    display_table(
        teams.sort_values("fifa_rank"),
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
        {
            "team_name": "Team",
            "group_letter": "Group",
            "fifa_rank": "FIFA Rank",
            "last_10_points_per_match": "Last 10 PPM",
            "last_10_goal_diff_per_match": "Last 10 GD",
            "overall_star_power_z": "Star Power",
            "attacking_star_power_z": "Attack",
            "avg_corners_for": "Corners For",
            "blended_yellow_cards_for": "Yellow Cards",
            "profile_completeness_score": "Data Completeness",
        },
    )


def render_match_explorer(
    matches: pd.DataFrame,
    context: pd.DataFrame,
    selected_group: str,
    selected_team: str,
) -> None:
    selected_phase = st.radio(
        "Matches to show",
        ["All matches", "Group stage", "Knockout stage"],
        horizontal=True,
    )
    filtered = filtered_match_explorer(matches, selected_phase, selected_group, selected_team)
    section_note(
        "This table honors the phase selector above plus the sidebar focus controls. Group focus applies to group-stage rows; knockout rows are controlled by phase and team."
    )
    if filtered.empty:
        st.info("No matches match the current filter combination.")
    else:
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
        )

    group_context = context.copy()
    if selected_group != "All groups":
        group_context = group_context[group_context["group_letter"] == selected_group]
    if selected_team != "All teams":
        group_context = group_context[
            (group_context["home_team"] == selected_team)
            | (group_context["away_team"] == selected_team)
        ]

    st.subheader("Why the Group Matches Lean That Way")
    section_note(
        "Positive difference values favor the listed home team. Knockout matches are simulated later, so this context table is group-stage only."
    )
    if group_context.empty:
        st.info("No group-stage feature context matches the current filters.")
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
                "overall_star_power_diff": "Star Power Diff",
                "expected_total_corners": "Corners",
                "expected_total_yellow_cards": "Yellows",
                "expected_total_red_cards": "Reds",
            },
        )


def render_model_quality(
    metrics: pd.DataFrame,
    quality: pd.DataFrame,
    history: pd.DataFrame,
) -> None:
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
        fig.update_layout(height=370, xaxis_tickangle=-20, legend_title_text="")
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
        fig.update_layout(height=370, legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Metric Detail")
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

    with st.sidebar:
        st.header("Focus Controls")
        selected_team = st.selectbox(
            "Team focus",
            team_names,
            help="Highlights this team in the bracket and filters team/match views.",
        )
        selected_group = st.selectbox(
            "Group focus",
            groups,
            help="Controls the group table and group-stage match context.",
        )
        if selected_team != "All teams":
            st.caption(
                f"Team selected: {selected_team}. Group and match views will focus on that team where possible."
            )

    tab_overview, tab_bracket, tab_groups, tab_teams, tab_matches, tab_quality = st.tabs(
        [
            "Overview",
            "Bracket",
            "Group Stage",
            "Team Profiles",
            "Match Explorer",
            "Model Quality",
        ]
    )

    with tab_overview:
        render_overview(matches, metrics, selected_team)
    with tab_bracket:
        render_bracket(matches, selected_team)
    with tab_groups:
        render_group_stage(matches, standings, teams, selected_group, selected_team)
    with tab_teams:
        render_team_profiles(teams, matches, selected_team)
    with tab_matches:
        render_match_explorer(matches, context, selected_group, selected_team)
    with tab_quality:
        render_model_quality(metrics, quality, history)


if __name__ == "__main__":
    main()
