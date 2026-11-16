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
    "interview_answers",
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
    assert {"readiness_score", "status", "created_at"} <= set(analysis_columns.keys())
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


def test_interview_result_schema_shape():
    """Bảng kết quả phỏng vấn phải có điểm, thời điểm và ràng buộc cần thiết."""
    session_columns = Base.metadata.tables["interview_sessions"].columns
    assert "total_score" in session_columns
    assert "completed_at" in session_columns

    session_checks = {
        constraint.name
        for constraint in Base.metadata.tables["interview_sessions"].constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_interview_sessions_status" in session_checks

    answer_columns = Base.metadata.tables["interview_answers"].columns
    assert {"question_id", "answer_text", "score", "feedback", "created_at"} <= set(
        answer_columns.keys()
    )
    assert answer_columns["question_id"].nullable is False
    assert answer_columns["score"].nullable is False

    answer_foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in Base.metadata.tables["interview_answers"].foreign_keys
    }
    assert answer_foreign_keys == {"interview_questions.id"}

    unique_names = {
        constraint.name
        for constraint in Base.metadata.tables["interview_answers"].constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert "uq_interview_answers_question" in unique_names

    check_names = {
        constraint.name
        for constraint in Base.metadata.tables["interview_answers"].constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_interview_answers_score" in check_names
