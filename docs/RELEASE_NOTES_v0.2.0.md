# CiteMind v0.2.0

CiteMind v0.2.0 adds a library-wide Knowledge Home and a bounded evidence Agent.

## Highlights

- Ask one question across every uploaded course, lecture, note, and paper.
- See the Agent's visible activity: library searches, exact-page reads, and optional original-page visual inspection.
- Receive one evidence-backed answer with validated PDF-page citations and a grouped map of related courses and materials.
- Open a cross-course citation to switch into the correct course workspace and land on the exact original PDF page.
- Keep the existing course-scoped RAG workspace for focused follow-up questions.

## Safety boundary

- The Agent can only search, read a discovered document page, inspect a discovered page, or finish.
- A run is synchronous, limited to six actions, deduplicates repeated calls, and cannot write to or delete the library.
- The existing citation validator remains the final answer gate.

## Verification

- 51 backend tests pass, including read-only action validation, cross-course citation tests, and focused-evidence window priority.
- The production frontend build passes.
- A real browser run searched the local library, rendered formulas, returned six page citations, and opened the first citation at the correct paper page with zero console errors.
- The existing 30-question bilingual retrieval benchmark remains the public regression gate.

## Known limits

- The Agent does not create a persistent editable knowledge graph.
- Exploration runs are synchronous and use the configured compatible chat API.
- Windows-first, PDF only, one local user, no cloud synchronization.
