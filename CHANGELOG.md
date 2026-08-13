# Changelog

## 0.1.5 - 2026-08-13

### Added

- Rendered inline and display LaTeX in AI answers with KaTeX.
- Supported subscripts, superscripts, fractions, roots, integrals, and matrix environments.
- Accepted `\\( ... \\)`, `\\[ ... \\]`, `$ ... $`, and `$$ ... $$` delimiters.

### Validated

- Six formulas and three display blocks rendered in the production UI with no browser errors.
- 23 focused backend checks and a production frontend build.

## 0.1.4 - 2026-08-13

### Fixed

- Added nearby-page context so a retrieved section heading can bring its adjacent explanation into the AI evidence set.
- Prioritized equation-bearing Chinese pages for questions that name a specific formula.
- Strengthened the evidence prompt against using contents pages as formula proof or double-counting compact and expanded expressions.
- Highlighted short Chinese PDF text fragments with local two-character terms.

### Validated

- 23 focused backend checks and a production frontend build
- Seven private tutorial PDFs, 222/222 pages with selectable text
- Three study sessions with every displayed citation opened in the PDF viewer
- Document-scoped revision session: 3/3 useful answers, 6/6 citations on direct evidence pages
- Course-wide comparison session recorded as partial because broad questions still admitted weak outline citations and one incorrect synthesis

## 0.1.3 - 2026-08-13

### Fixed

- Added local Chinese bigram retrieval so natural rephrasings do not depend on SQLite's whole-string CJK tokenization.
- Preserved strict semantic thresholds while admitting sufficiently overlapping Chinese evidence.
- Converted chat transport disconnects into controlled 502 responses instead of raw 500 errors.
- Repaired a missing inline marker when the model returns a valid citation array but omits `[n]` in the answer text.
- Switched the Chinese demo PDF to a font with standard Unicode extraction instead of compatibility ideographs.

### Validated

- 21 focused backend checks
- Real English answer: 14.02 seconds, one verified citation to PDF page 8
- Real insufficient-evidence answer: zero citations and `insufficient=true`
- Real Chinese rephrased answer: Chinese response with one verified citation to PDF page 5

## 0.1.2 - 2026-08-13

### Fixed

- Rejected document scopes that belong to another course before retrieval.
- Closed PDF handles before rejecting files over the 200-page limit.
- Removed uploaded originals after corrupt-PDF, page-limit, and embedding failures.
- Split adjacent Chinese sentences without requiring whitespace after punctuation.

### Added

- Self-authored five-page Chinese demo course with ten annotated questions.
- Bilingual retrieval evaluation across English and Chinese documents in one course.

### Validated

- 19 focused backend checks
- 30/30 bilingual top-five page recall

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
