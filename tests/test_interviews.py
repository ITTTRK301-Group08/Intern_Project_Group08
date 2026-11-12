"""Unit và integration test cho nghiệp vụ tạo phiên phỏng vấn thử.

Toàn bộ test dùng SQLite in-memory và provider AI giả; không gọi Gemini thật.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.career import CareerRole, Skill
from app.models.interview import InterviewAnswer, InterviewQuestion, InterviewSession
from app.models.profile_data import CareerRoleSkill
from app.schemas.interview.ai_response import InterviewGenerationAIResponse
from app.services import interview_service
from app.services.ai import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AIService,
    AITimeoutError,
    BaseAIProvider,
)

CONSENT_REQUIRED = "AI_CONSENT_REQUIRED"
CONSENT_VERSION_UNSUPPORTED = "AI_CONSENT_VERSION_UNSUPPORTED"


class FakeProvider(BaseAIProvider):
    """Provider giả trả về lần lượt kết quả hoặc exception đã định trước."""

    name = "fake"

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0
        self.last_prompt = None
        self.last_response_schema = None
        self.last_system_instruction = None

    async def generate(self, *, prompt, response_schema=None, system_instruction=None):
        self.calls += 1
        self.last_prompt = prompt
        self.last_response_schema = response_schema
        self.last_system_instruction = system_instruction
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def register_and_login(
    client,
    email: str = "interview@example.com",
    password: str = "StrongPass123",
) -> tuple[dict[str, str], int]:
    """Đăng ký, đăng nhập và trả về header JWT cùng user_id."""
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, register.json()["data"]["user"]["id"]


def seed_career_role(
    db_session,
    *,
    name: str = "Backend Developer",
    is_active: bool = True,
    with_skills: bool = True,
) -> int:
    """Tạo vị trí nghề nghiệp và kỹ năng liên quan trong database test."""
    role = CareerRole(
        name=name,
        slug=name.casefold().replace(" ", "-"),
        level="Intern",
        description=f"Mô tả cho {name}",
        is_active=is_active,
    )
    db_session.add(role)
    db_session.flush()
    role_id = role.id

    if with_skills:
        skill = Skill(name=f"{name} Python")
        db_session.add(skill)
        db_session.flush()
        db_session.add(
            CareerRoleSkill(
                career_role_id=role_id,
                skill_id=skill.id,
                required_level=3,
                is_required=True,
                weight=1.0,
            )
        )

    db_session.commit()
    return role_id


def interview_payload(
    career_role_id: int,
    *,
    accepted: bool = True,
    purpose_version: str = "v1",
) -> dict:
    """Tạo request hợp lệ theo schema InterviewCreateRequest."""
    return {
        "career_role_id": career_role_id,
        "ai_consent": {
            "accepted": accepted,
            "purpose_version": purpose_version,
        },
    }


def questions_payload(count: int = 3) -> dict:
    """Tạo dữ liệu JSON hợp lệ cho bộ câu hỏi phỏng vấn."""
    return {
        "questions": [
            {
                "question_text": f"Câu hỏi phỏng vấn số {index}",
                "competency": f"Năng lực số {index}",
                "evaluation_criteria": [
                    f"Tiêu chí {index}.1",
                    f"Tiêu chí {index}.2",
                ],
            }
            for index in range(1, count + 1)
        ]
    }


def questions_json(count: int = 3) -> str:
    """Chuyển dữ liệu câu hỏi thành JSON mà AI Service có thể parse."""
    return json.dumps(questions_payload(count), ensure_ascii=False)


def install_fake_ai(monkeypatch, *outcomes) -> FakeProvider:
    """Cài AI Service thật với provider giả để không gọi Gemini."""
    provider = FakeProvider(outcomes)
    service = AIService(provider, max_retries=0)
    monkeypatch.setattr(interview_service, "get_ai_service", lambda: service)
    return provider


def assert_no_interview_saved(db_session) -> None:
    """Bảo đảm không có session hoặc câu hỏi nào bị lưu một phần."""
    assert db_session.query(InterviewSession).count() == 0
    assert db_session.query(InterviewQuestion).count() == 0


# ---------------------------------------------------------------------------
# Xác thực
# ---------------------------------------------------------------------------


def test_requires_jwt(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    role_id = seed_career_role(db_session)

    response = client.post(
        "/api/v1/interviews",
        json=interview_payload(role_id),
    )

    assert response.status_code == 401
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_invalid_token_rejected(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    role_id = seed_career_role(db_session)

    response = client.post(
        "/api/v1/interviews",
        headers={"Authorization": "Bearer invalid-token"},
        json=interview_payload(role_id),
    )

    assert response.status_code == 401
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_user_id_comes_from_jwt_not_request_body(client, db_session, monkeypatch):
    headers_owner, owner_id = register_and_login(client, "owner@example.com")
    headers_other, other_id = register_and_login(client, "other@example.com")
    assert owner_id != other_id

    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    # Client không được phép gửi user_id trong body.
    invalid_payload = interview_payload(role_id)
    invalid_payload["user_id"] = owner_id
    rejected = client.post(
        "/api/v1/interviews",
        headers=headers_other,
        json=invalid_payload,
    )
    assert rejected.status_code == 422
    assert_no_interview_saved(db_session)

    # Khi không gửi user_id, phiên phải thuộc đúng người dùng trong JWT.
    created = client.post(
        "/api/v1/interviews",
        headers=headers_other,
        json=interview_payload(role_id),
    )
    assert created.status_code == 201

    session = db_session.query(InterviewSession).one()
    assert session.user_id == other_id
    assert session.user_id != owner_id
    assert headers_owner["Authorization"] != headers_other["Authorization"]


# ---------------------------------------------------------------------------
# Vị trí nghề nghiệp và consent
# ---------------------------------------------------------------------------


def test_career_role_not_found(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    headers, _ = register_and_login(client)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(999999),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_CAREER_ROLE_NOT_FOUND"
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_inactive_career_role_rejected(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session, is_active=False)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_CAREER_ROLE_INACTIVE"
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_career_role_without_skills_rejected(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session, with_skills=False)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_ROLE_SKILLS_REQUIRED"
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_missing_ai_consent_rejected(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"career_role_id": role_id},
    )

    assert response.status_code == 422
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_ai_consent_not_accepted_rejected(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id, accepted=False),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["data"]["code"] == CONSENT_REQUIRED
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


def test_ai_consent_version_unsupported_rejected(client, db_session, monkeypatch):
    provider = install_fake_ai(monkeypatch, questions_json())
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id, purpose_version="v999"),
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]["data"]["code"] == CONSENT_VERSION_UNSUPPORTED
    )
    assert provider.calls == 0
    assert_no_interview_saved(db_session)


# ---------------------------------------------------------------------------
# Sinh câu hỏi thành công
# ---------------------------------------------------------------------------


def test_create_interview_success(client, db_session, monkeypatch):
    headers, user_id = register_and_login(client)
    role_id = seed_career_role(db_session)
    provider = install_fake_ai(monkeypatch, questions_json())

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Tạo phiên phỏng vấn thành công."

    data = body["data"]
    assert data["id"] > 0
    assert data["status"] == "in_progress"
    assert data["career_role"] == {
        "id": role_id,
        "name": "Backend Developer",
        "level": "Intern",
    }
    assert len(data["questions"]) == 3

    for index, question in enumerate(data["questions"], start=1):
        assert question["question_order"] == index
        assert question["question_text"] == f"Câu hỏi phỏng vấn số {index}"
        assert question["competency"] == f"Năng lực số {index}"
        assert question["evaluation_criteria"] == [
            f"Tiêu chí {index}.1",
            f"Tiêu chí {index}.2",
        ]

    # Kiểm tra dữ liệu thật trong database.
    session = db_session.query(InterviewSession).one()
    assert session.id == data["id"]
    assert session.user_id == user_id
    assert session.career_role_id == role_id
    assert session.status == "in_progress"

    questions = (
        db_session.query(InterviewQuestion)
        .order_by(InterviewQuestion.question_order)
        .all()
    )
    assert len(questions) == 3
    assert [question.question_order for question in questions] == [1, 2, 3]
    assert [question.session_id for question in questions] == [session.id] * 3
    assert [question.question_text for question in questions] == [
        f"Câu hỏi phỏng vấn số {index}" for index in range(1, 4)
    ]

    # AI Service Task 1 được gọi đúng một lần với schema và system instruction.
    assert provider.calls == 1
    assert provider.last_response_schema is InterviewGenerationAIResponse
    assert provider.last_system_instruction is not None


def test_prompt_contains_only_public_catalog_data(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "privacy@example.com")
    role_id = seed_career_role(db_session)
    provider = install_fake_ai(monkeypatch, questions_json())

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )
    assert response.status_code == 201

    prompt = provider.last_prompt
    assert prompt is not None
    assert "Backend Developer" in prompt
    assert "Intern" in prompt
    assert "Backend Developer Python" in prompt
    assert "privacy@example.com" not in prompt
    assert "StrongPass123" not in prompt
    assert headers["Authorization"] not in prompt
    assert "user_id" not in prompt


# ---------------------------------------------------------------------------
# AI trả về dữ liệu không hợp lệ
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [2, 4])
def test_ai_wrong_question_count_rejected(
    client, db_session, monkeypatch, count
):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json(count))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_empty_question_list_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json(0))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_empty_question_text_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    payload = questions_payload()
    payload["questions"][0]["question_text"] = "   "
    install_fake_ai(monkeypatch, json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_missing_competency_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    payload = questions_payload()
    del payload["questions"][0]["competency"]
    install_fake_ai(monkeypatch, json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_missing_evaluation_criteria_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    payload = questions_payload()
    del payload["questions"][0]["evaluation_criteria"]
    install_fake_ai(monkeypatch, json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_empty_evaluation_criteria_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    payload = questions_payload()
    payload["questions"][0]["evaluation_criteria"] = []
    install_fake_ai(monkeypatch, json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_duplicate_questions_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    payload = questions_payload()
    payload["questions"][1]["question_text"] = payload["questions"][0][
        "question_text"
    ]
    install_fake_ai(monkeypatch, json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_DUPLICATE_QUESTIONS"
    assert_no_interview_saved(db_session)


def test_ai_duplicate_questions_with_different_spacing_rejected(
    client, db_session, monkeypatch
):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    payload = questions_payload()
    payload["questions"][1]["question_text"] = (
        "  " + payload["questions"][0]["question_text"].upper() + "  "
    )
    install_fake_ai(monkeypatch, json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_DUPLICATE_QUESTIONS"
    assert_no_interview_saved(db_session)


def test_ai_invalid_json_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, "không phải json")

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


def test_ai_empty_response_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, "")

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_AI_INVALID_RESPONSE"
    assert_no_interview_saved(db_session)


# ---------------------------------------------------------------------------
# Lỗi AI và lỗi database
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (AITimeoutError("timeout"), 504, "INTERVIEW_AI_TIMEOUT"),
        (AIRateLimitError("rate limit"), 429, "INTERVIEW_AI_RATE_LIMITED"),
        (
            AIAuthenticationError("bad key"),
            502,
            "INTERVIEW_AI_AUTHENTICATION_FAILED",
        ),
        (AIInvalidRequestError("bad request"), 502, "INTERVIEW_AI_INVALID_REQUEST"),
        (AIProviderError("provider down"), 502, "INTERVIEW_AI_UNAVAILABLE"),
        (AIConfigurationError("missing key"), 503, "INTERVIEW_AI_UNAVAILABLE"),
    ],
)
def test_ai_errors_are_mapped_safely(
    client,
    db_session,
    monkeypatch,
    error,
    expected_status,
    expected_code,
):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, error)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == expected_status
    body = response.json()
    assert body["detail"]["data"]["code"] == expected_code
    assert "bad key" not in str(body)
    assert "missing key" not in str(body)
    assert "provider down" not in str(body)
    assert_no_interview_saved(db_session)


def test_database_commit_failure_rolls_back(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    def raise_commit_error():
        raise SQLAlchemyError("commit thất bại")

    monkeypatch.setattr(db_session, "commit", raise_commit_error)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 500
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_DATABASE_ERROR"

    db_session.rollback()
    assert_no_interview_saved(db_session)


def test_database_flush_failure_rolls_back(client, db_session, monkeypatch):
    headers, _ = register_and_login(client)
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    def raise_flush_error():
        raise SQLAlchemyError("flush thất bại")

    monkeypatch.setattr(db_session, "flush", raise_flush_error)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )

    assert response.status_code == 500
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_DATABASE_ERROR"

    db_session.rollback()
    assert_no_interview_saved(db_session)


# ---------------------------------------------------------------------------
# Trả lời, chấm điểm và hoàn thành phiên (M6)
# ---------------------------------------------------------------------------


def grading_json(score: float = 80.0, feedback: str = "Phản hồi cải thiện") -> str:
    """Tạo JSON chấm điểm hợp lệ cho AI Service."""
    return json.dumps({"score": score, "feedback": feedback}, ensure_ascii=False)


def create_session(client, headers, role_id: int) -> dict:
    """Tạo phiên phỏng vấn thành công và trả về dữ liệu response."""
    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json=interview_payload(role_id),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_submit_answer_grades_and_persists(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "answer@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json(), grading_json(82.5, "Cần nêu ví dụ."))

    session_data = create_session(client, headers, role_id)
    question_id = session_data["questions"][0]["id"]

    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/answers",
        headers=headers,
        json={"question_id": question_id, "answer_text": "Câu trả lời của tôi."},
    )

    assert response.status_code == 201
    answer = response.json()["data"]
    assert answer["question_id"] == question_id
    assert answer["answer_text"] == "Câu trả lời của tôi."
    assert answer["score"] == pytest.approx(82.5)
    assert answer["feedback"] == "Cần nêu ví dụ."

    stored = db_session.query(InterviewAnswer).filter_by(question_id=question_id).one()
    assert float(stored.score) == pytest.approx(82.5)
    assert stored.answer_text == "Câu trả lời của tôi."


def test_submit_duplicate_answer_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "duplicate@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json(), grading_json())

    session_data = create_session(client, headers, role_id)
    question_id = session_data["questions"][0]["id"]
    payload = {"question_id": question_id, "answer_text": "Câu trả lời."}

    first = client.post(
        f"/api/v1/interviews/{session_data['id']}/answers",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/interviews/{session_data['id']}/answers",
        headers=headers,
        json=payload,
    )
    assert second.status_code == 409
    assert second.json()["detail"]["data"]["code"] == "INTERVIEW_ANSWER_ALREADY_EXISTS"
    assert db_session.query(InterviewAnswer).count() == 1


def test_submit_answer_for_unknown_question_rejected(
    client, db_session, monkeypatch
):
    headers, _ = register_and_login(client, "unknownq@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    session_data = create_session(client, headers, role_id)
    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/answers",
        headers=headers,
        json={"question_id": 999999, "answer_text": "Trả lời."},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_QUESTION_NOT_FOUND"


def test_submit_answer_requires_ownership(client, db_session, monkeypatch):
    owner_headers, _ = register_and_login(client, "owner_answer@example.com")
    other_headers, _ = register_and_login(client, "other_answer@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    session_data = create_session(client, owner_headers, role_id)
    question_id = session_data["questions"][0]["id"]

    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/answers",
        headers=other_headers,
        json={"question_id": question_id, "answer_text": "Trả lời."},
    )

    assert response.status_code == 404
    assert db_session.query(InterviewAnswer).count() == 0


def test_complete_requires_all_answers(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "incomplete@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    session_data = create_session(client, headers, role_id)
    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/complete",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_INCOMPLETE"


def test_complete_computes_average_and_persists(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "complete@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(
        monkeypatch,
        questions_json(),
        grading_json(60.0, "Phản hồi 1"),
        grading_json(70.0, "Phản hồi 2"),
        grading_json(80.0, "Phản hồi 3"),
    )

    session_data = create_session(client, headers, role_id)
    for question in session_data["questions"]:
        answered = client.post(
            f"/api/v1/interviews/{session_data['id']}/answers",
            headers=headers,
            json={
                "question_id": question["id"],
                "answer_text": f"Trả lời cho câu {question['question_order']}.",
            },
        )
        assert answered.status_code == 201

    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/complete",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["total_score"] == pytest.approx(70.0)
    assert data["completed_at"] is not None
    assert len(data["questions"]) == 3
    assert all(question["answer"] is not None for question in data["questions"])

    db_session.expire_all()
    stored = db_session.get(InterviewSession, session_data["id"])
    assert stored.status == "completed"
    assert float(stored.total_score) == pytest.approx(70.0)
    assert stored.completed_at is not None


def test_complete_is_idempotent(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "idempotent@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(
        monkeypatch,
        questions_json(),
        grading_json(90.0, "Tốt"),
        grading_json(90.0, "Tốt"),
        grading_json(90.0, "Tốt"),
    )

    session_data = create_session(client, headers, role_id)
    for question in session_data["questions"]:
        client.post(
            f"/api/v1/interviews/{session_data['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "answer_text": "Trả lời."},
        )

    first = client.post(
        f"/api/v1/interviews/{session_data['id']}/complete", headers=headers
    )
    second = client.post(
        f"/api/v1/interviews/{session_data['id']}/complete", headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["status"] == "completed"
    assert second.json()["data"]["total_score"] == pytest.approx(
        first.json()["data"]["total_score"]
    )


def test_answer_after_completion_rejected(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "aftercomplete@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(
        monkeypatch,
        questions_json(),
        grading_json(70.0, "A"),
        grading_json(70.0, "B"),
        grading_json(70.0, "C"),
    )

    session_data = create_session(client, headers, role_id)
    for question in session_data["questions"]:
        client.post(
            f"/api/v1/interviews/{session_data['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "answer_text": "Trả lời."},
        )
    client.post(f"/api/v1/interviews/{session_data['id']}/complete", headers=headers)

    # Câu đã có trả lời trong phiên completed phải bị chặn.
    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/answers",
        headers=headers,
        json={
            "question_id": session_data["questions"][0]["id"],
            "answer_text": "Trả lời lại.",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_NOT_IN_PROGRESS"


def test_history_detail_and_questions_endpoints(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "history@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    session_data = create_session(client, headers, role_id)

    history = client.get("/api/v1/interviews", headers=headers)
    assert history.status_code == 200
    history_data = history.json()["data"]
    assert history_data["total"] == 1
    assert history_data["interviews"][0]["id"] == session_data["id"]

    detail = client.get(f"/api/v1/interviews/{session_data['id']}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["data"]["questions"]) == 3

    questions = client.get(
        f"/api/v1/interviews/{session_data['id']}/questions", headers=headers
    )
    assert questions.status_code == 200
    questions_data = questions.json()["data"]
    assert questions_data["session_id"] == session_data["id"]
    assert [item["question_order"] for item in questions_data["questions"]] == [1, 2, 3]


def test_history_hides_other_users_sessions(client, db_session, monkeypatch):
    owner_headers, _ = register_and_login(client, "owner_hist@example.com")
    other_headers, _ = register_and_login(client, "other_hist@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    session_data = create_session(client, owner_headers, role_id)

    assert (
        client.get(
            f"/api/v1/interviews/{session_data['id']}", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/interviews/{session_data['id']}/questions",
            headers=other_headers,
        ).status_code
        == 404
    )
    other_history = client.get("/api/v1/interviews", headers=other_headers)
    assert other_history.json()["data"]["total"] == 0


def test_new_session_same_role_abandons_previous(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "abandon@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json(), questions_json())

    first = create_session(client, headers, role_id)
    second = create_session(client, headers, role_id)
    assert first["id"] != second["id"]

    db_session.expire_all()
    first_session = db_session.get(InterviewSession, first["id"])
    second_session = db_session.get(InterviewSession, second["id"])
    assert first_session.status == "abandoned"
    assert second_session.status == "in_progress"

    response = client.post(
        f"/api/v1/interviews/{first['id']}/answers",
        headers=headers,
        json={
            "question_id": first["questions"][0]["id"],
            "answer_text": "Trả lời muộn.",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_ABANDONED"


def test_stale_session_abandoned_after_24_hours(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "stale@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(monkeypatch, questions_json())

    session_data = create_session(client, headers, role_id)

    db_session.expire_all()
    stored = db_session.get(InterviewSession, session_data["id"])
    stored.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        hours=25
    )
    db_session.commit()

    history = client.get("/api/v1/interviews", headers=headers)
    assert history.status_code == 200

    db_session.expire_all()
    stored = db_session.get(InterviewSession, session_data["id"])
    assert stored.status == "abandoned"


def test_complete_rolls_back_on_database_error(client, db_session, monkeypatch):
    headers, _ = register_and_login(client, "completerollback@example.com")
    role_id = seed_career_role(db_session)
    install_fake_ai(
        monkeypatch,
        questions_json(),
        grading_json(70.0, "A"),
        grading_json(70.0, "B"),
        grading_json(70.0, "C"),
    )

    session_data = create_session(client, headers, role_id)
    for question in session_data["questions"]:
        client.post(
            f"/api/v1/interviews/{session_data['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "answer_text": "Trả lời."},
        )

    original_commit = db_session.commit

    def raise_commit_error():
        raise SQLAlchemyError("commit thất bại")

    monkeypatch.setattr(db_session, "commit", raise_commit_error)
    response = client.post(
        f"/api/v1/interviews/{session_data['id']}/complete",
        headers=headers,
    )
    monkeypatch.setattr(db_session, "commit", original_commit)

    assert response.status_code == 500
    assert response.json()["detail"]["data"]["code"] == "INTERVIEW_DATABASE_ERROR"

    db_session.rollback()
    db_session.expire_all()
    stored = db_session.get(InterviewSession, session_data["id"])
    assert stored.status == "in_progress"
    assert stored.total_score is None
