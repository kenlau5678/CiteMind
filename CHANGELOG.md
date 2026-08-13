# Changelog

## 0.1.1 - 2026-08-13

### Fixed

- A supported AI answer must now contain at least one verified inline citation.
- Evidence-insufficient answers use an explicit protocol state and cannot carry contradictory citations.
- Changing between course-wide and single-document scope always clears the previous conversation.
- Common English question words no longer create weak keyword matches.

### Validated

- 14 focused backend checks
- 20/20 top-five page recall after the retrieval change

## 0.1.0 - 2026-08-12

First working MVP of CiteMind.

### Added

- Local course workspaces for lectures, notes, and papers
- Page-preserving PDF ingestion with local multilingual embeddings
- SQLite FTS5 and vector hybrid retrieval
- Evidence-only AI answers with server-validated citation numbers
- PDF page navigation and evidence highlighting
- Local chat history and privacy-preserving deletion
- Self-authored demo course and 20-question retrieval benchmark
- Focused backend tests, production frontend build, and CI workflow

### Known limitations

- Text-based PDFs only; no OCR
- Windows and Chromium browsers are the verified environment
- One OpenAI-compatible chat provider and one local user
- Real-course acceptance testing and the v1.0 release remain pending
