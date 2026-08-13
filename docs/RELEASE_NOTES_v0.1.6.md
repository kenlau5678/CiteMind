# CiteMind v0.1.6 — fit PDF pages to the viewer

PDF pages now scale to the available reading-pane width instead of using a fixed 1.35× scale. The viewer observes width changes and rerenders the page and citation highlights at the same responsive scale.

At a 1280×720 viewport, the test PDF rendered as a 479 px canvas inside a 535 px reading pane. Both page edges were visible and the pane had no horizontal overflow.

The focused backend suite passes 23 checks and the production frontend builds successfully.
