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
    "interview_sessions",
    "interview_questions",
<<<<<<< HEAD
    "refresh_tokens",
=======
    "interview_answers",
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
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
    assert {
        index.name for index in Base.metadata.tables["student_profiles"].indexes
    } >= {"ix_student_profiles_target_role_id"}

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

    analysis_columns = Base.metadata.tables["analyses"].columns
    assert "source_type" in analysis_columns
    assert "readiness_score" in analysis_columns

    gap_columns = Base.metadata.tables["analysis_skill_gaps"].columns
    assert {"current_level", "target_level", "gap", "is_required", "weight"} <= set(
        gap_columns.keys()
    )

    refresh_columns = Base.metadata.tables["refresh_tokens"].columns
    assert {
        "user_id",
        "token_hash",
        "family_id",
        "expires_at",
        "revoked_at",
    } <= set(refresh_columns.keys())
    assert {
        foreign_key.target_fullname
        for foreign_key in Base.metadata.tables["refresh_tokens"].foreign_keys
    } == {"users.id"}
