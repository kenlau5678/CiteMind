import argparse
import json
import re
from pathlib import Path

from app import ai
from app.db import connect
from app.main import SearchRequest, add_neighbor_context, prepare_visual_evidence, search_chunks


DEFAULT_CASES = Path(__file__).parent / "evals" / "theoretical_mechanics.json"
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def load_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation file must contain a non-empty JSON array")
    if len({case.get("id") for case in cases}) != len(cases):
        raise ValueError("Evaluation case IDs must be unique")
    for case in cases:
        if not case.get("question") or not isinstance(case.get("sources"), list):
            raise ValueError(f"Invalid evaluation case: {case.get('id', '(missing id)')}")
    return cases


def source_matches(item: dict, sources: list[dict]) -> bool:
    return any(item["title"] == source["title"] and item["page_number"] in source["pages"] for source in sources)


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("\\", "").lower()


def answer_passes(result: dict, evidence: list[dict], case: dict) -> bool:
    expected_insufficient = case.get("should_be_insufficient", False)
    if result["insufficient"] != expected_insufficient or CONTROL_CHARACTERS.search(result["answer"]):
        return False
    if expected_insufficient:
        return not result["citation_numbers"]
    cited = [evidence[number - 1] for number in result["citation_numbers"]]
    if not any(source_matches(item, case["sources"]) for item in cited):
        return False
    answer = normalized(result["answer"])
    if not all(normalized(term) in answer for term in case.get("answer_terms", [])):
        return False
    return not case.get("requires_math") or "\\(" in result["answer"] or "\\[" in result["answer"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and grounded answers on a real course")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--course-id", type=int)
    parser.add_argument("--course-name", default="理论力学")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--answers", action="store_true", help="Also call the configured AI models")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    with connect() as db:
        course = db.execute(
            "SELECT id,name FROM courses WHERE id=?" if args.course_id else "SELECT id,name FROM courses WHERE name=?",
            (args.course_id if args.course_id else args.course_name,),
        ).fetchone()
    if not course:
        parser.error("Course not found")
    if args.answers and not ai.API_KEY():
        parser.error("OPENAI_API_KEY is required with --answers")

    retrieval_hits = answer_hits = 0
    for case in cases:
        results = search_chunks(course["id"], SearchRequest(query=case["question"], top_k=max(args.top_k, 8)))
        expected_insufficient = case.get("should_be_insufficient", False)
        retrieval_ok = not results if expected_insufficient else any(
            source_matches(item, case["sources"]) for item in results[:args.top_k]
        )
        retrieval_hits += retrieval_ok
        answer_ok = None
        if args.answers:
            evidence = add_neighbor_context(results[:8])
            if not evidence:
                answer_ok = expected_insufficient
            else:
                visual_evidence, images = prepare_visual_evidence(case["question"], evidence)
                result = (
                    ai.answer_with_images(case["question"], visual_evidence, [], images)
                    if images else ai.answer(case["question"], evidence, [])
                )
                answer_ok = answer_passes(result, visual_evidence if images else evidence, case)
            answer_hits += answer_ok
        status = "PASS" if retrieval_ok and answer_ok is not False else "MISS"
        detail = f"retrieve={'yes' if retrieval_ok else 'no'}"
        if answer_ok is not None:
            detail += f", answer={'yes' if answer_ok else 'no'}"
        print(f"{status} {case['id']} [{detail}] {case['question']}")

    retrieval_score = retrieval_hits / len(cases)
    print(f"\nTop-{args.top_k} retrieval: {retrieval_hits}/{len(cases)} = {retrieval_score:.0%}")
    answer_score = answer_hits / len(cases) if args.answers else 1.0
    if args.answers:
        print(f"Grounded answers: {answer_hits}/{len(cases)} = {answer_score:.0%}")
    raise SystemExit(0 if retrieval_score >= args.threshold and answer_score >= args.threshold else 1)


if __name__ == "__main__":
    main()
