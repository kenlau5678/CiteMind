import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { MathText } from "./components/MathText";
import { PdfViewer, savedPdfPage } from "./components/PdfViewer";
import { CitationPreview } from "./components/CitationPreview";
import type { Citation, Course, Document, Message } from "./types";

const kindNames = { lecture: "Lecture", notes: "Notes", paper: "Paper" };

export default function App() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeDocument, setActiveDocument] = useState<Document | null>(null);
  const [scopeDocumentId, setScopeDocumentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [page, setPage] = useState(1);
  const [highlight, setHighlight] = useState<string>();
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [draggedDocumentId, setDraggedDocumentId] = useState<number | null>(null);
  const [aiConfigured, setAiConfigured] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const selectedCourse = courses.find((course) => course.id === courseId);
  const readyDocuments = documents.filter((document) => document.status === "ready");
  const hasProcessingDocuments = documents.some((document) => document.status === "processing");

  async function refreshCourses(selectFirst = false) {
    const data = await api.courses();
    setCourses(data);
    if ((selectFirst || courseId === null) && data[0]) setCourseId(data[0].id);
  }

  useEffect(() => {
    refreshCourses(true).catch(showError);
    api.config().then((config) => setAiConfigured(config.ai_configured)).catch(showError);
  }, []);
  useEffect(() => {
    if (!courseId) return;
    Promise.all([api.documents(courseId), api.messages(courseId)]).then(([docs, history]) => {
      setDocuments(docs);
      setMessages(history);
      const next = docs.find((item) => item.id === activeDocument?.id) ?? docs[0] ?? null;
      setActiveDocument(next);
      setPage(next ? savedPdfPage(next.id, next.page_count) : 1);
      setHighlight(undefined);
    }).catch(showError);
  }, [courseId]);
  useEffect(() => {
    if (!courseId || !hasProcessingDocuments) return;
    const timer = window.setInterval(() => {
      api.documents(courseId).then((docs) => {
        setDocuments(docs);
        setActiveDocument((current) => docs.find((item) => item.id === current?.id) ?? docs[0] ?? null);
      }).catch(showError);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [courseId, hasProcessingDocuments]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  function showError(reason: unknown) {
    setError(reason instanceof Error ? reason.message : "Something went wrong");
  }

  async function createCourse() {
    const name = window.prompt("Course name");
    if (!name?.trim()) return;
    try {
      const course = await api.createCourse(name.trim());
      await refreshCourses();
      setCourseId(course.id);
    } catch (reason) { showError(reason); }
  }

  async function changeScope(value: string) {
    if (!courseId) return;
    const next = value === "course" ? null : Number(value);
    if (next === scopeDocumentId) return;
    try {
      await api.clearMessages(courseId);
      setScopeDocumentId(next);
      setMessages([]);
    } catch (reason) { showError(reason); }
  }

  async function submitQuestion(event: FormEvent) {
    event.preventDefault();
    if (!courseId || !question.trim() || busy) return;
    const text = question.trim();
    setQuestion("");
    setError("");
    setMessages((current) => [...current, { role: "user", content: text, citations: [] }]);
    setBusy(true);
    try {
      const result = await api.ask(courseId, text, scopeDocumentId);
      setMessages((current) => [...current, { role: "assistant", content: result.answer, citations: result.citations, vision_used: result.vision_used }]);
    } catch (reason) {
      setMessages((current) => current.slice(0, -1));
      setQuestion(text);
      showError(reason);
    } finally { setBusy(false); }
  }

  function openCitation(citation: Citation) {
    const document = documents.find((item) => item.id === citation.document_id);
    if (!document) return;
    setActiveDocument(document);
    setPage(citation.page_number);
    setHighlight(citation.content);
  }

  function openDocument(document: Document) {
    setActiveDocument(document);
    setPage(savedPdfPage(document.id, document.page_count));
    setHighlight(undefined);
  }

  async function removeDocument(document: Document) {
    if (!window.confirm(`Delete “${document.title}”? Its index and this course's chat history will also be deleted.`)) return;
    try {
      await api.deleteDocument(document.id);
      if (!courseId) return;
      const docs = await api.documents(courseId);
      setDocuments(docs);
      setMessages([]);
      setActiveDocument(docs[0] ?? null);
      setScopeDocumentId(null);
      await refreshCourses();
    } catch (reason) { showError(reason); }
  }

  async function retryDocument(document: Document) {
    try {
      const retried = await api.retryDocument(document.id);
      setDocuments((current) => current.map((item) => item.id === retried.id ? retried : item));
      setActiveDocument((current) => current?.id === retried.id ? retried : current);
    } catch (reason) { showError(reason); }
  }

  async function moveDocument(documentId: number, targetId: number) {
    if (!courseId || documentId === targetId) return;
    const previous = documents;
    const from = previous.findIndex((item) => item.id === documentId);
    const to = previous.findIndex((item) => item.id === targetId);
    if (from < 0 || to < 0) return;
    const next = [...previous];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setDocuments(next);
    try {
      await api.reorderDocuments(courseId, next.map((item) => item.id));
    } catch (reason) {
      setDocuments(previous);
      showError(reason);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">C</span><span>CiteMind<small>Verify every answer.</small></span></div>
        <div className="sidebar-heading"><span>Your courses</span><button onClick={createCourse} aria-label="Create course">＋</button></div>
        <nav className="course-list">
          {courses.map((course) => (
            <button key={course.id} className={course.id === courseId ? "course active" : "course"} onClick={() => setCourseId(course.id)}>
              <span className="course-icon">{course.name.slice(0, 1).toUpperCase()}</span>
              <span><strong>{course.name}</strong><small>{course.document_count ?? 0} sources</small></span>
            </button>
          ))}
          {!courses.length && <p className="empty-hint">Create your first course to begin.</p>}
        </nav>
        <footer><span className="privacy-dot" /> Local library · AI for relevant excerpts</footer>
      </aside>

      {!selectedCourse ? (
        <section className="welcome">
          <span className="hero-mark">C</span>
          <p className="eyebrow">Your evidence-first study space</p>
          <h1>Ask your notes.<br />Verify every answer.</h1>
          <p>Bring lectures, notes, and papers together. CiteMind answers from your material and takes you back to the exact page.</p>
          <button className="primary" onClick={createCourse}>Create your first course</button>
        </section>
      ) : (
        <section className="workspace">
          <header className="workspace-header">
            <div><span className="eyebrow">Course library</span><h1>{selectedCourse.name}</h1></div>
            <button className="primary" onClick={() => setShowUpload(true)}>＋ Add PDF</button>
          </header>

          <div className="source-strip">
            {documents.map((document) => (
              <article
                key={document.id}
                draggable
                className={`${activeDocument?.id === document.id ? "source-card active" : "source-card"} ${document.status} ${draggedDocumentId === document.id ? "dragging" : ""}`}
                onClick={() => openDocument(document)}
                onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", String(document.id)); setDraggedDocumentId(document.id); }}
                onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }}
                onDrop={(event) => { event.preventDefault(); const sourceId = Number(event.dataTransfer.getData("text/plain")) || draggedDocumentId; if (sourceId) void moveDocument(sourceId, document.id); setDraggedDocumentId(null); }}
                onDragEnd={() => setDraggedDocumentId(null)}
              >
                <span className={`kind ${document.kind}`}>{kindNames[document.kind]}</span>
                <button
                  className="drag-handle"
                  aria-label={`Reorder ${document.title}. Use left and right arrow keys.`}
                  title="Drag to reorder"
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => {
                    const offset = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
                    const target = documents[documents.findIndex((item) => item.id === document.id) + offset];
                    if (offset && target) { event.preventDefault(); void moveDocument(document.id, target.id); }
                  }}
                >⠿</button>
                <strong title={document.title}>{document.title}</strong>
                {document.status === "processing" && <small className="document-progress">OCR {document.processed_pages} / {document.page_count} pages<progress aria-label={`OCR progress for ${document.title}`} value={document.processed_pages} max={document.page_count} /></small>}
                {document.status === "failed" && <small className="document-failed" title={document.error ?? undefined}>{document.processed_pages < document.page_count ? `Paused at page ${document.processed_pages + 1}` : "Needs attention"}</small>}
                {document.status === "ready" && <small>{document.page_count} pages</small>}
                {document.status === "failed" && <button className="retry-document" aria-label={`Retry ${document.title}`} onClick={(event) => { event.stopPropagation(); retryDocument(document); }}>Retry</button>}
                <button className="quiet-delete" disabled={document.status === "processing"} aria-label={`Delete ${document.title}`} onClick={(event) => { event.stopPropagation(); removeDocument(document); }}>×</button>
              </article>
            ))}
            {!documents.length && <button className="empty-source" onClick={() => setShowUpload(true)}>Drop in a PDF to start your library →</button>}
          </div>

          {!aiConfigured && <div className="config-notice">AI question answering is not configured. Copy <code>.env.example</code> to <code>.env</code> and add your API key.</div>}

          <div className="split-view">
            {activeDocument ? (
              <PdfViewer key={activeDocument.id} documentId={activeDocument.id} title={activeDocument.title} page={page} pageCount={activeDocument.page_count} highlight={highlight} onPageChange={(next) => { setPage(next); setHighlight(undefined); }} />
            ) : <section className="viewer-panel blank-panel"><span>No document open</span></section>}

            <section className="chat-panel">
              <header className="panel-header">
                <div><span className="eyebrow">Evidence assistant</span><strong>Ask CiteMind</strong></div>
                <select aria-label="Answer scope" value={scopeDocumentId ?? "course"} onChange={(event) => changeScope(event.target.value)}>
                  <option value="course">Entire course</option>
                  {readyDocuments.map((document) => <option key={document.id} value={document.id}>Only: {document.title}</option>)}
                </select>
              </header>
              <div className="messages">
                {!messages.length && (
                  <div className="chat-empty"><span>✦</span><h2>What do you want to understand?</h2><p>I’ll answer only from this course and cite the exact pages I used.</p></div>
                )}
                {messages.map((message, index) => (
                  <article key={message.id ?? index} className={`message ${message.role}`}>
                    <span className="role">{message.role === "user" ? "You" : "CiteMind"}</span>
                    {message.role === "assistant" ? <MathText>{message.content}</MathText> : <p>{message.content}</p>}
                    {!!message.citations?.length && <div className="citations">
                      {message.citations.map((citation) => (
                        <button key={citation.number} aria-label={`打开 ${citation.title} 第 ${citation.page_number} 页`} onClick={() => openCitation(citation)}>
                          <span className="citation-source">[{citation.number}] {citation.title} · p.{citation.page_number}{citation.visual && <em>视觉核对</em>}</span>
                          <CitationPreview documentId={citation.document_id} page={citation.page_number} content={citation.content} />
                          <small className="citation-open-hint">打开第 {citation.page_number} 页细看 <b>→</b></small>
                        </button>
                      ))}
                    </div>}
                  </article>
                ))}
                {busy && <div className="thinking"><i /><i /><i /> Finding evidence and checking citations…</div>}
                <div ref={bottomRef} />
              </div>
              {error && <button className="error-banner" onClick={() => setError("")}>{error}<span>×</span></button>}
              <form className="ask-box" onSubmit={submitQuestion}>
                <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={readyDocuments.length ? "Ask a question about your materials…" : hasProcessingDocuments ? "Wait for PDF processing to finish" : "Add a PDF before asking a question"} disabled={!readyDocuments.length || busy} rows={2} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} />
                <button aria-label="Ask" disabled={!question.trim() || busy}>↑</button>
                <small>CiteMind may be wrong. Always check the cited source.</small>
              </form>
            </section>
          </div>
        </section>
      )}

      {showUpload && courseId && <UploadDialog courseId={courseId} onClose={() => setShowUpload(false)} onUploaded={async (document) => {
        const docs = await api.documents(courseId);
        setDocuments(docs); setActiveDocument(document); setPage(1); setShowUpload(false); await refreshCourses();
      }} onError={showError} />}
    </main>
  );
}

function UploadDialog({ courseId, onClose, onUploaded, onError }: { courseId: number; onClose: () => void; onUploaded: (document: Document) => void; onError: (error: unknown) => void }) {
  const [kind, setKind] = useState<Document["kind"]>("lecture");
  const [uploading, setUploading] = useState(false);
  async function choose(file?: File) {
    if (!file) return;
    setUploading(true);
    try { onUploaded(await api.upload(courseId, kind, file)); }
    catch (error) { onError(error); setUploading(false); }
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !uploading) onClose(); }}>
    <section className="modal" role="dialog" aria-modal="true" aria-label="Add a PDF">
      <button className="modal-close" onClick={onClose} disabled={uploading}>×</button>
      <span className="eyebrow">Add source</span><h2>Bring a PDF into this course</h2>
      <p>Text or scanned PDF · up to 25 MB and 200 pages. Scanned pages are sent to your configured AI for visual OCR and keep their original page numbers.</p>
      <div className="kind-picker">{Object.entries(kindNames).map(([value, label]) => <button key={value} className={kind === value ? "active" : ""} onClick={() => setKind(value as Document["kind"])}>{label}</button>)}</div>
      <label className={uploading ? "file-drop uploading" : "file-drop"}>
        <input type="file" accept="application/pdf,.pdf" disabled={uploading} onChange={(event) => choose(event.target.files?.[0])} />
        <span>{uploading ? "Uploading and checking pages…" : "Choose a PDF"}</span>
        <small>{uploading ? "You can close this window once the upload finishes" : "Your original file stays on this computer"}</small>
      </label>
    </section>
  </div>;
}
