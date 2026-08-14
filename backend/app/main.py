import json
import math
import mimetypes
import os
import re
import threading
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
MAX_SCAN_PAGES = max(1, min(MAX_PAGES, int(os.getenv("CITEMIND_SCAN_MAX_PAGES", "50"))))

SYMBOL_GLYPHS = {
    "\uf028": "(", "\uf029": ")", "\uf02b": "+", "\uf02d": "−", "\uf03d": "=",
    "\uf03c": "<", "\uf03e": ">", "\uf05c": "∴",
    "\uf061": "α", "\uf062": "β", "\uf063": "χ", "\uf064": "δ", "\uf065": "ε",
    "\uf066": "φ", "\uf067": "γ", "\uf068": "η", "\uf069": "ι", "\uf06a": "φ",
    "\uf06b": "κ", "\uf06c": "λ", "\uf06d": "μ", "\uf06e": "ν", "\uf06f": "ο",
    "\uf070": "π", "\uf071": "θ", "\uf072": "ρ", "\uf073": "σ", "\uf074": "τ",
    "\uf075": "υ", "\uf077": "ω", "\uf078": "ξ", "\uf079": "ψ", "\uf07a": "ζ",
    "\uf0a2": "′", "\uf0a3": "≤", "\uf0ae": "→", "\uf0b0": "°", "\uf0b1": "±",
    "\uf0b3": "≥", "\uf0b4": "×", "\uf0b6": "∂", "\uf0b8": "÷", "\uf0b9": "≠",
    "\uf0ba": "≡", "\uf0bb": "≈", "\uf0d0": "∠", "\uf0d1": "∇", "\uf0d5": "∏",
    "\uf0d6": "√", "\uf0d7": "⋅", "\uf0e5": "∑", "\uf0f2": "∫",
}


def normalize_private_glyphs(text: str, glyph_fonts: dict[str, set[str]]) -> str:
    """Decode only private glyphs whose source font makes their meaning unambiguous."""
    for glyph, replacement in SYMBOL_GLYPHS.items():
        fonts = glyph_fonts.get(glyph, set())
        if fonts and all("Symbol" in font for font in fonts):
            text = text.replace(glyph, replacement)
    dot = "\uf026"
    fonts = glyph_fonts.get(dot, set())
    if fonts and all("MT-Extra" in font for font in fonts):
        text = text.replace(dot * 2, "¨").replace(dot, "˙")
    return text


def extract_page_text(page: fitz.Page) -> str:
    glyph_fonts: dict[str, set[str]] = {}
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for glyph in span["text"]:
                    if "\ue000" <= glyph <= "\uf8ff":
                        glyph_fonts.setdefault(glyph, set()).add(span["font"])
    return normalize_private_glyphs(page.get_text("text", sort=True), glyph_fonts)


def visual_page_reason(page: fitz.Page, text: str) -> str | None:
    """Cheap local gate: only pages with meaningful visual detail may call a vision model."""
    page_area = max(page.rect.width * page.rect.height, 1)
    image_area = sum(
        max(0, block["bbox"][2] - block["bbox"][0]) * max(0, block["bbox"][3] - block["bbox"][1])
        for block in page.get_text("dict")["blocks"] if block.get("type") == 1
    )
    raw = page.get_text("text")
    if image_area / page_area >= 0.08:
        return "large_image"
    drawings = len(page.get_drawings())
    if drawings and (drawings >= 4 or len(text) < 1200):
        return "vector_diagram"
    if sum("\ue000" <= char <= "\uf8ff" for char in raw) >= 3:
        return "legacy_formula"
    if sum(text.count(marker) for marker in ("=", "∑", "∫", "√", "∂", "×")) >= 4:
        return "formula_dense"
    return None


def scan_page_needs_ocr(page: fitz.Page, text: str) -> bool:
    """Detect rasterized pages without enough native text to search reliably."""
    visible_characters = len(re.sub(r"\s+", "", text))
    return visible_characters < 32 and bool(page.get_images(full=True))


PAGE_REFERENCE_TERMS = (
    "这页", "这一页", "本页", "当前页", "这道题", "这道例题", "此题", "图中", "上图",
    "this page", "this example", "this problem", "the figure above",
)


