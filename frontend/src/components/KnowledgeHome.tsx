import type { FormEvent } from "react";
import { CitationPreview } from "./CitationPreview";
import { MathText } from "./MathText";
import type { AgentResult, AgentStep, Citation, Course } from "../types";

type Props = {
  courses: Course[];
  question: string;
  busy: boolean;
  status: string;
  error: string;
  aiConfigured: boolean;
  result: AgentResult | null;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onSelectCourse: (courseId: number) => void;
  onCreateCourse: () => void;
  onOpenCitation: (citation: Citation) => void;
  onClearError: () => void;
};

const examples = [
  "虚位移原理需要哪些前置知识？哪些课程和资料讲到了？",
  "比较 Transformer 和 LSTM 的核心差异",
  "整理变分原理相关的定义、公式和学习顺序",
];

function stepText(step: AgentStep) {
  if (step.tool === "search_materials") return `搜索“${String(step.arguments.query ?? "全部资料")}” · 找到 ${step.result_count} 页`;
  const source = step.document_title ? `《${step.document_title}》` : "资料";
  if (step.tool === "read_page") return `阅读${source}第 ${step.arguments.page_number} 页${step.arguments.radius ? "及相邻页" : ""}`;
  if (step.tool === "inspect_page") return `视觉核对${source}第 ${step.arguments.page_number} 页的公式或图形`;
  return "证据已收集，准备生成回答";
}

export function KnowledgeHome({
  courses, question, busy, status, error, aiConfigured, result,
  onQuestionChange, onSubmit, onSelectCourse, onCreateCourse, onOpenCitation, onClearError,
}: Props) {
  const canAsk = courses.some((course) => (course.document_count ?? 0) > 0) && aiConfigured;

  return (
    <section className={result ? "knowledge-home result-open" : "knowledge-home"}>
      <div className="knowledge-scroll">
        <header className="knowledge-heading">
          <span className="eyebrow">Explore your knowledge library</span>
          <h1>{result ? "Your knowledge, connected." : "What do you want to understand?"}</h1>
          {!result && <p>Ask across every uploaded course, lecture, note, and paper. CiteMind will show exactly which PDF pages support the answer.</p>}
        </header>

        <form className="library-ask" onSubmit={onSubmit}>
          <textarea
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder={courses.length ? "Ask a question across your entire library…" : "Create a course and add a PDF to begin"}
            disabled={!canAsk || busy}
            rows={result ? 2 : 4}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <div className="library-ask-footer">
            <small>{aiConfigured ? "Searches your local library and cites exact PDF pages." : "Configure your AI key before asking across the library."}</small>
            <button disabled={!canAsk || !question.trim() || busy}>{busy ? "Exploring…" : "Ask library"}<span>→</span></button>
          </div>
        </form>

        {!result && courses.length > 0 && (
          <div className="question-examples" aria-label="Example questions">
            {examples.map((example) => <button key={example} onClick={() => onQuestionChange(example)}>{example}</button>)}
          </div>
        )}

        {error && <button className="error-banner home-error" onClick={onClearError}>{error}<span>×</span></button>}

        {busy && (
          <section className="agent-running" aria-live="polite">
            <div className="thinking"><i /><i /><i /> {status || "正在探索知识库…"}</div>
          </section>
        )}

        {result ? (
          <div className="exploration-grid">
            <aside className="agent-steps">
              <span className="eyebrow">Agent activity</span>
              <h2>How CiteMind explored</h2>
              <ol>
                {result.steps.map((step) => <li key={step.number}><span>✓</span><p>{stepText(step)}</p></li>)}
              </ol>
            </aside>

            <article className="exploration-answer">
              <span className="eyebrow">Evidence-backed answer</span>
              {result.answer ? <MathText>{result.answer}</MathText> : <p className="answer-placeholder">等待已验证的回答…</p>}

              {!!result.citations.length && (
                <div className="citations home-citations">
                  {result.citations.map((citation) => (
                    <button key={`${citation.document_id}-${citation.page_number}`} onClick={() => onOpenCitation(citation)}>
                      <span className="citation-source">[{citation.number}] {citation.course_name && `${citation.course_name} · `}{citation.title} · p.{citation.page_number}{citation.visual && <em>视觉核对</em>}</span>
                      <CitationPreview documentId={citation.document_id} page={citation.page_number} content={citation.content} />
                      <small className="citation-open-hint">打开原始 PDF 第 {citation.page_number} 页 <b>→</b></small>
                    </button>
                  ))}
                </div>
              )}
            </article>

            {!!result.courses.length && (
              <section className="related-courses">
                <span className="eyebrow">Related courses and materials</span>
                <h2>Where this knowledge appears</h2>
                <div className="related-course-list">
                  {result.courses.map((course) => (
                    <article key={course.id}>
                      <button className="related-course-title" onClick={() => onSelectCourse(course.id)}>
                        <span className="course-icon">{course.name.slice(0, 1).toUpperCase()}</span>
                        <span><strong>{course.name}</strong><small>{course.documents.length} relevant sources</small></span>
                        <b>↗</b>
                      </button>
                      <ul>{course.documents.map((document) => <li key={document.id}>{document.title}<span>p.{document.pages.join(", ")}</span></li>)}</ul>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </div>
        ) : (
          <section className="home-courses">
            <header><h2>Your courses</h2>{!courses.length && <button className="primary" onClick={onCreateCourse}>Create your first course</button>}</header>
            {courses.length ? (
              <div className="home-course-grid">
                {courses.map((course) => (
                  <button key={course.id} onClick={() => onSelectCourse(course.id)}>
                    <span className="course-icon">{course.name.slice(0, 1).toUpperCase()}</span>
                    <span><strong>{course.name}</strong><small>{course.document_count ?? 0} sources</small></span>
                    <b>Open course ↗</b>
                  </button>
                ))}
              </div>
            ) : (
              <div className="home-onboarding"><span className="hero-mark">C</span><h3>Build your first knowledge library</h3><p>Create a course, upload a textbook or lecture, then ask questions across everything you collect.</p></div>
            )}
          </section>
        )}
      </div>
    </section>
  );
}
