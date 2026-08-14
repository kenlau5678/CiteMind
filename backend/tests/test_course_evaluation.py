from pathlib import Path

from evaluate_course import answer_passes, load_cases, write_report


def test_theoretical_mechanics_evaluation_set_is_complete():
    cases = load_cases(Path(__file__).parents[1] / "evals" / "theoretical_mechanics.json")
    assert len(cases) == 50
    assert sum(case.get("should_be_insufficient", False) for case in cases) == 3
    assert all(case["sources"] or case.get("should_be_insufficient") for case in cases)


def test_grounded_answer_requires_expected_page_terms_and_math():
    case = {
        "sources": [{"title": "Lecture", "pages": [6]}],
        "answer_terms": ["虚功"],
        "requires_math": True,
    }
    result = {"answer": "由虚功得 \\(N=P\\) [1]", "citation_numbers": [1], "insufficient": False}
    assert answer_passes(result, [{"title": "Lecture", "page_number": 6}], case)
    assert not answer_passes(result, [{"title": "Lecture", "page_number": 5}], case)


def test_markdown_report_records_question_and_failure(tmp_path):
    report = tmp_path / "report.md"
    write_report(report, [{
        "id": "tm-001", "question": "Question?", "expected": ["Lecture p.6"],
        "retrieved": ["Lecture p.5"], "retrieval_ok": False, "answer_ok": False,
        "checks": {"citation": False}, "cited": ["Lecture p.5"], "answer": "Wrong.", "error": None,
    }], 1, 5)
    text = report.read_text(encoding="utf-8")
    assert "tm-001 - 失败" in text
    assert "Question?" in text
    assert "citation：失败" in text
