# CiteMind v0.1.3 — real API validation candidate

This candidate is the first version tested end-to-end against the configured real AI service using only the self-authored public demo material.

## Real API evidence

- English supported answer completed in 14.02 seconds with one valid citation to PDF page 8.
- A question absent from the material returned `insufficient=true` with zero citations.
- A naturally rephrased Chinese question returned a Chinese answer with one valid citation to PDF page 5.
- A real provider disconnect became a controlled 502 after the error path was fixed.

## Reliability fixes

- Chinese bigram overlap joins FTS5 and semantic retrieval without lowering the semantic threshold.
- A valid model citation array can repair a completely omitted inline marker; conflicting markers still fail closed.
- Network transport errors no longer escape as internal server errors.
- The Chinese demo PDF now extracts standard Unicode with zero CJK compatibility characters.

## Automated evidence

- **21/21** focused backend checks pass.
- **30/30** bilingual questions retrieve the correct PDF page in the top five.
- Production frontend build passes.
- All five final Chinese PDF pages pass visual rendering review.

Three private real-course learning sessions and explicit authorization for public GitHub publication remain required before v1.0.0.
