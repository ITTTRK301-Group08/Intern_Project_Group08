from app.database.base import Base
import app.models  # noqa: F401


EXPECTED_TABLES = {
    "users",
    "student_profiles",
    "cvs",
    "career_categories",
    "career_roles",
    "skills",
    "profile_strengths",
    "profile_skills",
    "career_role_skills",
    "cv_experiences",
    "cv_educations",
    "analyses",
    "analysis_skill_gaps",
    "learning_resources",
    "learning_plans",
    "learning_plan_items",
}


def test_schema_has_normalized_mysql_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES

    for table in Base.metadata.tables.values():
        mysql_options = table.dialect_options["mysql"]
        assert mysql_options["engine"] == "InnoDB"
        assert mysql_options["charset"] == "utf8mb4"

    profile_columns = Base.metadata.tables["student_profiles"].columns
    assert "strengths" not in profile_columns
    assert "self_assessed_skills" not in profile_columns
    assert "target_role_id" in profile_columns

    analysis_columns = Base.metadata.tables["analyses"].columns
    assert {
        "readiness_score",
        "market_source",
        "benchmark_date",
        "status",
        "created_at",
    } <= set(analysis_columns.keys())
    analysis_indexes = {
        tuple(column.name for column in index.columns)
        for index in Base.metadata.tables["analyses"].indexes
    }
    assert ("user_id", "created_at") in analysis_indexes

    skill_gap_columns = Base.metadata.tables["analysis_skill_gaps"].columns
    assert {"evidence", "has_evidence"} <= set(skill_gap_columns.keys())

    profile_skill_forekeys = {
        foreign_key.target_fullname
        for foreign_key in Base.metadata.tables["profile_skills"].foreign_keys
    }
    assert profile_skill_forekeys == {
        "student_profiles.id",
        "skills.id",
    }

    resource_forekeys = {
        foreign_key.target_fullname
        for foreign_key in Base.metadata.tables["learning_resources"].foreign_keys
    }
    assert resource_forekeys == {"skills.id"}

    plan_forekeys = {
        foreign_key.target_fullname
        for foreign_key in Base.metadata.tables["learning_plans"].foreign_keys
    }
    assert plan_forekeys == {"analyses.id", "users.id"}

    plan_item_forekeys = {
        foreign_key.target_fullname
        for foreign_key in Base.metadata.tables["learning_plan_items"].foreign_keys
    }
    assert plan_item_forekeys == {
        "learning_plans.id",
        "skills.id",
        "learning_resources.id",
    }
