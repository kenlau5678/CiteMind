# Validation report

Validated on 2026-08-13 with Windows 11, Python 3.12, Node.js 24, and a Chromium-based browser.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Backend risk-chain tests | `cd backend; .\.venv\Scripts\python -m pytest -q` | 14/14 passed |
| Production frontend | `cd frontend; npm run build` | Passed |
| Page provenance | Generated two-page PDF test | Text stayed on PDF pages 1 and 2 |
| Citation integrity | Invalid, fabricated, and mismatched citation tests | All rejected |
| Unsupported answer integrity | Supported answer without a citation | Rejected |
| Insufficient-evidence protocol | Explicit insufficient answer | Accepted only with zero citations |
| Complete document deletion | API integration test | File endpoint, chunks, and course chat removed |
| Scanned-PDF handling | Empty-image PDF integration test | Rejected with an explicit OCR limitation |
| Retrieval quality | 20 manually annotated demo questions | 20/20 top-five page recall (100%) |
| 100-page indexing | Generated 100-page text PDF, warm local model cache | 3.47 seconds |
| Citation navigation | Browser interaction against production build | Opened PDF page 8 and rendered six evidence highlights |
| Scope isolation | Browser switched course-wide chat to one document | Old messages cleared, new scope selected, no dialog or console error |
| Browser runtime errors | Browser console after citation navigation | None |
| One-command startup | `.\start.ps1`, then `/api/health` | `{"status":"ok"}` |
| Demo video | `ffprobe` | H.264, 1280×720, 30 fps, 18 seconds |

## Still requiring human acceptance

- Three genuine learning sessions with private course material
- A real answer request against the user's chosen AI account and model
- Public GitHub repository and `v1.0.0` release

These items are not represented as complete by demo data or mocked model responses.
