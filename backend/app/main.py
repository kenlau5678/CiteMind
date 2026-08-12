import json
import mimetypes
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai
from .db import FILES_DIR, connect, decode_message, init_db, rows


MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_PAGES = 200


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CiteMind API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    document_id: int | None = None
    top_k: int = Field(default=8, ge=1, le=20)


class AskRequest(SearchRequest):
    pass


def require_course(course_id: int):
    with connect() as db:
        course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course:
        raise HTTPException(404, "Course not found")
    return dict(course)


def split_page(text: str) -> list[str]:
    clean = re.sub(r"[ \t]+", " ", text).strip()
    if not clean:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|(?<=[.!?。！？])\s+", clean) if part.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > 2800:
            chunks.append(current)
            current = current[-300:] + " " + paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def _keyword_results(db, course_id: int, query: str, document_id: int | None, limit: int):
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
    match = " OR ".join(f'"{token}"' for token in tokens[:12])
    scope = "AND c.document_id=?" if document_id else ""
    params = [match, course_id] + ([document_id] if document_id else []) + [limit]
    if match:
        try:
            return rows(db.execute(
                f"""SELECT c.*, d.title, d.filename, bm25(chunks_fts) keyword_score
                    FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid
                    JOIN documents d ON d.id=c.document_id
                    WHERE chunks_fts MATCH ? AND c.course_id=? {scope}
                    ORDER BY keyword_score LIMIT ?""",
                params,
            ).fetchall())
        except Exception:
            pass
    like = f"%{query[:200]}%"
    params = [course_id, like] + ([document_id] if document_id else []) + [limit]
    return rows(db.execute(
        f"""SELECT c.*, d.title, d.filename, 0 keyword_score FROM chunks c
            JOIN documents d ON d.id=c.document_id
            WHERE c.course_id=? AND c.content LIKE ? {scope} LIMIT ?""",
        params,
    ).fetchall())


def search_chunks(course_id: int, request: SearchRequest):
    require_course(course_id)
    try:
        query_vector = ai.embed([request.query])[0]
    except ai.AIError as exc:
        raise HTTPException(503, str(exc)) from exc
    with connect() as db:
        keyword = _keyword_results(db, course_id, request.query, request.document_id, 30)
        sql = """SELECT c.*, d.title, d.filename FROM chunks c
                 JOIN documents d ON d.id=c.document_id
                 WHERE c.course_id=? AND c.embedding IS NOT NULL"""
        params = [course_id]
        if request.document_id:
            sql += " AND c.document_id=?"
            params.append(request.document_id)
        semantic = rows(db.execute(sql, params).fetchall())
    semantic.sort(key=lambda item: ai.cosine(query_vector, json.loads(item["embedding"])), reverse=True)
    semantic = semantic[:30]
    merged: dict[int, dict] = {}
    for rank, item in enumerate(keyword, 1):
        merged[item["id"]] = {**item, "score": 1 / (60 + rank), "keyword_match": True}
    for rank, item in enumerate(semantic, 1):
        score = ai.cosine(query_vector, json.loads(item["embedding"]))
        current = merged.setdefault(item["id"], {**item, "score": 0, "keyword_match": False})
        current["score"] += 1 / (60 + rank)
        current["semantic_score"] = score
    ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
    safe = [item for item in ranked if item.get("keyword_match") or item.get("semantic_score", 0) >= 0.25]
    for item in safe:
        item.pop("embedding", None)
        item.pop("keyword_score", None)
    return safe[: request.top_k]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "ai_configured": bool(ai.API_KEY()),
        "chat_model": ai.CHAT_MODEL(),
        "embedding_model": ai.LOCAL_EMBEDDING_MODEL(),
    }


@app.get("/api/courses")
def list_courses():
    with connect() as db:
        return rows(db.execute(
            """SELECT c.*, count(DISTINCT d.id) document_count FROM courses c
               LEFT JOIN documents d ON d.course_id=c.id GROUP BY c.id ORDER BY c.created_at DESC"""
        ).fetchall())


