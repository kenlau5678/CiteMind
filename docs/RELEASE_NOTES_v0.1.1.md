# CiteMind v0.1.1 — reliability release candidate

This candidate tightens the two promises at the center of CiteMind: an answer is scoped to the selected material, and a supported answer is verifiable.

## Changes since v0.1.0

- Supported answers must contain at least one server-validated inline citation.
- Evidence-insufficient answers use an explicit `insufficient` state and must contain no citations.
- Changing answer scope clears the old conversation before the new scope becomes active.
- Keyword retrieval ignores common English question words that could create weak matches.
- Focused backend checks increased from 9 to 14.

The bundled retrieval benchmark remains **20/20 top-five page recall (100%)** after the ranking change.

This remains a local release candidate. A real API call, three private course sessions, and public GitHub publication are still required before v1.0.0.