def question_references_current_page(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in PAGE_REFERENCE_TERMS)


def question_requests_vision(question: str) -> bool:
    lowered = question.lower()
    return question_references_current_page(question) or any(term in lowered for term in (
        "图", "曲线", "坐标", "箭头", "受力", "机构", "公式", "方程", "矩阵",
        "diagram", "figure", "chart", "image", "graph", "formula", "equation", "matrix",
    ))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CiteMind API", version="0.1.8", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class DocumentOrder(BaseModel):
    document_ids: list[int] = Field(min_length=1)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    document_id: int | None = None
    top_k: int = Field(default=8, ge=1, le=20)


class AskRequest(SearchRequest):
    context_document_id: int | None = None
    context_page_number: int | None = Field(default=None, ge=1)


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
    paragraphs = [
        part.strip()
        for part in re.split(r"\n\s*\n|(?<=[。！？])|(?<=[.!?])\s+", clean)
        if part.strip()
    ]
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
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
        "how", "i", "in", "is", "it", "of", "on", "or", "the", "this", "to", "what",
        "when", "where", "which", "why", "with",
    }
    tokens = [
        token for token in re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
        if (len(token) >= 2 or "\u4e00" <= token <= "\u9fff") and token not in stopwords
    ]
    match = " OR ".join(f'"{token}"' for token in tokens[:12])
    scope = "AND c.document_id=?" if document_id else ""
    params = [match, course_id] + ([document_id] if document_id else []) + [limit]
    if match:
        try:
            return rows(db.execute(
                f"""SELECT c.*, d.title, d.filename, bm25(chunks_fts) keyword_score
                    FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid
                    JOIN documents d ON d.id=c.document_id
                    WHERE chunks_fts MATCH ? AND c.course_id=? AND d.status='ready' {scope}
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
            WHERE c.course_id=? AND d.status='ready' AND c.content LIKE ? {scope} LIMIT ?""",
        params,
    ).fetchall())


def _cjk_bigrams(text: str) -> set[str]:
    return {
        sequence[index:index + 2]
        for sequence in re.findall(r"[\u4e00-\u9fff]+", text)
        for index in range(len(sequence) - 1)
    }


def _query_topics(query: str) -> set[str]:
    cleaned = re.sub(r"(是什么|为什么|如何|怎么|怎样|分别|各|公式)", "|", query)
    topics = set()
    for segment in re.findall(r"[\u4e00-\u9fff]+", cleaned):
        if len(segment) >= 4:
            topics.add(segment)
        topics.update(part for part in segment.split("的") if len(part) >= 4)
    return topics


def _cjk_results(db, course_id: int, query: str, document_id: int | None, limit: int):
    query_terms = _cjk_bigrams(query)
    query_topics = _query_topics(query)
    if not query_terms:
        return []
    sql = """SELECT c.*, d.title, d.filename FROM chunks c
             JOIN documents d ON d.id=c.document_id WHERE c.course_id=? AND d.status='ready'"""
    params = [course_id]
    if document_id is not None:
        sql += " AND c.document_id=?"
        params.append(document_id)
    candidates = rows(db.execute(sql, params).fetchall())
    candidate_terms = [_cjk_bigrams(item["content"]) for item in candidates]
    document_frequency = {
        term: sum(term in terms for terms in candidate_terms)
        for term in query_terms
    }
    weights = {
        term: math.log((len(candidates) + 1) / (frequency + 1)) + 1
        for term, frequency in document_frequency.items()
    }
    query_weight = sum(weights.values()) or 1
    scored = []
    minimum_overlap = 1 if len(query_terms) <= 2 else 2
    for item, terms in zip(candidates, candidate_terms):
        matched = query_terms & terms
        overlap = len(matched)
        ratio = sum(weights[term] for term in matched) / query_weight
        if overlap >= minimum_overlap and ratio >= 0.15:
            searchable = f"{item['title']}\n{item['content']}"
            topic_match = max((len(topic) for topic in query_topics if topic in searchable), default=0)
            formula_match = False
            if any(marker in item["content"] for marker in ("=", "＝", "\uf03d")):
                for match in re.finditer("公式", query):
                    prefix = re.search(r"[\u4e00-\u9fff]+$", query[:match.start()])
                    if prefix and any(
                        prefix.group()[-length:] in item["content"]
                        for length in range(min(5, len(prefix.group())), 1, -1)
                    ):
                        formula_match = True
                        break
            formula_bonus = 0.35 if formula_match else 0
            topic_bonus = 0.12 * min(topic_match, 8)
            item["lexical_score"] = ratio + formula_bonus + topic_bonus
            item["lexical_overlap"] = overlap
            item["formula_match"] = formula_match
            item["topic_match"] = topic_match
            scored.append(item)
    scored.sort(key=lambda item: (item["lexical_score"], item["lexical_overlap"]), reverse=True)
    return scored[:limit]


