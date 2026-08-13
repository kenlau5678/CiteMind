import pytest
import httpx

from app.ai import AIError, answer, validate_answer


def test_validated_citations_match_inline_numbers():
    result = validate_answer('{"answer":"A claim [2] and another [1].","citations":[2,1],"insufficient":false}', 2)
    assert result["citation_numbers"] == [1, 2]
    assert result["insufficient"] is False


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
