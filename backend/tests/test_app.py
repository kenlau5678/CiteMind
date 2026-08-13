import json

from app.main import split_page


def create_course(client):
    response = client.post("/api/courses", json={"name": "Machine Learning"})
    assert response.status_code == 201
    return response.json()["id"]


def upload(client, course_id, sample_pdf):
    response = client.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "lecture"},
        files={"file": ("lecture-01.pdf", sample_pdf, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_chinese_sentences_split_without_spaces():
    chunks = split_page(("第一句介绍机器学习。第二句解释反向传播！第三句讨论检索？" * 160))
    assert len(chunks) > 1
    assert "。\n第二句" in chunks[0]
    assert chunks[0].endswith(("。", "！", "？"))


def test_pdf_chunks_keep_real_page_numbers(client, sample_pdf):
    http, _, db_module = client
    course_id = create_course(http)
    document = upload(http, course_id, sample_pdf)
    assert document["page_count"] == 2
    with db_module.connect() as db:
        chunks = db.execute("SELECT page_number, content FROM chunks ORDER BY page_number").fetchall()
    assert [row["page_number"] for row in chunks] == [1, 2]
    assert "Backpropagation" in chunks[0]["content"]
    assert "Convolution" in chunks[1]["content"]


def test_ask_returns_only_validated_source_metadata(client, sample_pdf, monkeypatch):
    http, main, _ = client
    course_id = create_course(http)
    document = upload(http, course_id, sample_pdf)
    monkeypatch.setattr(main.ai, "answer", lambda question, evidence, history: {
        "answer": "Convolution shares weights [1].",
        "citation_numbers": [1],
        "insufficient": False,
    })
    response = http.post(f"/api/courses/{course_id}/ask", json={"query": "What does convolution do?", "top_k": 5})
    assert response.status_code == 200, response.text
    citation = response.json()["citations"][0]
    assert citation["document_id"] == document["id"]
    assert citation["page_number"] in {1, 2}
    assert citation["content"]
    assert response.json()["insufficient"] is False


def test_delete_document_removes_file_chunks_and_chat(client, sample_pdf, monkeypatch):
    http, main, db_module = client
    course_id = create_course(http)
    document = upload(http, course_id, sample_pdf)
    monkeypatch.setattr(main.ai, "answer", lambda question, evidence, history: {
        "answer": "The material says this [1].", "citation_numbers": [1], "insufficient": False
    })
    assert http.post(f"/api/courses/{course_id}/ask", json={"query": "training data"}).status_code == 200
    assert http.delete(f"/api/documents/{document['id']}").status_code == 204
    with db_module.connect() as db:
        assert db.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 0
    assert http.get(f"/api/documents/{document['id']}/file").status_code == 404


def test_insufficient_answer_is_returned_without_fabricated_citations(client, sample_pdf, monkeypatch):
    http, main, _ = client
    course_id = create_course(http)
    upload(http, course_id, sample_pdf)
    monkeypatch.setattr(main.ai, "answer", lambda question, evidence, history: {
        "answer": "The supplied material does not answer this question.",
        "citation_numbers": [],
        "insufficient": True,
    })
    response = http.post(f"/api/courses/{course_id}/ask", json={"query": "What is the tuition fee?"})
    assert response.status_code == 200
    assert response.json()["insufficient"] is True
    assert response.json()["citations"] == []


def test_scanned_pdf_is_rejected(client):
    import fitz
    http, _, _ = client
    course_id = create_course(http)
    pdf = fitz.open()
    pdf.new_page()
    data = pdf.tobytes()
    pdf.close()
    response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "notes"},
        files={"file": ("scan.pdf", data, "application/pdf")},
    )
    assert response.status_code == 422
    assert "Scanned PDFs" in response.json()["detail"]


def test_pdf_over_page_limit_leaves_no_file(client):
    import fitz
    http, _, db_module = client
    course_id = create_course(http)
    pdf = fitz.open()
    for _ in range(201):
        pdf.new_page()
    data = pdf.tobytes()
    pdf.close()
    response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "lecture"},
        files={"file": ("too-long.pdf", data, "application/pdf")},
    )
    assert response.status_code == 413
    assert list(db_module.FILES_DIR.iterdir()) == []


def test_document_scope_cannot_cross_courses(client, sample_pdf):
    http, _, _ = client
    first_course = create_course(http)
    document = upload(http, first_course, sample_pdf)
    second_course = http.post("/api/courses", json={"name": "Another course"}).json()["id"]
    response = http.post(
        f"/api/courses/{second_course}/search",
        json={"query": "convolution", "document_id": document["id"]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found in this course"


def test_corrupt_pdf_leaves_no_file(client):
    http, _, db_module = client
    course_id = create_course(http)
    response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "paper"},
        files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 422
    assert list(db_module.FILES_DIR.iterdir()) == []


def test_embedding_failure_leaves_no_file(client, sample_pdf, monkeypatch):
    http, main, db_module = client
    course_id = create_course(http)

    def fail_embedding(_):
        raise main.ai.AIError("local model failed")

    monkeypatch.setattr(main.ai, "embed", fail_embedding)
    response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "notes"},
        files={"file": ("notes.pdf", sample_pdf, "application/pdf")},
    )
    assert response.status_code == 503
    assert list(db_module.FILES_DIR.iterdir()) == []