def search_chunks(course_id: int, request: SearchRequest):
    require_course(course_id)
    if request.document_id is not None:
        with connect() as db:
            scoped_document = db.execute(
                "SELECT 1 FROM documents WHERE id=? AND course_id=?",
                (request.document_id, course_id),
            ).fetchone()
        if not scoped_document:
            raise HTTPException(404, "Document not found in this course")
    try:
        query_vector = ai.embed([request.query])[0]
    except ai.AIError as exc:
        raise HTTPException(503, str(exc)) from exc
    with connect() as db:
        keyword = _keyword_results(db, course_id, request.query, request.document_id, 30)
        cjk = _cjk_results(db, course_id, request.query, request.document_id, 30)
        sql = """SELECT c.*, d.title, d.filename FROM chunks c
                 JOIN documents d ON d.id=c.document_id
                 WHERE c.course_id=? AND d.status='ready' AND c.embedding IS NOT NULL"""
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
    for rank, item in enumerate(cjk, 1):
        current = merged.setdefault(item["id"], {**item, "score": 0, "keyword_match": False})
        current["score"] += (2 if item.get("formula_match") else 1) / (60 + rank)
        current["score"] += min(item.get("lexical_score", 0), 1.5) / 100
        current["cjk_match"] = True
    for rank, item in enumerate(semantic, 1):
        score = ai.cosine(query_vector, json.loads(item["embedding"]))
        current = merged.setdefault(item["id"], {**item, "score": 0, "keyword_match": False})
        current["score"] += 1 / (60 + rank)
        current["semantic_score"] = score
    ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
    deduplicated = []
    seen_pages = set()
    for item in ranked:
        page = (item["title"], item["page_number"])
        if page in seen_pages:
            continue
        seen_pages.add(page)
        deduplicated.append(item)
    safe = [
        item for item in deduplicated
        if item.get("keyword_match") or item.get("cjk_match") or item.get("semantic_score", 0) >= 0.25
    ]
    for item in safe:
        item.pop("embedding", None)
        item.pop("keyword_score", None)
        item.pop("lexical_score", None)
        item.pop("lexical_overlap", None)
        item.pop("formula_match", None)
        item.pop("topic_match", None)
    return safe[: request.top_k]


def add_neighbor_context(evidence: list[dict], max_extra: int = 6) -> list[dict]:
    """Include nearby pages when a section heading ranks above its explanation."""
    if not evidence or max_extra <= 0:
        return merge_page_evidence(evidence)
    result = merge_page_evidence(evidence)
    base_count = len(result)
    seen = {(item["document_id"], item["page_number"]) for item in result}
    with connect() as db:
        for seed in result[:4]:
            neighbors = rows(db.execute(
                """SELECT c.*, d.title, d.filename FROM chunks c
                   JOIN documents d ON d.id=c.document_id
                   WHERE c.document_id=? AND c.page_number IN (?,?)
                   ORDER BY c.page_number""",
                (seed["document_id"], seed["page_number"] - 1, seed["page_number"] + 1),
            ).fetchall())
            for item in merge_page_evidence(neighbors):
                page = (item["document_id"], item["page_number"])
                if page in seen:
                    continue
                item.pop("embedding", None)
                result.append(item)
                seen.add(page)
                if len(result) >= base_count + max_extra:
                    return result
    return result


