import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app import ai
from app.db import connect
from app.main import SearchRequest, add_neighbor_context, prepare_visual_evidence, search_chunks


DEFAULT_CASES = Path(__file__).parent / "evals" / "theoretical_mechanics.json"
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
STANDARDS = {
    "retrieval": "Top-5 检索结果至少包含一个预期 PDF 页",
    "insufficient": "资料充分/不足判断与标注一致",
    "citation": "回答至少引用一个预期 PDF 页；资料不足时不得引用",
    "terms": "回答包含该题预先标注的全部课程关键词",
    "math": "需要公式的题使用可渲染的 LaTeX 定界符",
    "control_characters": "回答不含会破坏公式显示的控制字符",
}


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


def grade_answer(result: dict, evidence: list[dict], case: dict) -> tuple[dict[str, bool], list[dict]]:
    expected_insufficient = case.get("should_be_insufficient", False)
    cited = [evidence[number - 1] for number in result["citation_numbers"]]
    answer = normalized(result["answer"])
    checks = {
        "insufficient": result["insufficient"] == expected_insufficient,
        "citation": not cited if expected_insufficient else any(
            source_matches(item, case["sources"]) for item in cited
        ),
        "terms": all(normalized(term) in answer for term in case.get("answer_terms", [])),
        "math": not case.get("requires_math") or "\\(" in result["answer"] or "\\[" in result["answer"],
        "control_characters": CONTROL_CHARACTERS.search(result["answer"]) is None,
    }
    return checks, cited


def answer_passes(result: dict, evidence: list[dict], case: dict) -> bool:
    checks, _ = grade_answer(result, evidence, case)
    return all(checks.values())


def write_report(path: Path, records: list[dict], planned: int, top_k: int) -> None:
    retrieval_hits = sum(record["retrieval_ok"] for record in records)
    answer_hits = sum(record.get("answer_ok", False) for record in records)
    overall_hits = sum(record["retrieval_ok"] and record.get("answer_ok", False) for record in records)
    lines = [
        "# CiteMind 理论力学回答质量评测",
        "",
        f"- 运行时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- 计划题数：{planned}",
        f"- 已完成：{len(records)}",
        f"- 回答模型：{records[0].get('model', '未记录')}" if records else "- 回答模型：未记录",
        f"- 使用原页视觉回答：{sum(record.get('vision_used', False) for record in records)} 题",
        f"- Top-{top_k} 召回通过：{retrieval_hits}/{len(records)}" if records else "- Top-5 召回通过：0/0",
        f"- 回答检查通过：{answer_hits}/{len(records)}" if records else "- 回答检查通过：0/0",
        f"- 整体通过：{overall_hits}/{len(records)}" if records else "- 整体通过：0/0",
        "",
        "## 判定标准",
        "",
        "每题只有在召回检查和全部回答检查均通过时，才记为整体通过。",
        "本轮采用可重复的确定性规则，不使用另一个 AI 充当裁判；规则通过不等同于已证明数学内容完全正确。",
        "",
    ]
    lines.extend(f"- **{name}**：{description}" for name, description in STANDARDS.items())
    for record in records:
        status = "通过" if record["retrieval_ok"] and record.get("answer_ok", False) else "失败"
        lines.extend([
            "",
            f"## {record['id']} - {status}",
            "",
            f"- 问题：{record['question']}",
            f"- 预期资料页：{'; '.join(record['expected']) or '无，应判断资料不足'}",
            f"- Top-{top_k} 实际检索：{'; '.join(record['retrieved']) or '无'}",
            f"- 实际引用：{'; '.join(record.get('cited', [])) or '无'}",
            f"- 必须包含的课程词：{'; '.join(record.get('answer_terms', [])) or '无'}",
            f"- 缺少的课程词：{'; '.join(record.get('missing_terms', [])) or '无'}",
            f"- 召回：{'通过' if record['retrieval_ok'] else '失败'}",
        ])
        if record.get("error"):
            lines.append(f"- 回答错误：{record['error']}")
        else:
            for name, passed in record.get("checks", {}).items():
                lines.append(f"- {name}：{'通过' if passed else '失败'}")
        lines.extend(["", "### 实际回答", "", record.get("answer") or "（未生成回答）"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and grounded answers on a real course")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--course-id", type=int)
    parser.add_argument("--course-name", default="理论力学")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--answers", action="store_true", help="Also call the configured AI models")
    parser.add_argument("--limit", type=int, help="Run only the first N cases")
    parser.add_argument("--report", type=Path, help="Write a detailed Markdown report")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    load_dotenv(Path(__file__).parents[1] / ".env")
    cases = load_cases(args.cases)
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        cases = cases[:args.limit]
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
    records = []
    for case in cases:
        results = search_chunks(course["id"], SearchRequest(query=case["question"], top_k=max(args.top_k, 8)))
        expected_insufficient = case.get("should_be_insufficient", False)
        retrieval_ok = not results if expected_insufficient else any(
            source_matches(item, case["sources"]) for item in results[:args.top_k]
        )
        retrieval_hits += retrieval_ok
        answer_ok = None
        result = None
        cited = []
        checks = {}
        error = None
        images = []
        if args.answers:
            evidence = add_neighbor_context(results[:8])
            if not evidence:
                answer_ok = expected_insufficient
                checks = {"insufficient": answer_ok}
            else:
                try:
                    visual_evidence, images = prepare_visual_evidence(case["question"], evidence)
                    result = (
                        ai.answer_with_images(case["question"], visual_evidence, [], images)
                        if images else ai.answer(case["question"], evidence, [])
                    )
                    checks, cited = grade_answer(result, visual_evidence if images else evidence, case)
                    answer_ok = all(checks.values())
                except ai.AIError as exc:
                    answer_ok, error = False, str(exc)
            answer_hits += answer_ok
        record = {
            "id": case["id"],
            "question": case["question"],
            "expected": [
                f"{source['title']} p.{page}" for source in case["sources"] for page in source["pages"]
            ],
            "retrieved": [f"{item['title']} p.{item['page_number']}" for item in results[:args.top_k]],
            "retrieval_ok": retrieval_ok,
            "answer_ok": answer_ok,
            "checks": checks,
            "cited": [f"{item['title']} p.{item['page_number']}" for item in cited],
            "answer": result["answer"] if result else None,
            "error": error,
            "answer_terms": case.get("answer_terms", []),
            "missing_terms": [
                term for term in case.get("answer_terms", [])
                if not result or normalized(term) not in normalized(result["answer"])
            ],
            "model": ai.VISION_ANSWER_MODEL() if images else ai.CHAT_MODEL(),
            "vision_used": bool(images),
        }
        records.append(record)
        if args.report:
            write_report(args.report, records, len(cases), args.top_k)
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
