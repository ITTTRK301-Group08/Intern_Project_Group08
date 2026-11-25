"""Unit tests for Service-layer scoring, authorization, and interview logic."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token, hash_password
from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.cv import CV
from app.models.interview import InterviewAnswer, InterviewQuestion, InterviewSession
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.models.profile_data import CareerRoleSkill
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.analysis import AIConsent
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.interview.ai_response import (
    InterviewAnswerScoreAI,
    InterviewGenerationAIResponse,
    InterviewQuestionAI,
)
from app.services import (
    analysis_service,
    auth_service,
    catalog_service,
    dashboard_service,
    interview_service,
    learning_plan_service,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _create_user(
    db_session,
    *,
    email: str,
    password: str = "StrongPass123!",
    role: str = "student",
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_role_with_skills(db_session, *, slug: str = "backend-eng") -> tuple[CareerRole, list[Skill]]:
    category = CareerCategory(name="Software Engineering", slug=f"cat-{slug}")
    db_session.add(category)
    db_session.flush()

    role = CareerRole(
        category_id=category.id,
        name="Backend Engineer",
        slug=slug,
        level="Junior",
        description="Build APIs and services.",
        is_active=True,
    )
    skill_py = Skill(name=f"Python-{slug}", is_active=True)
    skill_sql = Skill(name=f"SQL-{slug}", is_active=True)
    skill_inactive = Skill(name=f"Legacy-{slug}", is_active=False)
    db_session.add_all([role, skill_py, skill_sql, skill_inactive])
    db_session.flush()

    db_session.add_all(
        [
            CareerRoleSkill(
                career_role_id=role.id,
                skill_id=skill_py.id,
                required_level=4,
                weight=2.0,
                is_required=True,
            ),
            CareerRoleSkill(
                career_role_id=role.id,
                skill_id=skill_sql.id,
                required_level=3,
                weight=1.0,
                is_required=True,
            ),
            CareerRoleSkill(
                career_role_id=role.id,
                skill_id=skill_inactive.id,
                required_level=2,
                weight=5.0,
                is_required=False,
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(role)
    return role, [skill_py, skill_sql, skill_inactive]


# ---------------------------------------------------------------------------
# 1. Scoring Functions (Tầng Service)
# ---------------------------------------------------------------------------


class TestScoringServices:
    """Unit tests for readiness scoring, learning progress, and interview scoring."""

    def test_calculate_readiness_score_empty_and_zero_cases(self):
        assert dashboard_service.calculate_readiness_score([]) == 0.0
        assert (
            dashboard_service.calculate_readiness_score(
                [
                    {"current_level": -2, "required_level": 4, "weight": 1.0},
                    {"current_level": 0, "required_level": 5, "weight": 2.0},
                ]
            )
            == 0.0
        )

    def test_calculate_readiness_score_weighted_and_clamped(self):
        # Skill A: 2/4 = 0.5 * weight 2.0 = 1.0
        # Skill B: 6/4 -> clamped to 1.0 * weight 1.0 = 1.0
        # Total = (2.0 / 3.0) * 100 = 66.7
        items = [
            {"current_level": 2, "required_level": 4, "weight": 2.0},
            {"current_level": 6, "required_level": 4, "weight": 1.0},
        ]
        assert dashboard_service.calculate_readiness_score(items) == 66.7

    def test_calculate_readiness_score_guards_zero_weight_and_required_level(self):
        # weight=0 clamps to 0.1; required_level=0 clamps to 1
        items = [{"current_level": 1, "required_level": 0, "weight": 0}]
        assert dashboard_service.calculate_readiness_score(items) == 100.0

    def test_dashboard_summary_computes_fallback_readiness_and_skill_counts(self, db_session):
        user = _create_user(db_session, email="score-summary@example.com")
        role, skills = _create_role_with_skills(db_session, slug="summary-role")

        analysis = Analysis(
            user_id=user.id,
            career_role_id=role.id,
            consent_accepted=True,
            consent_purpose_version="v1",
            status="completed",
            readiness_score=None,  # Force calculation fallback in get_dashboard_summary
            completed_at=_utcnow(),
        )
        db_session.add(analysis)
        db_session.flush()

        db_session.add_all(
            [
                AnalysisSkillGap(
                    analysis_id=analysis.id,
                    skill_id=skills[0].id,
                    current_level=4,  # matched (4 >= 4), weight 2.0 -> 2.0
                    target_level=4,
                    has_evidence=True,
                    evidence="Python 4/5",
                ),
                AnalysisSkillGap(
                    analysis_id=analysis.id,
                    skill_id=skills[1].id,
                    current_level=1,  # gap (1 < 3), weight 1.0 -> 0.3333
                    target_level=3,
                    has_evidence=True,
                    evidence="SQL coursework",
                ),
            ]
        )
        db_session.commit()

        summary = dashboard_service.get_dashboard_summary(db_session, user_id=user.id)
        assert summary["total_skills_evaluated"] == 2
        assert summary["skills_matched_count"] == 1
        assert summary["skills_gap_count"] == 1
        # (2.0 * 1.0 + 1.0 * (1/3)) / 3.0 * 100 = 77.8
        assert summary["readiness_score"] == 77.8

    def test_learning_progress_calculates_overall_and_weekly_percentages(self, db_session):
        user = _create_user(db_session, email="progress-calc@example.com")
        role, skills = _create_role_with_skills(db_session, slug="progress-role")
        analysis = Analysis(
            user_id=user.id,
            career_role_id=role.id,
            consent_accepted=True,
            consent_purpose_version="v1",
            status="completed",
            readiness_score=50,
            completed_at=_utcnow(),
        )
        db_session.add(analysis)
        db_session.flush()

        today = _utcnow().date()
        plan = LearningPlan(
            user_id=user.id,
            analysis_id=analysis.id,
            title="30-day Backend Plan",
            status="active",
            start_date=today,
            end_date=today + timedelta(days=29),
        )
        db_session.add(plan)
        db_session.flush()

        db_session.add_all(
            [
                LearningPlanItem(
                    plan_id=plan.id,
                    skill_id=skills[0].id,
                    week_number=1,
                    task_description="Task W1-1",
                    is_completed=True,
                ),
                LearningPlanItem(
                    plan_id=plan.id,
                    skill_id=skills[0].id,
                    week_number=1,
                    task_description="Task W1-2",
                    is_completed=False,
                ),
                LearningPlanItem(
                    plan_id=plan.id,
                    skill_id=skills[1].id,
                    week_number=2,
                    task_description="Task W2-1",
                    is_completed=True,
                ),
            ]
        )
        db_session.commit()

        progress = dashboard_service.get_learning_progress(db_session, user_id=user.id)
        assert progress["has_active_plan"] is True
        assert progress["plan"]["total_tasks"] == 3
        assert progress["plan"]["completed_tasks"] == 2
        assert progress["plan"]["progress_percent"] == 66.7

        w1 = next(w for w in progress["weekly_breakdown"] if w["week_number"] == 1)
        w2 = next(w for w in progress["weekly_breakdown"] if w["week_number"] == 2)
        w3 = next(w for w in progress["weekly_breakdown"] if w["week_number"] == 3)
        assert w1["progress_percent"] == 50.0
        assert w2["progress_percent"] == 100.0
        assert w3["progress_percent"] == 0.0

    def test_validate_ai_score_rounding_and_invalid_bounds(self):
        valid = InterviewAnswerScoreAI(score=Decimal("85.555"), feedback="  Cấu trúc rõ ràng.  ")
        score, feedback = interview_service._validate_ai_score(valid)
        assert score == Decimal("85.56")
        assert feedback == "Cấu trúc rõ ràng."

        for invalid_score in (Decimal("-0.1"), Decimal("100.01"), Decimal("NaN"), Decimal("Infinity")):
            bad_obj = SimpleNamespace(score=invalid_score, feedback="Valid text")
            with pytest.raises(HTTPException) as exc_info:
                interview_service._validate_ai_score(bad_obj)
            assert exc_info.value.status_code == 502

        blank_feedback = SimpleNamespace(score=Decimal("70"), feedback="   ")
        with pytest.raises(HTTPException) as exc_info:
            interview_service._validate_ai_score(blank_feedback)
        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# 2. Authorization & Permissions (Tầng Service / Core Deps)
# ---------------------------------------------------------------------------


class TestAuthorizationServices:
    """Unit tests for RBAC, lock/inactive enforcement, tokens, and resource ownership."""

    def test_register_and_authenticate_active_vs_locked_user(self, db_session):
        user = auth_service.register_user(
            db_session,
            RegisterRequest(email="rbac-student@example.com", password="Password123!"),
        )
        assert user.role == "student"
        assert user.is_active is True

        # Duplicate email rejected
        with pytest.raises(HTTPException) as dup_exc:
            auth_service.register_user(
                db_session,
                RegisterRequest(email="rbac-student@example.com", password="Password123!"),
            )
        assert dup_exc.value.status_code == 400

        # Valid login returns JWT + refresh token
        logged_user, access_token, refresh_token = auth_service.authenticate_user(
            db_session,
            LoginRequest(email="rbac-student@example.com", password="Password123!"),
        )
        assert logged_user.id == user.id
        assert access_token and refresh_token

        # Lock user -> login blocked with 403
        user.is_active = False
        db_session.commit()
        with pytest.raises(HTTPException) as lock_exc:
            auth_service.authenticate_user(
                db_session,
                LoginRequest(email="rbac-student@example.com", password="Password123!"),
            )
        assert lock_exc.value.status_code == 403
        assert lock_exc.value.detail == "Account is inactive"

    def test_get_current_user_and_require_admin_guards(self, db_session):
        student = _create_user(db_session, email="guard-student@example.com", role="student")
        admin = _create_user(db_session, email="guard-admin@example.com", role="admin")
        locked = _create_user(db_session, email="guard-locked@example.com", role="admin", is_active=False)

        student_token = create_access_token({"sub": str(student.id)})
        admin_token = create_access_token({"sub": str(admin.id)})
        locked_token = create_access_token({"sub": str(locked.id)})
        bad_sub_token = create_access_token({"sub": "not-an-int"})

        assert get_current_user(student_token, db_session).id == student.id
        assert require_admin(get_current_user(admin_token, db_session)).id == admin.id

        with pytest.raises(HTTPException) as student_err:
            require_admin(student)
        assert student_err.value.status_code == 403

        with pytest.raises(HTTPException) as locked_err:
            get_current_user(locked_token, db_session)
        assert locked_err.value.status_code == 403

        with pytest.raises(HTTPException) as bad_sub_err:
            get_current_user(bad_sub_token, db_session)
        assert bad_sub_err.value.status_code == 401

    def test_refresh_token_rotation_and_reuse_revokes_family(self, db_session):
        _create_user(db_session, email="rotate@example.com", password="Password123!")
        _, _, rt1 = auth_service.authenticate_user(
            db_session,
            LoginRequest(email="rotate@example.com", password="Password123!"),
        )

        # Rotate once -> rt2 valid, rt1 revoked
        _, rt2 = auth_service.refresh_session(db_session, RefreshRequest(refresh_token=rt1))
        assert rt2 != rt1

        # Reusing rt1 triggers family-wide revocation
        with pytest.raises(HTTPException) as reuse_err:
            auth_service.refresh_session(db_session, RefreshRequest(refresh_token=rt1))
        assert reuse_err.value.status_code == 401

        # Even rt2 is now revoked
        with pytest.raises(HTTPException) as family_revoked_err:
            auth_service.refresh_session(db_session, RefreshRequest(refresh_token=rt2))
        assert family_revoked_err.value.status_code == 401

        tokens = db_session.scalars(select(RefreshToken)).all()
        assert len(tokens) == 2
        assert all(t.revoked_at is not None for t in tokens)

    def test_bootstrap_admin_refuses_promoting_student(self, db_session):
        _create_user(db_session, email="student-no-promo@example.com", role="student")
        with pytest.raises(ValueError, match="refusing to elevate"):
            catalog_service.bootstrap_admin(
                db_session,
                email="student-no-promo@example.com",
                password="AdminPassword123!",
            )

        admin, created = catalog_service.bootstrap_admin(
            db_session,
            email="new-admin@example.com",
            password="AdminPassword123!",
        )
        assert created is True
        assert admin.role == "admin"

    def test_service_ownership_checks_prevent_cross_user_access(self, db_session):
        owner = _create_user(db_session, email="owner@example.com")
        intruder = _create_user(db_session, email="intruder@example.com")
        role, _ = _create_role_with_skills(db_session, slug="ownership-role")

        cv = CV(
            user_id=owner.id,
            file_name="resume.pdf",
            file_path="uploads/resume.pdf",
            mime_type="application/pdf",
            file_size=1024,
            extracted_text="Python developer",
            is_active=True,
        )
        analysis = Analysis(
            user_id=owner.id,
            career_role_id=role.id,
            consent_accepted=True,
            consent_purpose_version="v1",
            status="completed",
            readiness_score=80,
            completed_at=_utcnow(),
        )
        db_session.add_all([cv, analysis])
        db_session.flush()

        today = _utcnow().date()
        plan = LearningPlan(
            user_id=owner.id,
            analysis_id=analysis.id,
            title="Owner Plan",
            status="active",
            start_date=today,
            end_date=today + timedelta(days=29),
        )
        session = InterviewSession(user_id=owner.id, career_role_id=role.id, status="ready")
        db_session.add_all([plan, session])
        db_session.commit()

        # CV ownership
        with pytest.raises(HTTPException) as cv_err:
            analysis_service.get_owned_active_cv(db_session, user_id=intruder.id, cv_id=cv.id)
        assert cv_err.value.status_code == 403

        # Learning plan ownership
        with pytest.raises(HTTPException) as plan_err:
            learning_plan_service.get_plan_detail(db_session, user_id=intruder.id, plan_id=plan.id)
        assert plan_err.value.status_code == 403

        # Interview session ownership
        with pytest.raises(HTTPException) as session_err:
            interview_service._get_owned_session(db_session, session_id=session.id, user_id=intruder.id)
        assert session_err.value.status_code == 403


# ---------------------------------------------------------------------------
# 3. Interview Service Logic (Tầng Service)
# ---------------------------------------------------------------------------


class TestInterviewServiceUnit:
    """Unit tests for interview question prep, validation, scoring, stale cleanup, and completion."""

    def test_build_skill_contexts_orders_by_weight_and_filters_inactive(self, db_session):
        role, skills = _create_role_with_skills(db_session, slug="skill-order")
        contexts = interview_service._build_skill_contexts(role)
        # Only active skills (Python weight=2.0, SQL weight=1.0), sorted descending by weight
        assert [c.name for c in contexts] == [skills[0].name, skills[1].name]

    def test_validate_generated_questions_rejects_normalized_duplicates(self):
        dup_resp = InterviewGenerationAIResponse(
            questions=[
                InterviewQuestionAI(
                    question_text="  Explain   GIL in Python? ",
                    competency="Python",
                    evaluation_criteria=["Threading", "Multiprocessing"],
                ),
                InterviewQuestionAI(
                    question_text="explain gil in python?",
                    competency="Python",
                    evaluation_criteria=["Concurrency"],
                ),
                InterviewQuestionAI(
                    question_text="How do database indexes work?",
                    competency="SQL",
                    evaluation_criteria=["B-Tree"],
                ),
            ]
        )
        with pytest.raises(HTTPException) as exc_info:
            interview_service._validate_generated_questions(dup_resp)
        assert exc_info.value.status_code == 502
        assert exc_info.value.detail["data"]["code"] == interview_service.AI_DUPLICATE_QUESTIONS

    def test_validate_answer_text_rejects_blank_and_oversized(self):
        assert interview_service._validate_answer_text("  Valid answer  ") == "Valid answer"

        with pytest.raises(HTTPException) as empty_exc:
            interview_service._validate_answer_text("   \n\t  ")
        assert empty_exc.value.status_code == 422

        too_long = "a" * (interview_service.ANSWER_MAX_LENGTH + 1)
        with pytest.raises(HTTPException) as long_exc:
            interview_service._validate_answer_text(too_long)
        assert long_exc.value.status_code == 422

    def test_abandon_stale_interview_sessions_marks_only_old_open_sessions(self, db_session):
        user = _create_user(db_session, email="stale-interview@example.com")
        role, _ = _create_role_with_skills(db_session, slug="stale-role")
        now = _utcnow()

        old_ready = InterviewSession(
            user_id=user.id,
            career_role_id=role.id,
            status="ready",
            updated_at=now - timedelta(hours=25),
        )
        old_completed = InterviewSession(
            user_id=user.id,
            career_role_id=role.id,
            status="completed",
            updated_at=now - timedelta(hours=48),
        )
        recent_in_progress = InterviewSession(
            user_id=user.id,
            career_role_id=role.id,
            status="in_progress",
            updated_at=now - timedelta(hours=2),
        )
        db_session.add_all([old_ready, old_completed, recent_in_progress])
        db_session.commit()

        affected = interview_service.abandon_stale_interview_sessions(
            db_session,
            user_id=user.id,
            now=now,
        )
        assert affected == 1

        db_session.refresh(old_ready)
        db_session.refresh(old_completed)
        db_session.refresh(recent_in_progress)
        assert old_ready.status == "abandoned"
        assert old_completed.status == "completed"
        assert recent_in_progress.status == "in_progress"

    def test_create_answer_and_complete_interview_session_averages_scores(self, db_session):
        user = _create_user(db_session, email="interview-flow@example.com")
        role, _ = _create_role_with_skills(db_session, slug="interview-flow-role")

        class FakeInterviewAI:
            async def generate_structured(self, *, prompt, response_schema, system_instruction):
                if response_schema is InterviewGenerationAIResponse:
                    return InterviewGenerationAIResponse(
                        questions=[
                            InterviewQuestionAI(
                                question_text=f"Question {i}: Describe design pattern {i}.",
                                competency="System Design",
                                evaluation_criteria=["Clarity", "Trade-offs"],
                            )
                            for i in range(1, 4)
                        ]
                    )
                if response_schema is InterviewAnswerScoreAI:
                    # Deterministic scores per question prompt content
                    if "Question 1" in prompt:
                        return InterviewAnswerScoreAI(score=Decimal("80.00"), feedback="Tốt về nền tảng.")
                    if "Question 2" in prompt:
                        return InterviewAnswerScoreAI(score=Decimal("85.50"), feedback="Phân tích khá sâu.")
                    return InterviewAnswerScoreAI(score=Decimal("90.25"), feedback="Ví dụ thực tế rất hay.")
                raise AssertionError(f"Unexpected schema: {response_schema}")

        fake_ai = FakeInterviewAI()
        created = asyncio.run(
            interview_service.create_interview_session(
                db_session,
                user_id=user.id,
                career_role_id=role.id,
                consent=AIConsent(accepted=True, purpose_version="v1"),
                ai_service=fake_ai,
            )
        )
        assert created.status == "ready"
        assert len(created.questions) == 3
        session_id = created.id

        # Cannot complete before answering all questions
        with pytest.raises(HTTPException) as incomplete_exc:
            interview_service.complete_interview_session(
                db_session,
                user_id=user.id,
                session_id=session_id,
            )
        assert incomplete_exc.value.status_code == 409

        # Submit answers for all 3 questions
        for idx, q in enumerate(created.questions, start=1):
            ans_res = asyncio.run(
                interview_service.submit_interview_answer(
                    db_session,
                    user_id=user.id,
                    session_id=session_id,
                    question_id=q.id,
                    answer_text=f"Detailed answer for question {idx}",
                    ai_service=fake_ai,
                )
            )
            assert ans_res["session_status"] == "in_progress"
            assert ans_res["answered_count"] == idx

        # Duplicate answer rejected
        with pytest.raises(HTTPException) as dup_ans_exc:
            asyncio.run(
                interview_service.submit_interview_answer(
                    db_session,
                    user_id=user.id,
                    session_id=session_id,
                    question_id=created.questions[0].id,
                    answer_text="Retry answer",
                    ai_service=fake_ai,
                )
            )
        assert dup_ans_exc.value.status_code == 409

        # Complete session -> average of (80.00, 85.50, 90.25) = 85.25
        completed = interview_service.complete_interview_session(
            db_session,
            user_id=user.id,
            session_id=session_id,
        )
        assert completed["status"] == "completed"
        assert completed["total_score"] == Decimal("85.25")
        assert completed["question_count"] == 3
        assert completed["answered_count"] == 3
