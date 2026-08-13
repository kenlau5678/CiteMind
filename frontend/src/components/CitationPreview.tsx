import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import PdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?worker";

const BAD_GLYPHS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\ue000-\uf8ff\ufffd]/;

export function cleanCitationText(text: string) {
  return text.replace(new RegExp(BAD_GLYPHS.source, "g"), " ").replace(/\s+/g, " ").trim();
}

export function hasUnmappedFormulaGlyphs(text: string) {
  return BAD_GLYPHS.test(text);
}

export function citationExcerpt(text: string) {
  const clean = cleanCitationText(text);
  const firstChinese = clean.search(/[\p{Script=Han}]{2}/u);
  return hasUnmappedFormulaGlyphs(text) && firstChinese > 0 ? clean.slice(firstChinese) : clean;
}

function anchorTerms(text: string) {
  const terms: string[] = [];
  for (const sequence of cleanCitationText(text).match(/[\p{Script=Han}]{4,}/gu) ?? []) {
    for (let index = 0; index <= sequence.length - 4; index += 2) terms.push(sequence.slice(index, index + 4));
  }
  terms.push(...(cleanCitationText(text).match(/[A-Za-z][A-Za-z_]{4,}/g) ?? []));
  return terms.slice(0, 40);
}

export function CitationPreview({ documentId, page, content }: { documentId: number; page: number; content: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    const worker = new pdfjs.PDFWorker({ port: new PdfWorker({ type: "module" }) } as never);
    const task = pdfjs.getDocument({ url: `/api/documents/${documentId}/file`, worker });

    const work = task.promise.then(async (pdf) => {
      const pdfPage = await pdf.getPage(page);
      const natural = pdfPage.getViewport({ scale: 1 });
      const viewport = pdfPage.getViewport({ scale: 640 / natural.width });
      const text = await pdfPage.getTextContent();
      const terms = anchorTerms(content);
      const formulaMatches = /[=+−]/.test(content)
        ? text.items.filter((item) => "str" in item && /[=+−]/.test(item.str))
        : [];
      const match = formulaMatches.at(-1)
        ?? text.items.find((item) => "str" in item && terms.some((term) => item.str.includes(term)));
      const transformed = match && "transform" in match
        ? pdfjs.Util.transform(viewport.transform, match.transform)
        : null;

      const pageCanvas = globalThis.document.createElement("canvas");
      pageCanvas.width = Math.ceil(viewport.width);
      pageCanvas.height = Math.ceil(viewport.height);
      const context = pageCanvas.getContext("2d");
      if (!context) return;
      await pdfPage.render({ canvas: pageCanvas, canvasContext: context, viewport }).promise;
      if (cancelled) return;

      const cropHeight = Math.min(210, pageCanvas.height);
      const anchorY = transformed?.[5] ?? pageCanvas.height * 0.25;
      const cropTop = Math.max(0, Math.min(pageCanvas.height - cropHeight, anchorY - 80));
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = pageCanvas.width;
      canvas.height = cropHeight;
      canvas.getContext("2d")?.drawImage(
        pageCanvas, 0, cropTop, pageCanvas.width, cropHeight,
        0, 0, pageCanvas.width, cropHeight,
      );
      setReady(true);
    }).catch(() => undefined);

    return () => {
      cancelled = true;
      void work.finally(() => { void task.destroy().finally(() => worker.destroy()); });
    };
  }, [content, documentId, page]);

  return (
    <span className={ready ? "citation-preview ready" : "citation-preview"} aria-label="Original PDF evidence preview">
      <span className="citation-preview-label">{/[=+−]|[˙¨α-ω]/u.test(content) ? "原页公式预览" : "原页证据预览"}</span>
      <canvas ref={canvasRef} />
    </span>
  );
}