def merge_page_evidence(evidence: list[dict]) -> list[dict]:
    """Expose each PDF page once while retaining every distinct chunk on that page."""
    result = []
    pages = {}
    for item in evidence:
        key = (item["document_id"], item["page_number"])
        if key not in pages:
            pages[key] = {**item}
            result.append(pages[key])
            continue
        content = item.get("content", "")
        if content and content not in pages[key].get("content", ""):
            pages[key]["content"] = f"{pages[key].get('content', '')}\n\n{content}".strip()
        if item.get("current_page"):
            pages[key]["current_page"] = True
    return result


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "ai_configured": bool(ai.API_KEY()),
        "chat_model": ai.CHAT_MODEL(),
        "vision_index_model": ai.VISION_INDEX_MODEL(),
        "vision_answer_model": ai.VISION_ANSWER_MODEL(),
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
        return rows(db.execute(
            "SELECT * FROM documents WHERE course_id=? ORDER BY sort_order,created_at DESC",
            (course_id,),
        ).fetchall())


@app.put("/api/courses/{course_id}/documents/order", status_code=204)
def reorder_documents(course_id: int, body: DocumentOrder):
    require_course(course_id)
    with connect() as db:
        current_ids = [row[0] for row in db.execute("SELECT id FROM documents WHERE course_id=?", (course_id,))]
        if len(body.document_ids) != len(current_ids) or set(body.document_ids) != set(current_ids):
            raise HTTPException(422, "Document order must include every document in this course exactly once")
        db.executemany(
            "UPDATE documents SET sort_order=? WHERE id=?",
            [(index, document_id) for index, document_id in enumerate(body.document_ids)],
        )


def process_scanned_document(document_id: int) -> None:
    """Continue a scanned document from its last committed page."""
    try:
        with connect() as db:
            document = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not document:
            return
        with fitz.open(FILES_DIR / document["stored_name"]) as pdf:
            for index in range(document["processed_pages"], pdf.page_count):
                page = pdf.load_page(index)
                text = extract_page_text(page)
                reason = visual_page_reason(page, text)
                description = model = None
                if scan_page_needs_ocr(page, text):
                    image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
                    text, description = ai.transcribe_scan_page(image)
                    reason, model = "scan_ocr", ai.VISION_INDEX_MODEL()
                pieces = split_page(text)
                vectors = ai.embed(pieces) if pieces else []
                with connect() as db:
                    if not db.execute("SELECT 1 FROM documents WHERE id=?", (document_id,)).fetchone():
                        return
                    db.execute("DELETE FROM chunks WHERE document_id=? AND page_number=?", (document_id, index + 1))
                    db.execute("DELETE FROM page_visuals WHERE document_id=? AND page_number=?", (document_id, index + 1))
                    db.executemany(
                        "INSERT INTO chunks(document_id,course_id,page_number,content,embedding) VALUES (?,?,?,?,?)",
                        [
                            (document_id, document["course_id"], index + 1, content, json.dumps(vector))
                            for content, vector in zip(pieces, vectors)
                        ],
                    )
                    if reason:
                        db.execute(
                            "INSERT INTO page_visuals(document_id,page_number,reason,description,model) VALUES (?,?,?,?,?)",
                            (document_id, index + 1, reason, description, model),
                        )
                    db.execute("UPDATE documents SET processed_pages=? WHERE id=?", (index + 1, document_id))
        with connect() as db:
            if db.execute("SELECT count(*) FROM chunks WHERE document_id=?", (document_id,)).fetchone()[0] == 0:
                raise ValueError("No readable text was found in this PDF")
            db.execute("UPDATE documents SET status='ready', error=NULL WHERE id=?", (document_id,))
    except Exception as exc:  # worker boundary: persist any page/model failure for retry
        with connect() as db:
            db.execute(
                "UPDATE documents SET status='failed', error=? WHERE id=?",
                ((str(exc) or "Document processing failed")[:300], document_id),
            )


