# Real-course acceptance

Use one private course that contains at least one lecture, one personal note, and one paper. Do not commit those files or their contents.

Run CiteMind with your configured API key:

```powershell
.\start.ps1
```

Complete the three sessions on different study tasks. For each one, ask at least three questions and click every citation used by an answer.

| Session | Real study task | Questions answered | Correct page citations | Wrong or missing citations | Useful outcome? |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | Locate a forgotten concept |  |  |  |  |
| 2 | Compare a lecture with a paper |  |  |  |  |
| 3 | Resolve a question while revising |  |  |  |  |

## Release gate

Release v1.0 only if all of these are true:

- A new user can complete start → upload → ask → open citation in ten minutes.
- No displayed citation points to a nonexistent file or page.
- Wrong or unsupported claims are recorded as issues, not hidden from the result.
- Private course documents, extracted text, database files, chat logs, and `.env` remain untracked.
- The public demo still scores at least 80% top-five page recall.

If a real session fails, record the exact question, expected file/page, returned file/page, and whether the failure came from extraction, retrieval, or answer generation. Do not add features until that path is fixed.

