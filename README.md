# CiteMind

**Ask your notes. Verify every answer.**

![CiteMind cross-course Knowledge Home](docs/images/citemind-knowledge-home.png)

[Watch the 18-second product walkthrough](docs/video/citemind-demo.mp4)

| Welcome | Add a source | Verify evidence |
| --- | --- | --- |
| ![CiteMind welcome screen](docs/images/citemind-welcome.png) | ![CiteMind PDF upload](docs/images/citemind-upload.png) | ![CiteMind citation viewer](docs/images/citemind-workspace.png) |

![CiteMind AI formula rendering](docs/images/citemind-formulas.png)

![CiteMind original-page formula evidence](docs/images/citemind-formula-preview.png)

CiteMind is a local-first course knowledge base for lecture notes, student notes, and papers. It answers questions only from the uploaded material, attaches a page-level citation to every supported claim, and opens the exact PDF page behind each citation.

> Status: working v0.2.1 MVP. Streaming cross-course Knowledge Agent, text and scanned PDFs with page vision, single user, Windows-first.

## Why CiteMind

Most document chat demos optimize for a fluent answer. CiteMind optimizes for a verifiable answer:

- the Knowledge Home can explore the whole library and show which courses and materials teach a topic;
- course workspaces stay available for questions grounded in one course or one selected document;
- the Agent is bounded to six read-only search, page-reading, and visual-inspection actions;
- Agent activity and the validated answer stream into the Knowledge Home while citations remain hidden until verification completes;
- citations are server-validated and cannot name a source the retriever did not supply;
- every citation contains the file, PDF page, and original excerpt;
- clicking evidence opens and highlights the matching PDF page;
- repeated chunks from the same PDF page are merged into one evidence card;
- source cards can be dragged into a preferred reading order, which persists after refresh;
- AI answers typeset inline and display LaTeX, including fractions and matrices;
- headings, lists, emphasis, code, links, blockquotes, and Markdown tables render as structured answer content;
- known legacy `Symbol` formula glyphs are decoded for retrieval, while every citation retains an exact original-page visual preview;
- diagram, plot, and formula questions can inspect one relevant original page with vision; page descriptions are cached after the first use;
- image-only scanned pages are transcribed in the background with live page progress, resumable failures, and original PDF page numbers;
- weak retrieval produces “no reliable evidence” instead of a confident guess.

## Quick start

Requirements: Windows 11, Python 3.12, Node.js 20+, and an OpenAI-compatible chat API key.

```powershell
Copy-Item .env.example .env
# Add OPENAI_API_KEY to .env
.\start.ps1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The first document takes longer because CiteMind downloads a multilingual local embedding model (about 220 MB) once.

Without an API key you can still create courses, upload and read PDFs, build the local index, and open original-page evidence. Add the key later to enable AI answers. If port 8000 is already in use, run `$env:CITEMIND_PORT=8002; .\start.ps1`.

For development, run the backend and frontend separately:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --env-file ..\.env
```

```powershell
cd frontend
npm install
npm run dev
```

## Product flow

1. Create courses and add text or scanned PDF lectures, notes, or papers.
2. Ask the Knowledge Home which courses and materials explain a topic.
3. Watch the bounded Agent search the library, read exact pages, and selectively inspect visual evidence.
4. Review the cited knowledge structure and related-course map, or enter one course for a focused question.
5. Open any citation to inspect the exact original PDF page and highlighted evidence.

## Architecture

```mermaid
flowchart LR
    PDF["Text or scanned PDF"] --> Parse["Page-preserving parser<br/>local extraction or visual OCR"]
    Parse --> Chunks["Paragraph chunks<br/>never cross a page"]
    Chunks --> FTS["SQLite FTS5"]
    Chunks --> Local["Local multilingual embeddings"]
    Q["Knowledge Home or course question"] --> Agent["Bounded read-only Agent<br/>search · read page · inspect page"]
    Agent --> Hybrid["Hybrid retrieval"]
    FTS --> Hybrid
    Local --> Hybrid
    Hybrid --> Evidence["Numbered evidence"]
    Evidence --> Visual{"Visual page needed?"}
    Visual -->|No| LLM["Configured chat API"]
    Visual -->|Yes| Page["Original PDF page<br/>cached visual description"]
    Page --> Vision["Vision answer model"]
    Vision --> Gate
    LLM --> Gate["Citation validator"]
    Gate --> UI["Answer + file + page + excerpt"]
```

The stack is intentionally small: React, FastAPI, SQLite/FTS5, PyMuPDF, PDF.js, and FastEmbed. Vectors are JSON rows in SQLite and cosine-ranked in process; this is appropriate for personal course libraries and avoids running a vector database.

## Privacy boundary