@app.post("/api/courses", status_code=201)
def create_course(body: CourseCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Course name cannot be blank")
    with connect() as db:
        cursor = db.execute("INSERT INTO courses(name) VALUES (?)", (name,))
        return dict(db.execute("SELECT * FROM courses WHERE id=?", (cursor.lastrowid,)).fetchone())


@app.delete("/api/courses/{course_id}", status_code=204)
def delete_course(course_id: int):
    require_course(course_id)
    with connect() as db:
        names = [row[0] for row in db.execute("SELECT stored_name FROM documents WHERE course_id=?", (course_id,))]
        db.execute("DELETE FROM courses WHERE id=?", (course_id,))
    for name in names:
        (FILES_DIR / name).unlink(missing_ok=True)


@app.get("/api/courses/{course_id}/documents")
def list_documents(course_id: int):
    require_course(course_id)
    with connect() as db:
        return rows(db.execute("SELECT * FROM documents WHERE course_id=? ORDER BY created_at DESC", (course_id,)).fetchall())


@app.post("/api/courses/{course_id}/documents", status_code=201)
def upload_document(course_id: int, kind: str = Form(...), file: UploadFile = File(...)):
    require_course(course_id)
    if kind not in {"lecture", "notes", "paper"}:
        raise HTTPException(422, "Invalid document kind")
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(415, "Only PDF files are supported")
    stored_name = f"{uuid.uuid4().hex}.pdf"
    target = FILES_DIR / stored_name
    size = 0
    try:
        with target.open("wb") as output:
            while block := file.file.read(1024 * 1024):
                size += len(block)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(413, "File exceeds the 25 MB limit")
                output.write(block)
        pdf = fitz.open(target)
        if pdf.page_count > MAX_PAGES:
            raise HTTPException(413, "PDF exceeds the 200-page limit")
        pages = [(index + 1, pdf.load_page(index).get_text("text")) for index in range(pdf.page_count)]
        pdf.close()
        pieces = [(page, chunk) for page, text in pages for chunk in split_page(text)]
        if not pieces:
            raise HTTPException(422, "No selectable text found. Scanned PDFs are not supported yet")
        vectors = []
        for start in range(0, len(pieces), 64):
            vectors.extend(ai.embed([content for _, content in pieces[start:start + 64]]))
        with connect() as db:
            cursor = db.execute(
                """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,status)
                   VALUES (?,?,?,?,?,?,?,'ready')""",
                (course_id, Path(file.filename).stem, kind, file.filename, stored_name, size, len(pages)),
            )
            document_id = cursor.lastrowid
            db.executemany(
                "INSERT INTO chunks(document_id,course_id,page_number,content,embedding) VALUES (?,?,?,?,?)",
                [(document_id, course_id, page, content, json.dumps(vector)) for (page, content), vector in zip(pieces, vectors)],
            )
            return dict(db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone())
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except (fitz.FileDataError, ai.AIError) as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(422 if isinstance(exc, fitz.FileDataError) else 503, str(exc)) from exc


@app.get("/api/documents/{document_id}/file")
def document_file(document_id: int):
    with connect() as db:
        document = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    if not document:
        raise HTTPException(404, "Document not found")
    return FileResponse(FILES_DIR / document["stored_name"], media_type="application/pdf", filename=document["filename"])


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document(document_id: int):
    with connect() as db:
        document = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not document:
            raise HTTPException(404, "Document not found")
        db.execute("DELETE FROM messages WHERE course_id=?", (document["course_id"],))
        db.execute("DELETE FROM documents WHERE id=?", (document_id,))
    (FILES_DIR / document["stored_name"]).unlink(missing_ok=True)


@app.post("/api/courses/{course_id}/search")
def search(course_id: int, body: SearchRequest):
    return search_chunks(course_id, body)


@app.get("/api/courses/{course_id}/messages")
def messages(course_id: int):
    require_course(course_id)
    with connect() as db:
        return [decode_message(row) for row in db.execute(
            "SELECT * FROM messages WHERE course_id=? ORDER BY id", (course_id,)
        ).fetchall()]


@app.delete("/api/courses/{course_id}/messages", status_code=204)
def clear_messages(course_id: int):
    require_course(course_id)
    with connect() as db:
        db.execute("DELETE FROM messages WHERE course_id=?", (course_id,))


@app.post("/api/courses/{course_id}/ask")
def ask(course_id: int, body: AskRequest):
    evidence = search_chunks(course_id, body)
    if not evidence:
        raise HTTPException(422, "No reliable evidence was found in this course")
    with connect() as db:
        history = rows(db.execute(
            "SELECT role,content FROM messages WHERE course_id=? ORDER BY id DESC LIMIT 4", (course_id,)
        ).fetchall())[::-1]
    try:
        result = ai.answer(body.query, evidence, history)
    except ai.AIError as exc:
        raise HTTPException(502, str(exc)) from exc
    citations = [
        {
            "number": number,
            "chunk_id": evidence[number - 1]["id"],
            "document_id": evidence[number - 1]["document_id"],
            "title": evidence[number - 1]["title"],
            "page_number": evidence[number - 1]["page_number"],
            "content": evidence[number - 1]["content"],
        }
        for number in result["citation_numbers"]
    ]
    with connect() as db:
        db.execute(
            "INSERT INTO messages(course_id,role,content,scope_document_id) VALUES (?,?,?,?)",
            (course_id, "user", body.query, body.document_id),
        )
        db.execute(
            "INSERT INTO messages(course_id,role,content,citations,scope_document_id) VALUES (?,?,?,?,?)",
            (course_id, "assistant", result["answer"], json.dumps(citations), body.document_id),
        )
    return {"answer": result["answer"], "citations": citations}


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    mimetypes.add_type("text/javascript", ".mjs")
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
