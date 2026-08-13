# CiteMind v0.1.5 — typeset AI formulas

AI answers now render inline and display LaTeX with KaTeX. Supported output includes subscripts, superscripts, fractions, roots, integrals, and matrices using standard `\\( ... \\)`, `\\[ ... \\]`, `$ ... $`, or `$$ ... $$` delimiters.

The answer prompt requests explicit LaTeX delimiters, while invalid expressions remain readable as source text instead of breaking the chat. Citation markers and ordinary answer text remain unchanged.

The production UI rendered six representative formulas and three display blocks without browser errors. The focused backend suite passes 23 checks and the production frontend builds successfully.
