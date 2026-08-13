# CiteMind v0.1.7 - original formula evidence

CiteMind now pairs normalized citation text with a sharp crop from the original PDF page. This keeps legacy lecture formulas readable even when an embedded font has no usable Unicode map: unambiguous `SymbolMT` operators and Greek letters are decoded for retrieval, uncertain glyphs are never guessed, and the original visual remains one click away.

The split workspace now keeps both panel headers and the complete PDF page inside the available height. Opening a citation resets the reading position, navigates to the cited page, and highlights the surrounding evidence without inheriting a previous scroll offset.

Chinese retrieval now weights rare course concepts above generic two-character fragments. On the seven-document, 222-page private tutorial set, the direct point-acceleration page moved from rank 9 to rank 2 and entered the default evidence window.

Validation: 25 focused backend checks, a clean dependency install, a production frontend build, 30/30 public bilingual retrieval questions, full reindex of all 222 private pages, alternate-port startup, and production-browser inspections of PDF page 27, rendered AI LaTeX, citation prose, rapid course switching, and the original-page formula preview. The committed screenshot uses only the self-authored CC0 demo PDF; private course files and extracted content remain ignored.

This remains a v0.1 engineering candidate. The v1.0 gate still requires a real lecture/notes/paper source mix and a clean AI course-wide comparison session.
