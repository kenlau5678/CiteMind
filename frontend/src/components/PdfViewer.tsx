import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import PdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?worker";

type Props = {
  documentId: number;
  title: string;
  page: number;
  highlight?: string;
  pageCount: number;
  onPageChange: (page: number) => void;
};

export function PdfViewer({ documentId, title, page, highlight, pageCount, onPageChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const worker = new pdfjs.PDFWorker({ port: new PdfWorker({ type: "module" }) } as never);
    const task = pdfjs.getDocument({ url: `/api/documents/${documentId}/file`, worker });
    task.promise.then(async (pdf) => {
      const pdfPage = await pdf.getPage(page);
      const viewport = pdfPage.getViewport({ scale: 1.35 });
      const canvas = canvasRef.current;
      if (!canvas || cancelled) return;
      const context = canvas.getContext("2d");
      if (!context) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      await pdfPage.render({ canvas, canvasContext: context, viewport }).promise;

      const overlay = overlayRef.current;
      if (overlay) {
        overlay.innerHTML = "";
        overlay.style.width = `${viewport.width}px`;
        overlay.style.height = `${viewport.height}px`;
        if (highlight) {
          const text = await pdfPage.getTextContent();
          const terms = (highlight.toLowerCase().match(/[a-z0-9]{5,}|[\p{Script=Han}]{2,}/gu) ?? [])
            .flatMap((term) => /\p{Script=Han}/u.test(term)
              ? Array.from({ length: term.length - 1 }, (_, index) => term.slice(index, index + 2))
              : [term])
            .slice(0, 24);
          text.items.forEach((raw) => {
            if (!("str" in raw) || !terms.some((term) => raw.str.toLowerCase().includes(term))) return;
            const tx = pdfjs.Util.transform(viewport.transform, raw.transform);
            const marker = document.createElement("mark");
            marker.className = "pdf-highlight";
            marker.style.left = `${tx[4]}px`;
            marker.style.top = `${tx[5] - Math.abs(tx[3])}px`;
            marker.style.width = `${Math.max(raw.width * viewport.scale, 20)}px`;
            marker.style.height = `${Math.max(Math.abs(tx[3]), 12)}px`;
            overlay.appendChild(marker);
          });
        }
      }
      if (!cancelled) setLoading(false);
    }).catch((reason) => {
      if (!cancelled) setError(reason instanceof Error ? reason.message : "Could not open PDF");
    });
    return () => {
      cancelled = true;
      void task.destroy().finally(() => worker.destroy());
    };
  }, [documentId, page, highlight]);

  return (
    <section className="viewer-panel">
      <header className="panel-header viewer-header">
        <div>
          <span className="eyebrow">Reading</span>
          <strong title={title}>{title}</strong>
        </div>
        <nav className="page-controls" aria-label="PDF page controls">
          <button aria-label="Previous page" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>←</button>
          <span>{page} / {pageCount}</span>
          <button aria-label="Next page" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>→</button>
        </nav>
      </header>
      <div className="pdf-scroll">
        {loading && <div className="viewer-status">Rendering page…</div>}
        {error && <div className="error-card">{error}</div>}
        <div className="pdf-page" hidden={!!error}>
          <canvas ref={canvasRef} />
          <div className="pdf-overlay" ref={overlayRef} aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}
