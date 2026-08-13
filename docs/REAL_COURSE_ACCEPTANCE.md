# Real-course acceptance

Use one private course that contains at least one lecture, one personal note, and one paper. Do not commit those files or their contents.

Run CiteMind with your configured API key:

```powershell
.\start.ps1
```

Complete the three sessions on different study tasks. For each one, ask at least three questions and click every citation used by an answer.

| Session | Real study task | Questions answered | Correct page citations | Wrong or missing citations | Useful outcome? |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | Locate a forgotten concept | 3 | 7 | 0 | Yes |
| 2 | Compare related lecture chapters | 3 | 8 | 6 | Partial |
| 3 | Resolve a question while revising (current-file scope) | 3 | 6 | 0 | Yes |

Completed on 2026-08-13 and extended to twenty-six private tutorial PDFs (655 selectable-text pages), covering kinematics, statics, particle dynamics, system dynamics, and analytical mechanics. Every displayed citation in the original sessions was opened and its file and page were checked. The extensions added nineteen mechanics retrieval checks, six real cited answers, and browser checks of original-page citation previews. A Chinese citation that initially opened with no highlights was fixed and rechecked with five highlights.

This run does not close the v1 gate: the supplied set contained tutorials only, not the required lecture, personal note, and paper mix. The course-wide comparison session also exposed weak outline-page citations and one incorrect synthesis of equivalent formula forms. Exact private questions, filenames, expected pages, and returned pages remain in an ignored local acceptance record rather than this public document.

The v0.1.7 retrieval follow-up reindexed the original 373 pages with safe legacy-symbol decoding and rare Chinese concept weighting. A previously missed point-acceleration evidence page moved from rank 9 to rank 2. All nineteen added mechanics questions retrieved the intended page in the top five. The material now spans the complete lecture sequence, but it is still a lecture-only set; the mixed-source acceptance course is still required.

## Release gate

Release v1.0 only if all of these are true:

- A new user can complete start → upload → ask → open citation in ten minutes.
- No displayed citation points to a nonexistent file or page.
- Wrong or unsupported claims are recorded as issues, not hidden from the result.
- Private course documents, extracted text, database files, chat logs, and `.env` remain untracked.
- The public demo still scores at least 80% top-five page recall.

If a real session fails, record the exact question, expected file/page, returned file/page, and whether the failure came from extraction, retrieval, or answer generation. Do not add features until that path is fixed.
