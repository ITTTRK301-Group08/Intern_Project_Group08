"""Kiểm thử tính tương thích JSON Schema giữa Pydantic và Gemini.

Bộ test này bảo vệ hai yêu cầu:
- AI-01: `GeminiProvider` chỉ gửi các khóa schema mà Gemini hỗ trợ.
- AI-02: Pydantic vẫn xác thực đầy đủ sau khi schema được làm sạch.

Không có lời gọi mạng hoặc Gemini API thật nào trong file này.
"""

import asyncio
import copy
import json
from enum import Enum
from types import SimpleNamespace
from typing import Annotated

import pytest
from google.genai import types
from google.genai import _transformers as genai_transformers
from google.genai.models import _GenerateContentConfig_to_mldev
from pydantic import BaseModel, Field, ValidationError

from app.schemas.ai import AIStructuredResponse
from app.schemas.interview.ai_response import (
    InterviewAnswerScoreAI,
    InterviewGenerationAIResponse,
)
from app.services.ai import gemini_provider as gemini_provider_module
from app.services.ai.ai_service import AIService
from app.services.ai.base import BaseAIProvider
from app.services.ai.exceptions import AIResponseValidationError
from app.services.ai.gemini_provider import (
    GeminiProvider,
    _to_gemini_compatible_schema,
)

API_KEY = "fake-gemini-key-for-tests"
MODEL = "gemini-test-model"

# Các khóa không được xuất hiện trong payload gửi Gemini.
_FORBIDDEN_SCHEMA_KEYS = frozenset(
    {
        "additionalProperties",
        "additional_properties",
        "minLength",
        "min_length",
        "maxLength",
        "max_length",
        "minItems",
        "min_items",
        "maxItems",
        "max_items",
        "minimum",
        "maximum",
        "minProperties",
        "min_properties",
        "maxProperties",
        "max_properties",
    }
)


# ---------------------------------------------------------------------------
# Schema mẫu phức tạp dùng riêng cho unit test sanitizer
# ---------------------------------------------------------------------------


class _Priority(str, Enum):
    LOW = "low"
    HIGH = "high"


class _NestedDetails(AIStructuredResponse):
    summary: Annotated[
        str,
        Field(min_length=5, max_length=100, description="Tóm tắt nội dung."),
    ]
    score: Annotated[int, Field(ge=0, le=10)]
    tags: Annotated[list[str], Field(min_length=1, max_length=5)]
    priority: _Priority


class _ComplexSchema(AIStructuredResponse):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    details: _NestedDetails
    items: Annotated[list[_NestedDetails], Field(min_length=1, max_length=3)]
    note: str | None = None


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------