def start_scanned_processing(document_id: int) -> None:
    # ponytail: in-process worker suits one local user; use a durable queue for multi-user hosting.
    threading.Thread(target=process_scanned_document, args=(document_id,), daemon=True).start()


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
    keep_file = False
    try:
        with target.open("wb") as output:
            while block := file.file.read(1024 * 1024):
                size += len(block)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(413, "File exceeds the 25 MB limit")
                output.write(block)
        with fitz.open(target) as pdf:
            if pdf.page_count > MAX_PAGES:
                raise HTTPException(413, "PDF exceeds the 200-page limit")
            pages = []
            scans = []
            for index in range(pdf.page_count):
                page = pdf.load_page(index)
                text = extract_page_text(page)
                if scan_page_needs_ocr(page, text):
                    scans.append(index)
                pages.append({
                    "number": index + 1,
                    "text": text,
                    "reason": visual_page_reason(page, text),
                    "description": None,
                    "model": None,
                })
            if len(scans) > MAX_SCAN_PAGES:
                raise HTTPException(413, f"Scanned PDF exceeds the {MAX_SCAN_PAGES}-page OCR limit")
            if scans and not ai.API_KEY():
                raise HTTPException(503, "Scanned PDF pages require OPENAI_API_KEY for visual OCR")
        if scans:
            with connect() as db:
                sort_order = db.execute(
                    "SELECT COALESCE(min(sort_order),0)-1 FROM documents WHERE course_id=?", (course_id,)
                ).fetchone()[0]
                cursor = db.execute(
                    """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,sort_order,status)
                       VALUES (?,?,?,?,?,?,?,?,'processing')""",
                    (course_id, Path(file.filename).stem, kind, file.filename, stored_name, size, len(pages), sort_order),
                )
                document_id = cursor.lastrowid
                document = dict(db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone())
            keep_file = True
            start_scanned_processing(document_id)
            return document
        pieces = [
            (page["number"], chunk)
            for page in pages
            for chunk in split_page(page["text"])
        ]
        if not pieces:
            raise HTTPException(422, "No readable text was found in this PDF")
        vectors = []
        for start in range(0, len(pieces), 64):
            vectors.extend(ai.embed([content for _, content in pieces[start:start + 64]]))
        with connect() as db:
            sort_order = db.execute(
                "SELECT COALESCE(min(sort_order),0)-1 FROM documents WHERE course_id=?", (course_id,)
            ).fetchone()[0]
            cursor = db.execute(
                """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,processed_pages,sort_order,status)
                   VALUES (?,?,?,?,?,?,?,?,?,'ready')""",
                (course_id, Path(file.filename).stem, kind, file.filename, stored_name, size, len(pages), len(pages), sort_order),
            )
            document_id = cursor.lastrowid
            db.executemany(
                "INSERT INTO chunks(document_id,course_id,page_number,content,embedding) VALUES (?,?,?,?,?)",
                [(document_id, course_id, page, content, json.dumps(vector)) for (page, content), vector in zip(pieces, vectors)],
            )
            db.executemany(
                "INSERT INTO page_visuals(document_id,page_number,reason,description,model) VALUES (?,?,?,?,?)",
                [
                    (document_id, page["number"], page["reason"], page["description"], page["model"])
                    for page in pages if page["reason"]
                ],
            )
            document = dict(db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone())
        keep_file = True
        return document
    except HTTPException:
        raise
    except (fitz.FileDataError, ai.AIError) as exc:
        raise HTTPException(422 if isinstance(exc, fitz.FileDataError) else 503, str(exc)) from exc
    finally:
        if not keep_file:
            target.unlink(missing_ok=True)


@app.post("/api/documents/{document_id}/retry", status_code=202)
def retry_document(document_id: int):
    with connect() as db:
        document = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not document:
            raise HTTPException(404, "Document not found")
        if document["status"] != "failed":
            raise HTTPException(409, "Only failed documents can be retried")
        db.execute("UPDATE documents SET status='processing', error=NULL WHERE id=?", (document_id,))
        result = dict(db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone())
    start_scanned_processing(document_id)
    return result


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
        if document["status"] == "processing":
            raise HTTPException(409, "Wait for processing to finish before deleting this document")
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


