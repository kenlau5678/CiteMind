import { useEffect, useRef } from "react";
import renderMathInElement from "katex/contrib/auto-render";

export function MathText({ children }: { children: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    renderMathInElement(ref.current, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
      trust: false,
    });
  }, [children]);

  return <div className="math-text" ref={ref}>{children}</div>;
}
