import argparse
import json
import os
import tempfile
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description="Measure CiteMind top-5 page recall")
    parser.add_argument("--course-id", type=int)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--local", action="store_true", help="Create a temporary course and evaluate it in process")
    args = parser.parse_args()
    cases = json.loads((Path(__file__).parents[1] / "sample-data" / "evaluation.json").read_text(encoding="utf-8"))
    if not args.local and not args.course_id:
        parser.error("--course-id is required unless --local is used")
    hits = 0
    temporary = tempfile.TemporaryDirectory() if args.local else None
    if args.local:
        os.environ["CITEMIND_DATA_DIR"] = temporary.name
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        client.__enter__()
        course = client.post("/api/courses", json={"name": "Demo Machine Learning"}).json()
        pdf = Path(__file__).parents[1] / "sample-data" / "citemind-demo-course.pdf"
        with pdf.open("rb") as source:
            upload = client.post(
                f"/api/courses/{course['id']}/documents",
                data={"kind": "lecture"},
                files={"file": (pdf.name, source, "application/pdf")},
            )
        upload.raise_for_status()
        args.course_id = course["id"]
    else:
        client = httpx.Client(timeout=120)
    try:
        for case in cases:
            response = client.post(
                f"{args.url}/api/courses/{args.course_id}/search",
                json={"query": case["question"], "top_k": 5},
            )
            response.raise_for_status()
            results = response.json()
            hit = any(item["page_number"] == case["page"] and item["filename"] == case["file"] for item in results)
            hits += hit
            print(f"{'PASS' if hit else 'MISS'} p.{case['page']}: {case['question']}")
    finally:
        client.__exit__(None, None, None) if args.local else client.close()
        if temporary:
            temporary.cleanup()
    score = hits / len(cases)
    print(f"\nTop-5 page recall: {hits}/{len(cases)} = {score:.0%}")
    raise SystemExit(0 if score >= 0.8 else 1)


if __name__ == "__main__":
    main()