def current_page_evidence(course_id: int, document_id: int, page_number: int) -> list[dict]:
    with connect() as db:
        document = db.execute(
            "SELECT page_count,status FROM documents WHERE id=? AND course_id=?",
            (document_id, course_id),
        ).fetchone()
        if not document or document["status"] != "ready" or page_number > document["page_count"]:
            raise HTTPException(422, "The current PDF page is not available")
        evidence = rows(db.execute(
            """SELECT c.*,d.title,d.filename FROM chunks c JOIN documents d ON d.id=c.document_id
               WHERE c.document_id=? AND c.page_number=? ORDER BY c.id""",
            (document_id, page_number),
        ).fetchall())
    if not evidence:
        raise HTTPException(422, "The current PDF page has no readable evidence")
    for item in evidence:
        item.pop("embedding", None)
        item["current_page"] = True
    return evidence


def prepare_visual_evidence(
    question: str, evidence: list[dict], forced_page: tuple[int, int] | None = None,
) -> tuple[list[dict], list[dict]]:
    if not ai.API_KEY() or not question_requests_vision(question) or ai.VISION_MAX_PAGES() == 0:
        return evidence, []
    enriched = [dict(item) for item in evidence]
    images = []
    seen: set[tuple[int, int]] = set()
    for index, item in enumerate(enriched):
        key = (item["document_id"], item["page_number"])
        if key in seen:
            continue
        seen.add(key)
        with connect() as db:
            document = db.execute("SELECT stored_name FROM documents WHERE id=?", (item["document_id"],)).fetchone()
            cached = db.execute(
                "SELECT reason,description FROM page_visuals WHERE document_id=? AND page_number=?",
                key,
            ).fetchone()
        if not document:
            continue
        with fitz.open(FILES_DIR / document["stored_name"]) as pdf:
            page = pdf.load_page(item["page_number"] - 1)
            reason = cached["reason"] if cached else visual_page_reason(page, extract_page_text(page))
            if not reason and key == forced_page:
                reason = "current_page"
            if not reason:
                continue
            image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
        description = cached["description"] if cached else None
        if not description:
            try:
                description = ai.describe_page(image, item["content"])
            except ai.AIError:
                description = None
        with connect() as db:
            db.execute(
                """INSERT INTO page_visuals(document_id,page_number,reason,description,model,updated_at)
                   VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT(document_id,page_number) DO UPDATE SET
                   reason=excluded.reason,
                   description=COALESCE(excluded.description,page_visuals.description),
                   model=COALESCE(excluded.model,page_visuals.model),
                   updated_at=CURRENT_TIMESTAMP""",
                (item["document_id"], item["page_number"], reason, description,
                 ai.VISION_INDEX_MODEL() if description else None),
            )
        if description:
            item["visual_description"] = description
        images.append({"number": index + 1, "image": image})
        if len(images) >= ai.VISION_MAX_PAGES():
            break
    return enriched, images


@app.post("/api/courses/{course_id}/ask")
def ask(course_id: int, body: AskRequest):
    evidence = search_chunks(course_id, body)
    forced_page = None
    if (
        question_references_current_page(body.query)
        and body.context_document_id is not None
        and body.context_page_number is not None
        and (body.document_id is None or body.document_id == body.context_document_id)
    ):
        pinned = current_page_evidence(course_id, body.context_document_id, body.context_page_number)
        pinned_ids = {item["id"] for item in pinned}
        evidence = pinned + [item for item in evidence if item["id"] not in pinned_ids]
        forced_page = (body.context_document_id, body.context_page_number)
    evidence = add_neighbor_context(evidence)
    if not evidence:
        raise HTTPException(422, "No reliable evidence was found in this course")
    with connect() as db:
        history = rows(db.execute(
            "SELECT role,content FROM messages WHERE course_id=? ORDER BY id DESC LIMIT 4", (course_id,)
        ).fetchall())[::-1]
    visual_evidence, images = prepare_visual_evidence(body.query, evidence, forced_page)
    vision_used = False
    try:
        if images:
            try:
                result = ai.answer_with_images(body.query, visual_evidence, history, images)
                vision_used = True
            except ai.AIError:
                result = ai.answer(body.query, evidence, history)
        else:
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
            "visual": vision_used and number in {item["number"] for item in images},
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
    return {
        "answer": result["answer"], "citations": citations,
        "insufficient": result["insufficient"], "vision_used": vision_used,
    }


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    mimetypes.add_type("text/javascript", ".mjs")
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
