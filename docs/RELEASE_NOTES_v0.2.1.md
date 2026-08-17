# CiteMind v0.2.1

CiteMind v0.2.1 makes Knowledge Home exploration visible as it happens and renders structured AI answers correctly.

## Highlights

- Agent status and completed tool steps stream to the browser over one POST request.
- The answer is released progressively after server-side citation validation; citation cards appear only with the verified final result.
- Markdown headings, ordered and unordered lists, emphasis, inline and fenced code, links, blockquotes, and tables now render alongside existing KaTeX formulas.
- Streaming errors return a controlled event and clear the incomplete answer state.

## Verification

- 52 backend tests pass, including event order, answer-delta reconstruction, and final citation metadata.
- The production frontend build passes without adding a Markdown or streaming dependency.
- Browser acceptance observed six Agent steps before completion and a final answer containing headings, emphasis, lists, tables, formulas, and page citations with zero console errors.