def _walk_schema(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_schema(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_schema(item)


def _collect_keys(node):
    keys = set()
    for mapping in _walk_schema(node):
        keys.update(mapping)
    return keys


def _assert_no_forbidden_keys(schema):
    present = _collect_keys(schema) & _FORBIDDEN_SCHEMA_KEYS
    assert not present, f"Còn khóa không tương thích Gemini: {sorted(present)}"


def _dump_sdk_schema(schema):
    return schema.model_dump(by_alias=True, exclude_none=True)


class _FakeModels:
    def __init__(self, outcome):
        self._outcome = outcome
        self.calls = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return self._outcome


class _FakeAio:
    def __init__(self, models):
        self.models = models

    async def aclose(self):
        return None


class _FakeGenerateResponse:
    def __init__(self, text):
        self.text = text


def _install_fake_client(monkeypatch, text):
    captured = {}

    class _FakeClient:
        def __init__(self, *, api_key, http_options):
            self.models = _FakeModels(_FakeGenerateResponse(text))
            self.aio = _FakeAio(self.models)
            captured["models"] = self.models

    monkeypatch.setattr(gemini_provider_module.genai, "Client", _FakeClient)
    return captured


def _capture_provider_schema(monkeypatch, response_schema):
    captured = _install_fake_client(monkeypatch, "{}")
    provider = GeminiProvider(api_key=API_KEY, model=MODEL)

    asyncio.run(provider.generate(prompt="Trả JSON", response_schema=response_schema))

    return captured["models"].calls[0]["config"].response_schema


class _FakeProvider(BaseAIProvider):
    name = "fake"

    def __init__(self, outcome):
        self._outcome = outcome
        self.calls = 0

    async def generate(self, *, prompt, response_schema=None, system_instruction=None):
        self.calls += 1
        return self._outcome


def _generate(schema, raw_json):
    service = AIService(_FakeProvider(raw_json), max_retries=0)
    return asyncio.run(
        service.generate_structured(prompt="Trả JSON", response_schema=schema)
    )


# ---------------------------------------------------------------------------
# Nhóm 1: Schema sanitizer
# ---------------------------------------------------------------------------


def test_sanitizer_removes_additional_properties_at_root():
    sanitized = _to_gemini_compatible_schema(_ComplexSchema)

    assert "additionalProperties" not in sanitized
    assert "additional_properties" not in sanitized
    assert sanitized["type"] == "object"


def test_sanitizer_removes_additional_properties_in_nested_objects():
    sanitized = _to_gemini_compatible_schema(_ComplexSchema)

    nested = sanitized["$defs"]["_NestedDetails"]
    assert "additionalProperties" not in nested
    assert "additional_properties" not in nested


def test_sanitizer_removes_snake_case_keys_and_keeps_supported_keywords():
    raw_schema = {
        "type": "object",
        "additionalProperties": False,
        "additional_properties": {"type": "string"},
        "minProperties": 1,
        "maxProperties": 5,
        "properties": {
            "name": {
                "type": "string",
                "format": "date-time",
                "nullable": True,
                "description": "Tên.",
                "additional_properties": False,
            },
            "choice": {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
            },
        },
        "required": ["name"],
    }

    sanitized = _to_gemini_compatible_schema(raw_schema)

    _assert_no_forbidden_keys(sanitized)
    assert sanitized["required"] == ["name"]
    assert sanitized["properties"]["name"] == {
        "type": "string",
        "format": "date-time",
        "nullable": True,
        "description": "Tên.",
    }
    assert sanitized["properties"]["choice"]["anyOf"] == [
        {"type": "string"},
        {"type": "integer"},
    ]


def test_sanitizer_removes_unsupported_constraints_at_root_and_nested():
    sanitized = _to_gemini_compatible_schema(_ComplexSchema)

    _assert_no_forbidden_keys(sanitized)
    assert "minLength" not in sanitized["properties"]["title"]
    assert "maxLength" not in sanitized["properties"]["title"]

    nested = sanitized["$defs"]["_NestedDetails"]
    assert "minLength" not in nested["properties"]["summary"]
    assert "maxLength" not in nested["properties"]["summary"]
    assert "minimum" not in nested["properties"]["score"]
    assert "maximum" not in nested["properties"]["score"]
    assert "minItems" not in nested["properties"]["tags"]
    assert "maxItems" not in nested["properties"]["tags"]


def test_sanitizer_processes_array_items():
    sanitized = _to_gemini_compatible_schema(_ComplexSchema)

    items_schema = sanitized["properties"]["items"]
    assert items_schema["type"] == "array"
    assert items_schema["items"] == {"$ref": "#/$defs/_NestedDetails"}
    assert "minItems" not in items_schema
    assert "maxItems" not in items_schema

    tag_items = sanitized["$defs"]["_NestedDetails"]["properties"]["tags"]["items"]
    assert tag_items == {"type": "string"}


def test_sanitizer_preserves_properties_required_enum_and_description():
    sanitized = _to_gemini_compatible_schema(_ComplexSchema)

    assert {"title", "details", "items", "note"} == set(
        sanitized["properties"].keys()
    )
    assert sanitized["required"] == ["title", "details", "items"]

    nested = sanitized["$defs"]["_NestedDetails"]
    assert nested["required"] == ["summary", "score", "tags", "priority"]
    assert sanitized["properties"]["title"]["type"] == "string"

    priority = sanitized["$defs"]["_Priority"]
    assert priority["enum"] == ["low", "high"]
    assert priority["type"] == "string"

    summary = nested["properties"]["summary"]
    assert summary["description"] == "Tóm tắt nội dung."
    assert summary["type"] == "string"


def test_sanitizer_does_not_mutate_input_schema():
    raw_schema = _ComplexSchema.model_json_schema()
    original = copy.deepcopy(raw_schema)

    _to_gemini_compatible_schema(raw_schema)

    assert raw_schema == original
    assert raw_schema["additionalProperties"] is False
    assert raw_schema["properties"]["title"]["minLength"] == 1


def test_sanitizer_does_not_mutate_pydantic_model_schema():
    before = _ComplexSchema.model_json_schema()

    _to_gemini_compatible_schema(_ComplexSchema)

    after = _ComplexSchema.model_json_schema()
    assert after == before
    assert after["additionalProperties"] is False
    assert after["properties"]["items"]["minItems"] == 1


def test_sanitizer_handles_complex_nested_structure_without_error():
    sanitized = _to_gemini_compatible_schema(InterviewGenerationAIResponse)

    assert sanitized["type"] == "object"
    assert sanitized["properties"]["questions"]["type"] == "array"
    assert "$defs" in sanitized
    assert "InterviewQuestionAI" in sanitized["$defs"]


# ---------------------------------------------------------------------------
# Nhóm 2: Schema phản hồi thực tế của M6
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [InterviewGenerationAIResponse, InterviewAnswerScoreAI],
)
def test_real_m6_schema_is_converted_without_unsupported_keys(model):
    sanitized = _to_gemini_compatible_schema(model)

    _assert_no_forbidden_keys(sanitized)
    assert sanitized["type"] == "object"
    assert "properties" in sanitized
    assert "required" in sanitized


def test_interview_generation_schema_preserves_structure_for_gemini():
    sanitized = _to_gemini_compatible_schema(InterviewGenerationAIResponse)

    questions = sanitized["properties"]["questions"]
    assert questions == {
        "items": {"$ref": "#/$defs/InterviewQuestionAI"},
        "title": "Questions",
        "type": "array",
    }
    assert sanitized["required"] == ["questions"]

    question = sanitized["$defs"]["InterviewQuestionAI"]
    assert question["type"] == "object"
    assert set(question["properties"]) == {
        "question_text",
        "competency",
        "evaluation_criteria",
    }
    assert question["required"] == [
        "question_text",
        "competency",
        "evaluation_criteria",
    ]
    assert question["properties"]["evaluation_criteria"]["type"] == "array"
    assert question["properties"]["evaluation_criteria"]["items"] == {"type": "string"}


def test_interview_score_schema_preserves_number_and_feedback():
    sanitized = _to_gemini_compatible_schema(InterviewAnswerScoreAI)

    score = sanitized["properties"]["score"]
    assert score["title"] == "Score"
    assert [variant["type"] for variant in score["anyOf"]] == ["number", "string"]

    feedback = sanitized["properties"]["feedback"]
    assert feedback["type"] == "string"
    assert feedback["title"] == "Feedback"


@pytest.mark.parametrize(
    "model",
    [InterviewGenerationAIResponse, InterviewAnswerScoreAI],
)
def test_real_m6_schema_is_accepted_by_installed_sdk(model):
    sanitized = _to_gemini_compatible_schema(model)
    fake_client = SimpleNamespace(vertexai=False)

    sdk_schema = genai_transformers.t_schema(fake_client, sanitized)

    assert isinstance(sdk_schema, types.Schema)
    _assert_no_forbidden_keys(_dump_sdk_schema(sdk_schema))


# ---------------------------------------------------------------------------
# Nhóm 3: Contract test với GeminiProvider và SDK
# ---------------------------------------------------------------------------


def test_provider_passes_sanitized_schema_to_generate_content_config(monkeypatch):
    response_schema = _capture_provider_schema(monkeypatch, InterviewGenerationAIResponse)

    assert isinstance(response_schema, dict)
    _assert_no_forbidden_keys(response_schema)
    assert response_schema["type"] == "object"
    assert "questions" in response_schema["properties"]


def test_sdk_payload_from_provider_config_has_no_unsupported_keys(monkeypatch):
    response_schema = _capture_provider_schema(monkeypatch, InterviewAnswerScoreAI)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
    )
    fake_client = SimpleNamespace(vertexai=False)

    payload = _GenerateContentConfig_to_mldev(fake_client, config)

    dumped = _dump_sdk_schema(payload["responseSchema"])
    _assert_no_forbidden_keys(dumped)
    assert dumped["type"] == "OBJECT"
    assert set(dumped["properties"]) == {"score", "feedback"}


