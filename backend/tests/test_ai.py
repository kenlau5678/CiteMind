import pytest

from app.ai import AIError, validate_answer


def test_validated_citations_match_inline_numbers():
    result = validate_answer('{"answer":"A claim [2] and another [1].","citations":[2,1]}', 2)
    assert result["citation_numbers"] == [1, 2]


@pytest.mark.parametrize("raw", [
    '{"answer":"Invented [3].","citations":[3]}',
    '{"answer":"Mismatch [1].","citations":[]}',
    '{"answer":"No inline citation.","citations":[1]}',
    'not json',
])
def test_invalid_or_fabricated_citations_are_rejected(raw):
    with pytest.raises(AIError):
        validate_answer(raw, 2)

