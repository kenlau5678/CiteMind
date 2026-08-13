# Validation report

Validated on 2026-08-13 with Windows 11, Python 3.12, Node.js 24, and a Chromium-based browser.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Backend risk-chain tests | `cd backend; .\.venv\Scripts\python -m pytest -q` | 23/23 passed |
| Production frontend | `cd frontend; npm run build` | Passed |
| Page provenance | Generated two-page PDF test | Text stayed on PDF pages 1 and 2 |
| Citation integrity | Invalid, fabricated, and mismatched citation tests | All rejected |
| Unsupported answer integrity | Supported answer without a citation | Rejected |
| Insufficient-evidence protocol | Explicit insufficient answer | Accepted only with zero citations |
| Complete document deletion | API integration test | File endpoint, chunks, and course chat removed |
| Scanned-PDF handling | Empty-image PDF integration test | Rejected with an explicit OCR limitation |
| Failed-upload cleanup | Corrupt, 201-page, and embedding-failure integration tests | No original file remained |
| Course isolation | Document from course A used as scope in course B | Rejected before retrieval |
| Chinese chunking | Adjacent Chinese sentences without spaces | Split at Chinese punctuation |
| Chinese rephrasing | “为什么混合检索更适合课程资料？” | Local bigram retrieval ranked PDF page 5 first |
| Retrieval quality | 30 manually annotated English and Chinese questions in one course | 30/30 top-five page recall (100%) |
| Chinese PDF text layer | Extracted all five pages after font subsetting | Standard Unicode; zero CJK compatibility characters |
| Chinese PDF rendering | Poppler rendered the final five A4 pages at 120 DPI; every page inspected | No missing glyphs, clipping, overlap, or footer errors |
| Real English AI answer | `gpt-4.1-mini` against public demo material | 14.02 s; valid citation to page 8 |
| Real evidence refusal | Asked for tuition fee absent from public demo | `insufficient=true`; zero citations; 17.74 s |
| Real Chinese AI answer | Rephrased Chinese question scoped to Chinese demo | Chinese answer; valid citation to page 5; 19.60 s |
| Chat transport failure | Provider disconnected during real validation plus focused test | Controlled 502; no raw 500 |
| 100-page indexing | Generated 100-page text PDF, warm local model cache | 3.47 seconds |
| Citation navigation | Browser interaction against production build | Opened PDF page 8 and rendered six evidence highlights |
| Private tutorial ingestion | Seven user-supplied PDFs | 222/222 pages had selectable text and indexed successfully |
| Private document-scoped revision | Three real questions; every citation clicked | 3/3 useful answers; 6/6 direct page citations |
| Chinese short-fragment highlighting | Real private citation page | Improved from zero to five highlights |
| AI formula rendering | Production browser with six formulas | Inline/display math, subscripts, superscripts, fraction, integral, root, and matrix rendered; no browser errors |
| Course-wide private comparison | Three broad cross-chapter questions | Partial: weak outline citations and one incorrect formula synthesis recorded locally |
| Scope isolation | Browser switched course-wide chat to one document | Old messages cleared, new scope selected, no dialog or console error |
| Browser runtime errors | Browser console after citation navigation | None |
| One-command startup | `.\start.ps1`, then `/api/health` | `{"status":"ok"}` |
| Demo video | `ffprobe` | H.264, 1280×720, 30 fps, 18 seconds |

## Still requiring acceptance

- A real course containing the required lecture, personal note, and paper source mix
- A clean course-wide comparison session without weak outline citations or incorrect synthesis
- Public GitHub repository and `v1.0.0` release

These items are not represented as complete by demo data or mocked model responses.
