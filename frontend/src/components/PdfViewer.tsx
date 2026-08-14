import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
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

type Zoom = "width" | "page" | number;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 3;
const readingKey = (documentId: number) => `citemind:pdf:${documentId}`;
const clamp = (value: number, minimum: number, maximum: number) => Math.min(Math.max(value, minimum), maximum);

function savedReading(documentId: number) {
  try { return JSON.parse(localStorage.getItem(readingKey(documentId)) ?? "{}"); }
  catch { return {}; }
}

export function savedPdfPage(documentId: number, pageCount: number) {
  const page = Number(savedReading(documentId).page);
  return Number.isFinite(page) ? clamp(Math.round(page), 1, Math.max(pageCount, 1)) : 1;
}

function savedPdfZoom(documentId: number): Zoom {
  const zoom = savedReading(documentId).zoom;
  return zoom === "width" || zoom === "page" || (typeof zoom === "number" && zoom >= MIN_ZOOM && zoom <= MAX_ZOOM) ? zoom : "width";
}

export function PdfViewer({ documentId, title, page, highlight, pageCount, onPageChange }: Props) {
  const viewerRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [availableSize, setAvailableSize] = useState({ width: 0, height: 0 });
  const [zoom, setZoom] = useState<Zoom>(() => savedPdfZoom(documentId));
  const [renderScale, setRenderScale] = useState(1);
  const [pageDraft, setPageDraft] = useState(String(page));
  const [fullscreen, setFullscreen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    const measure = () => setAvailableSize({
      width: Math.max(container.clientWidth - 56, 1),
      height: Math.max(container.clientHeight - 56, 1),
    });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => setPageDraft(String(page)), [page]);

  useEffect(() => {
    try { localStorage.setItem(readingKey(documentId), JSON.stringify({ page, zoom })); }
    catch { /* Reading still works when browser storage is unavailable. */ }
  }, [documentId, page, zoom]);

  useEffect(() => {
    const update = () => setFullscreen(document.fullscreenElement === viewerRef.current);
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTop = 0;
    container.scrollLeft = 0;
  }, [documentId, page]);

  useEffect(() => {
    if (!availableSize.width || !availableSize.height) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    const worker = new pdfjs.PDFWorker({ port: new PdfWorker({ type: "module" }) } as never);
    const task = pdfjs.getDocument({ url: `/api/documents/${documentId}/file`, worker });
    const work = task.promise.then(async (pdf) => {
      const pdfPage = await pdf.getPage(page);
      const natural = pdfPage.getViewport({ scale: 1 });
      const widthScale = availableSize.width / natural.width;
      const scale = clamp(
        zoom === "width" ? widthScale : zoom === "page" ? Math.min(widthScale, availableSize.height / natural.height) : zoom,
        MIN_ZOOM,
        MAX_ZOOM,
      );
      const viewport = pdfPage.getViewport({ scale });
      if (!cancelled) setRenderScale(scale);
      const canvas = canvasRef.current;
      if (!canvas || cancelled) return;
      const context = canvas.getContext("2d");
      if (!context) return;
      const outputScale = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      await pdfPage.render({
        canvas,
        canvasContext: context,
        viewport,
        transform: outputScale === 1 ? undefined : [outputScale, 0, 0, outputScale, 0, 0],
      }).promise;

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
      void work.finally(() => { void task.destroy().finally(() => worker.destroy()); });
    };
  }, [documentId, page, highlight, availableSize, zoom]);

  function commitPage(event?: FormEvent) {
    event?.preventDefault();
    const next = Number(pageDraft);
    if (Number.isFinite(next)) onPageChange(clamp(Math.round(next), 1, Math.max(pageCount, 1)));
    else setPageDraft(String(page));
  }

  function changeZoom(amount: number) {
    setZoom(clamp(Math.round((renderScale + amount) * 100) / 100, MIN_ZOOM, MAX_ZOOM));
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await viewerRef.current?.requestFullscreen();
    } catch { setError("Fullscreen is not available in this browser."); }
  }

  return (
    <section className="viewer-panel" ref={viewerRef}>
      <header className="panel-header viewer-header">
        <div>
          <span className="eyebrow">Reading</span>
          <strong title={title}>{title}</strong>
        </div>
        <nav className="page-controls" aria-label="PDF controls">
          <button title="Previous page" aria-label="Previous page" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>←</button>
          <form className="page-jump" onSubmit={commitPage}>
            <input aria-label="Page number" type="number" min="1" max={pageCount} value={pageDraft} onChange={(event) => setPageDraft(event.target.value)} onBlur={() => commitPage()} />
            <span>/ {pageCount}</span>
          </form>
          <button title="Next page" aria-label="Next page" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>→</button>
          <button title="Zoom out" aria-label="Zoom out" onClick={() => changeZoom(-0.15)}>−</button>
          <span className="zoom-value">{Math.round(renderScale * 100)}%</span>
          <button title="Zoom in" aria-label="Zoom in" onClick={() => changeZoom(0.15)}>+</button>
          <button className={zoom === "width" ? "active" : ""} title="Fit page width" aria-label="Fit page width" onClick={() => setZoom("width")}>↔</button>
          <button className={zoom === "page" ? "active" : ""} title="Fit whole page" aria-label="Fit whole page" onClick={() => setZoom("page")}>□</button>
          <button title={fullscreen ? "Exit full screen" : "Full screen"} aria-label={fullscreen ? "Exit full screen" : "Full screen"} onClick={toggleFullscreen}>⛶</button>
        </nav>
      </header>
      <div className="pdf-scroll" ref={scrollRef}>
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
