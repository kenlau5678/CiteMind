import pytest

from app.ai import AIError, validate_answer


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


@pytest.mark.parametrize("raw", [
    '{"answer":"Invented [3].","citations":[3],"insufficient":false}',
    '{"answer":"Mismatch [1].","citations":[],"insufficient":false}',
    '{"answer":"No inline citation.","citations":[1],"insufficient":false}',
    '{"answer":"Unsupported answer.","citations":[],"insufficient":false}',
    '{"answer":"Contradiction [1].","citations":[1],"insufficient":true}',
    '{"answer":"Missing protocol field.","citations":[]}',
    'not json',
])
def test_invalid_or_fabricated_citations_are_rejected(raw):
    with pytest.raises(AIError):
        validate_answer(raw, 2)