def test_unsanitized_pydantic_schema_would_send_unsupported_keys():
    """Chứng minh sanitizer thực sự thay đổi payload, không chỉ đổi tham số."""
    raw_schema = InterviewGenerationAIResponse.model_json_schema()
    fake_client = SimpleNamespace(vertexai=False)

    sdk_schema = genai_transformers.t_schema(fake_client, raw_schema)

    raw_keys = _collect_keys(_dump_sdk_schema(sdk_schema))
    assert "additionalProperties" in raw_keys
    assert raw_keys & {"minItems", "maxItems", "minLength", "maxLength"}


def test_sdk_rejects_truthy_additional_properties_but_sanitized_schema_is_safe():
    raw_schema = copy.deepcopy(_ComplexSchema.model_json_schema())
    raw_schema["additionalProperties"] = {"type": "string"}
    fake_client = SimpleNamespace(vertexai=False)

    with pytest.raises(ValueError):
        genai_transformers.t_schema(fake_client, raw_schema)

    sanitized = _to_gemini_compatible_schema(_ComplexSchema)
    assert genai_transformers.t_schema(fake_client, sanitized) is not None


# ---------------------------------------------------------------------------
# Nhóm 4: Pydantic vẫn xác thực đầy đủ
# ---------------------------------------------------------------------------


