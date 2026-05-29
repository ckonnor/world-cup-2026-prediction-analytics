import importlib.util
from pathlib import Path

import pandas as pd


APP_DATA_DIR = Path("app/data")


EXPECTED_FILES = {
    "dashboard_data_quality.csv",
    "dashboard_group_standings.csv",
    "dashboard_historical_competition_summary.csv",
    "dashboard_match_feature_context.csv",
    "dashboard_match_predictions.csv",
    "dashboard_model_metrics.csv",
    "dashboard_team_profiles.csv",
}


def _read_dashboard_csv(file_name: str) -> pd.DataFrame:
    path = APP_DATA_DIR / file_name
    assert path.exists(), f"Missing dashboard snapshot file: {path}"
    return pd.read_csv(path)


def _load_streamlit_app_module():
    spec = importlib.util.spec_from_file_location(
        "world_cup_streamlit_app",
        Path("app/streamlit_app.py"),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dashboard_snapshot_files_are_present() -> None:
    actual_files = {path.name for path in APP_DATA_DIR.glob("dashboard_*.csv")}
    assert actual_files == EXPECTED_FILES


def test_dashboard_match_predictions_contract() -> None:
    predictions = _read_dashboard_csv("dashboard_match_predictions.csv")

    required_columns = {
        "match_id",
        "competition_phase",
        "group",
        "round",
        "date_utc",
        "venue",
        "predicted_home_team",
        "predicted_away_team",
        "predicted_home_goals",
        "predicted_away_goals",
        "corners",
        "yellow_cards",
        "red_cards",
        "winner_label",
        "penalties",
        "scoreline",
        "predicted_winner_team",
    }
    assert required_columns.issubset(predictions.columns)
    assert len(predictions) == 104
    assert predictions["match_id"].is_unique
    assert set(predictions["competition_phase"]) == {"group", "knockout"}
    assert (predictions["competition_phase"] == "group").sum() == 72
    assert (predictions["competition_phase"] == "knockout").sum() == 32
    assert predictions["predicted_home_team"].notna().all()
    assert predictions["predicted_away_team"].notna().all()
    assert predictions["scoreline"].str.match(r"^\d+-\d+$").all()

    non_negative_columns = [
        "predicted_home_goals",
        "predicted_away_goals",
        "corners",
        "yellow_cards",
        "red_cards",
    ]
    for column in non_negative_columns:
        assert (predictions[column] >= 0).all()


def test_dashboard_group_and_team_contracts() -> None:
    standings = _read_dashboard_csv("dashboard_group_standings.csv")
    teams = _read_dashboard_csv("dashboard_team_profiles.csv")

    assert len(standings) == 48
    assert len(teams) == 48
    assert {
        "current_elo",
        "last_10_adjusted_points_per_match",
        "last_10_adjusted_goal_diff_per_match",
    }.issubset(teams.columns)
    assert teams["team_name"].is_unique
    assert standings[["group_letter", "team_name"]].drop_duplicates().shape[0] == 48
    assert set(standings["group_letter"]) == set("ABCDEFGHIJKL")
    assert set(teams["group_letter"]) == set("ABCDEFGHIJKL")
    assert standings["team_name"].isin(teams["team_name"]).all()
    assert teams["profile_completeness_score"].between(0, 1).all()


def test_dashboard_metrics_contract() -> None:
    metrics = _read_dashboard_csv("dashboard_model_metrics.csv")
    quality = _read_dashboard_csv("dashboard_data_quality.csv")

    expected_metrics = {
        "rounded_scoreline_outcome_accuracy",
        "direct_outcome_accuracy",
        "blended_scoreline_outcome_accuracy",
        "reconciled_scoreline_exact_accuracy",
        "average_goals_mae",
    }
    assert set(metrics["metric_name"]) == expected_metrics
    assert metrics["current_value"].notna().all()
    assert metrics["status"].isin({"below_guardrail", "guardrail", "target", "stretch"}).all()

    validation = quality.loc[
        (quality["check_group"] == "submission_validation")
        & (quality["check_name"] == "valid"),
        "check_value",
    ]
    assert validation.tolist() == [1]


def test_streamlit_table_helper_omits_none_height() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "st.dataframe(table, use_container_width=True, hide_index=True, height=height)" not in source
    assert 'if height is not None:' in source
    assert "display_columns = available_columns(frame, columns)" in source


def test_dashboard_includes_portfolio_case_study_story() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "Overview" in source
    assert "Project Build" in source
    assert "Analytics Engineering Pipeline" in source
    assert "features_historical_match_training" in source
    assert "Target Rationale" in source


def test_dashboard_navigation_is_consolidated() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    tab_section = source.split("tabs = st.tabs(", 1)[1].split("with tabs[0]:", 1)[0]

    assert '"Overview"' in tab_section
    assert '"Tournament"' in tab_section
    assert '"Teams"' in tab_section
    assert '"Methodology"' in tab_section
    for retired_tab in [
        '"Project Story"',
        '"Executive"',
        '"Bracket"',
        '"Groups"',
        '"Team Lens"',
        '"Matches"',
        '"Model Evidence"',
    ]:
        assert retired_tab not in tab_section


def test_team_profile_table_explains_model_columns() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "st.column_config.Column(help=help_text)" in source
    assert "available_columns(" in source
    assert "Intl Pedigree" in source
    assert "How strong the team has performed over time" in source
    assert "Official FIFA ranking points" in source
    assert "How much better or worse the team performed than expected" in source
    assert "How battle-tested this squad is at senior international level" in source
    assert "A dashboard-only composite view of team strength" in source
    assert "Coverage is a data-completeness check" in source


def test_team_profile_enrichment_supports_older_dashboard_exports() -> None:
    streamlit_app = _load_streamlit_app_module()
    stale_export = pd.DataFrame(
        {
            "team_name": ["Example FC"],
            "fifa_points": [None],
        }
    )

    enriched = streamlit_app.add_strength_index(stale_export)

    required_columns = {
        "confederation",
        "current_elo",
        "last_10_adjusted_points_per_match",
        "last_10_adjusted_goal_diff_per_match",
        "overall_star_power_z",
        "attacking_star_power_z",
        "dashboard_strength_index",
        "profile_completeness_score",
    }
    assert required_columns.issubset(enriched.columns)
    assert enriched.loc[0, "confederation"] == "Unknown"
    assert enriched.loc[0, "current_elo"] == 1500.0
    assert enriched.loc[0, "dashboard_strength_index"] == 50.0