- Original PDFs, extracted text, SQLite data, chat history, and embeddings stay in `backend/data/`.
- Embeddings are generated locally with a multilingual ONNX model.
- During scanned-PDF upload, each image-only page is sent once for visual OCR. During course questions, only the question, up to fourteen retrieved excerpts, at most two recent conversation turns, and at most one relevant original-page image go to the configured AI service. A Knowledge Home exploration sends up to sixteen excerpts and the bounded Agent's read-only action history.
- API keys are read from `.env`; document text and keys are not logged by CiteMind.
- Deleting a document removes its file and index and clears that course's chat history.

Do not upload material you are not allowed to process. Your AI provider's retention terms still apply to the excerpts sent for answering.

## Deliberate limits

- PDF only; no Word or PowerPoint
- PDFs up to 25 MB and 200 pages; visual OCR is capped at 50 scanned pages per file
- one local user; no accounts, sync, or collaboration
- cross-course exploration is synchronous and capped at six read-only actions; it does not run autonomously in the background
- one configurable OpenAI provider; visual analysis uses the Responses API
- no summaries, flashcards, quiz generation, or knowledge graph

## Quality gates

Run the focused backend checks and the production frontend build:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
cd ..\frontend
npm run build
```

The tests cover page provenance, background scanned-PDF OCR, page-level retry and cleanup, complete deletion, visual-page selection and caching, safe visual fallback, course and cross-course Agent answers, read-only Agent permissions, insufficient-evidence handling, and rejection of fabricated, mismatched, or unsupported answers.

The self-authored English and Chinese demo courses and 30-question retrieval benchmark live in `sample-data/`. Generate the PDFs, index both in one temporary course, and evaluate top-5 page recall:

```powershell
backend\.venv\Scripts\python sample-data\build_sample.py
backend\.venv\Scripts\python backend\evaluate.py --local
```

Current bundled benchmark: **30/30 English and Chinese questions (100%)** retrieve the annotated page in the top five, against an 80% release threshold. Both language sets are searched together in one course. Displayed citation identifiers are server-validated; fabricated or mismatched identifiers fail closed.

The private theoretical-mechanics acceptance set contains 50 questions covering formulas, definitions, worked examples, citations, and insufficient-evidence behavior. Its default run is local and checks top-5 source-page retrieval without calling an AI model:

```powershell
cd backend
.\.venv\Scripts\python evaluate_course.py
.\.venv\Scripts\python evaluate_course.py --answers
.\.venv\Scripts\python evaluate_course.py --answers --limit 30 --report ..\docs\evaluations\theoretical_mechanics_30_v2.md
```

The second command also checks grounded citations, required course terminology, math delimiters, and invalid control characters. It uses the configured AI models and therefore incurs API usage.

Initial real-course baseline: **41/50 (82%)** top-5 source-page retrieval. The misses remain in the set as regression targets instead of being rewritten to fit the current retriever.

The first 30 deterministic answer checks using `gpt-4.1-mini` without original-page vision produced **25/30 retrieval passes, 23/30 answer-rule passes, and 22/30 overall passes**. See the [baseline report](docs/evaluations/theoretical_mechanics_30.md); it records expected pages, retrieved pages, cited pages, missing terms, every rule result, and the full answer.

After source-page verification, course-synonym support, topic-aware page ranking, citation repair, and math-delimiter cleanup, one run produced **30/30 retrieval passes, 30/30 answer-rule passes, and 30/30 overall passes**. See the [second-run comparison report](docs/evaluations/theoretical_mechanics_30_v2.md). Four fresh v0.1.8 runs all kept **30/30 retrieval** while answer-rule results ranged from **25/30 to 29/30**; see the [stability report and failure analysis](docs/evaluations/theoretical_mechanics_30_stability.md).

See the dated [validation report](docs/VALIDATION.md) for the complete test matrix, including the measured 3.47-second warm-cache indexing time for a generated 100-page text PDF.

Before publishing v1.0, complete the privacy-safe [real-course acceptance checklist](docs/REAL_COURSE_ACCEPTANCE.md).

The current engineering candidate is documented in the [v0.2.1 release notes](docs/RELEASE_NOTES_v0.2.1.md). The full mechanics course and formula-evidence path have been rechecked, but CiteMind is not represented as v1.0 until the required lecture/notes/paper source mix passes.

## Repository map

```text
backend/app/       API, storage, retrieval, and citation validation
backend/tests/     focused risk-chain tests
frontend/src/      Knowledge Home, course workspace, and PDF evidence viewer
sample-data/       self-authored demo course and retrieval benchmark
ROADMAP.md         frozen v1 scope and later ideas
```

## Known risks

PDF text extraction can scramble unusually complex multi-column layouts. Prompt injection inside source files is treated as untrusted reference text, but no LLM control is absolute. Always inspect cited evidence before relying on an answer.

## License

[MIT](LICENSE). The generated demo document is also released under CC0-1.0.
