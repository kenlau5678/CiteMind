# CiteMind v0.1.8

CiteMind v0.1.8 makes course libraries easier to organize and keeps evidence concise.

## Highlights

- Drag any source card to choose its reading order; the order survives a refresh.
- A translucent insertion card previews the destination before drop.
- Left and right arrow keys remain available as an accessible reorder fallback.
- Multiple retrieved chunks from one PDF page now become one evidence item and one citation card.

## Verification

- 46 backend tests pass.
- The production frontend build passes.
- Browser acceptance covers drag, persisted order after refresh, keyboard restoration, and citation deduplication.
- A clean source archive installs and starts without an AI key; PDF library features remain available.
- Four fresh 30-question mechanics runs and their failure analysis are summarized in `docs/evaluations/theoretical_mechanics_30_stability.md`.

## Known limits

- Windows-first local application.
- PDF only, one local user, no cloud synchronization.
- AI answers require a configured compatible API key.
