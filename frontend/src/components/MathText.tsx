import { useEffect, useRef } from "react";
import renderMathInElement from "katex/contrib/auto-render";

export function MathText({ children }: { children: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const cleanText = children.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "");

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
  }, [cleanText]);

  return <div className="math-text" ref={ref}>{cleanText}</div>;
}
