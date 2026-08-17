import json

import pytest
import httpx

from app import ai
from app.ai import AIError, _answer_prompt, answer, answer_with_images, decide_agent_action, validate_answer


def test_answer_prompt_treats_course_wording_as_canonical():
    prompt = _answer_prompt(
        "解释牛顿第三定律",
        [{"title": "质点动力学", "page_number": 6, "content": "牛顿第三定律（相互作用公理）", "current_page": True}],
        [],
    )
    assert "CURRENTLY DISPLAYED PDF PAGE" in prompt
    assert "mirror the course material's terminology" in prompt
    assert "define every variable in words" in prompt
    assert "do not substitute general textbook wording or omit qualifiers" in prompt
    assert "Copy every mathematical symbol exactly from the source" in prompt


def test_validated_citations_match_inline_numbers():
    result = validate_answer('{"answer":"A claim [2] and another [1].","citations":[2,1],"insufficient":false}', 2)
    assert result["citation_numbers"] == [1, 2]
    assert result["insufficient"] is False


def test_control_characters_are_removed_without_damaging_latex():
    result = validate_answer(
        '{"answer":"虚转角 \\u0001\\\\(\\\\delta\\\\theta\\\\) [1]","citations":[1],"insufficient":false}', 1
    )
    assert result["answer"] == "虚转角 \\(\\delta\\theta\\) [1]"


def test_bare_greek_symbols_are_wrapped_for_math_rendering():
    result = validate_answer(
        '{"answer":"进动角ψ，章动角θ，自转角φ [1]","citations":[1],"insufficient":false}', 1
    )
    assert result["answer"] == "进动角\\(ψ\\)，章动角\\(θ\\)，自转角\\(φ\\) [1]"


def test_existing_greek_math_span_is_not_wrapped_twice():
    result = validate_answer(
        '{"answer":"角度 \\\\(θ\\\\) [1]","citations":[1],"insufficient":false}', 1
    )
    assert result["answer"] == "角度 \\(θ\\) [1]"


def test_explicit_insufficient_answer_can_have_no_citations():
    result = validate_answer(
        '{"answer":"The supplied material does not answer this question.","citations":[],"insufficient":true}', 2
    )
    assert result["citation_numbers"] == []
    assert result["insufficient"] is True


def test_valid_citation_array_repairs_missing_inline_marker():
    result = validate_answer(
        '{"answer":"A supported paragraph.","citations":[1],"insufficient":false}', 1
    )
    assert result["answer"] == "A supported paragraph. [1]"
    assert result["citation_numbers"] == [1]


@pytest.mark.parametrize("raw", [
    '{"answer":"Invented [3].","citations":[3],"insufficient":false}',
    '{"answer":"Mismatch [1].","citations":[],"insufficient":false}',
    '{"answer":"Unsupported answer.","citations":[],"insufficient":false}',
    '{"answer":"Contradiction [1].","citations":[1],"insufficient":true}',
    '{"answer":"Missing protocol field.","citations":[]}',
    'not json',
])
def test_invalid_or_fabricated_citations_are_rejected(raw):
    with pytest.raises(AIError):
        validate_answer(raw, 2)


def test_chat_transport_error_is_safely_mapped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")

    def disconnect(*_, **__):
        raise httpx.RemoteProtocolError("server disconnected")

    monkeypatch.setattr(httpx.Client, "post", disconnect)
    with pytest.raises(AIError, match="Chat service connection failed"):
        answer(
            "What does the source say?",
            [{"title": "Lecture", "page_number": 1, "content": "Evidence."}],
            [],
        )


def test_chat_retries_once_when_citation_numbers_are_invalid(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    replies = iter([
        '{"answer":"Wrong [2].","citations":[2],"insufficient":false}',
        '{"answer":"Correct [1].","citations":[1],"insufficient":false}',
    ])
    calls = []

    def post(*_, **kwargs):
        calls.append(kwargs["json"])
        raw = next(replies)
        return httpx.Response(200, json={"choices": [{"message": {"content": raw}}]}, request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(httpx.Client, "post", post)
    result = answer("Question?", [{"title": "Lecture", "page_number": 1, "content": "Evidence."}], [])
    assert result["citation_numbers"] == [1]
    assert len(calls) == 2
    assert "Correct only the citation protocol" in json.dumps(calls[1])


def test_vision_answer_retries_once_when_citation_numbers_are_invalid(monkeypatch):
    replies = iter([
        '{"answer":"Wrong [2].","citations":[2],"insufficient":false}',
        '{"answer":"Correct [1].","citations":[1],"insufficient":false}',
    ])
    calls = []

    def request(payload):
        calls.append(payload)
        return next(replies)

    monkeypatch.setattr(ai, "_responses_request", request)
    result = answer_with_images(
        "Question?", [{"title": "Lecture", "page_number": 1, "content": "Evidence."}], [], [],
    )
    assert result["citation_numbers"] == [1]
    assert len(calls) == 2
    assert "Correct only the citation protocol" in json.dumps(calls[1])


def test_agent_action_is_limited_to_validated_read_only_tools(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")

    def post(*_, **__):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "tool": "read_page",
            "arguments": {"document_id": 7, "page_number": 4, "radius": 1},
        })}}]}, request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(httpx.Client, "post", post)
    decision = decide_agent_action("Explain the topic", [{
        "document_id": 7, "course_name": "Mechanics", "title": "Lecture",
        "page_number": 4, "content": "Evidence",
    }], [])
    assert decision == {
        "tool": "read_page",
        "arguments": {"document_id": 7, "page_number": 4, "radius": 1},
    }


def test_agent_rejects_unrecognized_actions(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")

    def post(*_, **__):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "tool": "delete_document", "arguments": {"document_id": 1},
        })}}]}, request=httpx.Request("POST", "https://example.test"))

    monkeypatch.setattr(httpx.Client, "post", post)
    with pytest.raises(AIError, match="invalid action"):
        decide_agent_action("Goal", [], [])