def _valid_interview_payload():
    return {
        "questions": [
            {
                "question_text": "Câu hỏi số 1?",
                "competency": "Python",
                "evaluation_criteria": ["Rõ ràng", "Đúng trọng tâm"],
            },
            {
                "question_text": "Câu hỏi số 2?",
                "competency": "SQL",
                "evaluation_criteria": ["Chính xác"],
            },
            {
                "question_text": "Câu hỏi số 3?",
                "competency": "Giao tiếp",
                "evaluation_criteria": ["Mạch lạc"],
            },
        ]
    }


def test_valid_m6_data_still_passes_pydantic_validation():
    result = _generate(
        InterviewGenerationAIResponse,
        json.dumps(_valid_interview_payload(), ensure_ascii=False),
    )

    assert isinstance(result, InterviewGenerationAIResponse)
    assert len(result.questions) == 3
    assert result.questions[0].competency == "Python"


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda payload: payload.update(questions=[]), id="too-few-questions"),
        pytest.param(
            lambda payload: payload["questions"][0].update(evaluation_criteria=[]),
            id="empty-evaluation-criteria",
        ),
        pytest.param(
            lambda payload: payload["questions"][0].update(question_text="   "),
            id="blank-question-text",
        ),
        pytest.param(
            lambda payload: payload["questions"][0].update(unexpected="x"),
            id="extra-field",
        ),
    ],
)
def test_invalid_m6_generation_data_is_still_rejected(mutate):
    payload = _valid_interview_payload()
    mutate(payload)

    with pytest.raises(AIResponseValidationError):
        _generate(
            InterviewGenerationAIResponse,
            json.dumps(payload, ensure_ascii=False),
        )


@pytest.mark.parametrize(
    "score",
    [101, -1, "không phải số", float("nan")],
)
def test_invalid_m6_score_is_still_rejected(score):
    payload = {"score": score, "feedback": "Hợp lệ"}

    with pytest.raises(AIResponseValidationError):
        _generate(
            InterviewAnswerScoreAI,
            json.dumps(payload, ensure_ascii=False, allow_nan=True),
        )


def test_blank_m6_feedback_is_still_rejected():
    payload = {"score": 80, "feedback": "   "}

    with pytest.raises(AIResponseValidationError):
        _generate(InterviewAnswerScoreAI, json.dumps(payload))


def test_valid_m6_score_is_still_accepted():
    result = _generate(InterviewAnswerScoreAI, '{"score": 85, "feedback": "Tốt"}')

    assert isinstance(result, InterviewAnswerScoreAI)
    assert result.score == 85
    assert result.feedback == "Tốt"


def test_sanitizing_does_not_remove_pydantic_constraints():
    before = InterviewAnswerScoreAI.model_json_schema()
    _to_gemini_compatible_schema(InterviewAnswerScoreAI)
    after = InterviewAnswerScoreAI.model_json_schema()

    assert after == before
    score_variants = after["properties"]["score"]["anyOf"]
    assert any("minimum" in variant for variant in score_variants)
    assert any("maximum" in variant for variant in score_variants)

    with pytest.raises(ValidationError):
        InterviewAnswerScoreAI.model_validate({"score": 101, "feedback": "Tốt"})
    with pytest.raises(ValidationError):
        InterviewAnswerScoreAI.model_validate({"score": 0, "feedback": "Tốt", "x": 1})


def test_extra_forbid_remains_enabled():
    assert AIStructuredResponse.model_config["extra"] == "forbid"

    with pytest.raises(ValidationError):
        InterviewGenerationAIResponse.model_validate(
            {**_valid_interview_payload(), "unexpected": "x"}
        )
