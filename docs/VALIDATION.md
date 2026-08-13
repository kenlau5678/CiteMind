# Validation report

Validated on 2026-08-13 with Windows 11, Python 3.12, Node.js 24, and a Chromium-based browser.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Backend risk-chain tests | `cd backend; .\.venv\Scripts\python -m pytest -q` | 30/30 passed |
| Production frontend | `cd frontend; npm run build` | Passed |
| Clean dependency install | Empty verification directories; fresh Python virtual environment and `npm ci` | 25/25 backend checks and production frontend build passed |
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
| Private tutorial ingestion | Twenty-six user-supplied PDFs | 655/655 pages had selectable text and indexed successfully |
| Added mechanics retrieval | Seven questions across equilibrium, friction, force analysis, constraints, and virtual displacement | 7/7 expected pages appeared in the top five; ranks were 1 or 2 |
| Added mechanics AI answers | Three real cross-document questions with retry after two transient provider disconnects | 3/3 supported answers returned valid citations to the intended PDFs and pages |
| Added mechanics citation navigation | Production browser opened the friction-angle citation | Original-page preview loaded and opened page 4/25 with no browser errors |
| Complete-course extension | Twelve questions across particle dynamics, general theorems, collision, and Lagrange mechanics | 12/12 expected pages appeared in the top five; three real AI answers returned valid citations |
| Selective visual gate | Generated text-only and vector-diagram pages | Text page skipped locally; diagram page selected without an API call |
| Visual cache and fallback | Focused API integration tests | First analysis cached by document/page; repeat reused it; model failures fell back to text RAG |
| Real visual mechanics answer | Generalized-force question against the original formula page | `gpt-5.6-luna` cache plus `gpt-5.6-terra` answer succeeded in 16.61 s; repeat succeeded in 8.31 s |
| Visual citation navigation | Production browser against the real visual answer | `视觉核对` badge visible; original-page preview loaded; citation opened page 4/16; zero browser errors |
| Private document-scoped revision | Three real questions; every citation clicked | 3/3 useful answers; 6/6 direct page citations |
| Chinese short-fragment highlighting | Real private citation page | Improved from zero to five highlights |
| AI formula rendering | Production browser with six formulas | Inline/display math, subscripts, superscripts, fraction, integral, root, and matrix rendered; no browser errors |
| Legacy formula text | Seven private tutorials reindexed from geometrically sorted text | 3,787 private glyphs reduced to 1,661 using font-gated mappings only; checked page 27 reduced from 37 to zero |
| Original formula evidence | Production citation card against private page 27 | Sharp original-page crop displayed the fraction, Greek letters, accents, and surrounding prose |
| Public formula evidence | Self-authored CC0 demo PDF page 4 | Citation preview centered the source equation; public screenshot contains no private tutorial page |
| PDF fit-to-width | Production browser at 1280×720 | Reading and chat headers stayed visible; complete 479 px page fit inside the pane with zero retained scroll offset |
| Rare Chinese concept retrieval | “点的加速度如何分解为切向和法向” across all seven tutorials | Direct page 27 improved from rank 9 to rank 2 and entered the default eight-item evidence window |
| Course-wide private comparison | Three broad cross-chapter questions | Partial: weak outline citations and one incorrect formula synthesis recorded locally |
| Scope isolation | Browser switched course-wide chat to one document | Old messages cleared, new scope selected, no dialog or console error |
| Browser runtime errors | Rapid course switching, citation navigation, and original-page preview | None |
| One-command startup | `$env:CITEMIND_PORT=8002; .\start.ps1`, then `/api/health` | `{"status":"ok"}` on the configured alternate port |
| Demo video | `ffprobe` | H.264, 1280×720, 30 fps, 18 seconds |

## Still requiring acceptance

- A real course containing the required lecture, personal note, and paper source mix
- A clean course-wide comparison session without weak outline citations or incorrect synthesis
- Public GitHub repository and `v1.0.0` release

These items are not represented as complete by demo data or mocked model responses.
