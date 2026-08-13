# CiteMind v0.1.2 — bilingual isolation release candidate

This candidate adds direct evidence for Chinese retrieval and closes failure paths that could leave an unindexed PDF on disk.

## Changes since v0.1.1

- Failed uploads remove the original file after corrupt-PDF, page-limit, or local-embedding errors.
- PDF handles close before a file over 200 pages is rejected on Windows.
- A document scope from another course is rejected before retrieval.
- Adjacent Chinese sentences split correctly without spaces after Chinese punctuation.
- A self-authored Chinese course and ten annotated Chinese questions join the English benchmark.

## Evidence

- **19/19** focused backend checks pass.
- **30/30** combined English and Chinese questions retrieve the correct PDF page in the top five.
- The bilingual documents are indexed in the same course during evaluation.
- Production frontend build still passes.

This remains a local release candidate. A real API call, three private course sessions, and explicit authorization for public GitHub publication are still required before v1.0.0.
