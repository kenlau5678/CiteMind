# Changelog

## Unreleased

### Added

- Decode additional font-gated legacy `Symbol` operators used in mechanics PDFs, including inequalities, sums, integrals, dot products, angles, derivatives, and degrees.
- Cover both successful operator decoding and ambiguous-font refusal with focused regression tests.

### Validated

- 27 focused backend checks, a production frontend build, and 30/30 public bilingual retrieval questions.
- Nineteen additional private mechanics PDFs across statics, dynamics, and analytical mechanics, bringing the local course to 26 documents and 655 selectable-text pages.
- 7/7 added mechanics questions retrieved their expected page in the top five; every expected result ranked first or second.
- 12/12 complete-course extension questions retrieved their expected page in the top five; three real AI answers returned valid chapter citations.
- Production-browser citation previews loaded as original-page images, and the friction-angle citation opened page 4/25 with no browser errors.

## 0.1.7 - 2026-08-13

### Added

- Show a sharp original-PDF evidence strip inside every citation card.
- Decode unambiguous legacy `SymbolMT` operators and Greek letters, plus `MT-Extra` dot accents, before indexing.
- Weight rare Chinese concept bigrams above generic fragments during local retrieval.

### Fixed

- Keep both split-view panels within their grid row so headers and the complete PDF page are never vertically clipped.
- Reset the PDF reading position when a citation opens another document or page.
- Remove private-use glyphs from citation prose when the source font cannot be decoded safely.
- Allow one-command startup on an alternate `CITEMIND_PORT` and clarify the useful no-key reading mode.
- Finish in-flight PDF.js rendering before releasing a switched panel, preventing harmless `AbortError` console noise.

### Validated

- 25 focused backend checks and a production frontend build.
- Seven private tutorial PDFs, 222/222 pages reindexed with sorted page text and local embeddings.
- The real point-acceleration evidence page moved from rank 9 to rank 2 and entered the default evidence window.
- The checked formula page dropped from 37 private-use glyphs to zero; its original rendering remains visible beside the normalized text.
- Production browser check at 1280×720 showed the complete PDF page, synchronized page 27 navigation, rendered AI math, and the original-page formula preview.
- The committed formula-evidence screenshot uses only the self-authored CC0 demo course; private tutorial pages remain untracked.

## 0.1.6 - 2026-08-13

### Fixed

- Fit PDF pages to the reading pane instead of rendering at a fixed scale.
- Recalculate the PDF scale when the split view or window width changes.
- Keep citation highlights aligned with the resized PDF page.

### Validated

- At 1280×720, the 479 px PDF canvas fits inside the 535 px reading pane with no horizontal overflow.
- 23 focused backend checks and a production frontend build.

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
