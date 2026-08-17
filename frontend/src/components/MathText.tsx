import { createElement, Fragment, type ReactNode, useEffect, useMemo, useRef } from "react";
import renderMathInElement from "katex/contrib/auto-render";

const mathPattern = /(\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g;
const tableDivider = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/;
const blockStart = /^(#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s+|```|\\\[|\$\$)/;

function inline(text: string, key: string): ReactNode[] {
  return text.split(mathPattern).flatMap((part, index) => {
    if (/^(\\\[|\\\(|\$\$|\$)/.test(part)) return <Fragment key={`${key}-math-${index}`}>{part}</Fragment>;
    return part.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)\s]+\))/g).map((token, tokenIndex) => {
      const tokenKey = `${key}-${index}-${tokenIndex}`;
      if (token.startsWith("**") && token.endsWith("**")) return <strong key={tokenKey}>{token.slice(2, -2)}</strong>;
      if (token.startsWith("`") && token.endsWith("`")) return <code key={tokenKey}>{token.slice(1, -1)}</code>;
      const link = token.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
      if (link) return <a key={tokenKey} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>;
      return <Fragment key={tokenKey}>{token}</Fragment>;
    });
  });
}

function tableCells(line: string) {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}

function markdown(text: string) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }

    if (line.trim().startsWith("```")) {
      const language = line.trim().slice(3);
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) code.push(lines[index++]);
      index += index < lines.length ? 1 : 0;
      blocks.push(<pre key={`code-${index}`}><code className={language ? `language-${language}` : undefined}>{code.join("\n")}</code></pre>);
      continue;
    }

    if (line.trim() === "\\[" || line.trim() === "$$") {
      const closing = line.trim() === "\\[" ? "\\]" : "$$";
      const formula = [line];
      index += 1;
      while (index < lines.length) {
        formula.push(lines[index]);
        if (lines[index++].trim() === closing) break;
      }
      blocks.push(<div className="markdown-math" key={`math-${index}`}>{formula.join("\n")}</div>);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 1, 6);
      blocks.push(createElement(`h${level}`, { key: `heading-${index}` }, inline(heading[2], `heading-${index}`)));
      index += 1;
      continue;
    }

    if (index + 1 < lines.length && line.includes("|") && tableDivider.test(lines[index + 1])) {
      const headers = tableCells(line);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) rows.push(tableCells(lines[index++]));
      blocks.push(
        <div className="markdown-table-wrap" key={`table-${index}`}><table><thead><tr>
          {headers.map((cell, cellIndex) => <th key={cellIndex}>{inline(cell, `th-${index}-${cellIndex}`)}</th>)}
        </tr></thead><tbody>
          {rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{inline(cell, `td-${index}-${rowIndex}-${cellIndex}`)}</td>)}</tr>)}
        </tbody></table></div>,
      );
      continue;
    }

    const listMatch = line.match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);
    if (listMatch) {
      const ordered = /^\d/.test(listMatch[1]);
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[1]) !== ordered) break;
        items.push(item[2]);
        index += 1;
      }
      const List = ordered ? "ol" : "ul";
      blocks.push(<List key={`list-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inline(item, `li-${index}-${itemIndex}`)}</li>)}</List>);
      continue;
    }

    if (/^>\s+/.test(line)) {
      const quote: string[] = [];
      while (index < lines.length && /^>\s+/.test(lines[index])) quote.push(lines[index++].replace(/^>\s+/, ""));
      blocks.push(<blockquote key={`quote-${index}`}>{inline(quote.join(" "), `quote-${index}`)}</blockquote>);
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !blockStart.test(lines[index]) && !(index + 1 < lines.length && tableDivider.test(lines[index + 1]))) {
      paragraph.push(lines[index++].trim());
    }
    blocks.push(<p key={`paragraph-${index}`}>{inline(paragraph.join(" "), `paragraph-${index}`)}</p>);
  }
  return blocks;
}

export function MathText({ children }: { children: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const cleanText = children.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "");
  const content = useMemo(() => markdown(cleanText), [cleanText]);

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

  return <div className="math-text" ref={ref}>{content}</div>;
}
