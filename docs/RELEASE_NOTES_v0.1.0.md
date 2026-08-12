# CiteMind v0.1.0 — local release candidate

CiteMind v0.1.0 is the first complete engineering candidate for evidence-first course Q&A. It is ready for private, real-course acceptance testing but is intentionally not labelled v1.0.0 yet.

## Highlights

- Course libraries for lecture notes, student notes, and papers
- Text-based PDF ingestion with stable PDF-page provenance
- Local multilingual embeddings plus SQLite FTS5 hybrid retrieval
- AI answers constrained to retrieved evidence
- Server validation of every citation identifier
- Click-through PDF page navigation and evidence highlighting
- Original files, extracted text, embeddings, and history stored locally

## Validated

- 9/9 focused backend tests
- 20/20 top-five page recall on the bundled demo benchmark
- 3.47-second warm-cache indexing of a generated 100-page text PDF
- Production frontend build and one-command Windows startup
- Browser-tested citation navigation with no console errors

## Before v1.0.0

- Configure and test a real OpenAI-compatible API account
- Complete three private real-course learning sessions
- Resolve any failures found by those sessions
- Publish the repository and create the public GitHub release

See [VALIDATION.md](VALIDATION.md) and [REAL_COURSE_ACCEPTANCE.md](REAL_COURSE_ACCEPTANCE.md) for the evidence and release gate.

