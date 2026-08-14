import json
import time

from app.main import normalize_private_glyphs, split_page, visual_page_reason


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


def visual_pdf():
    import fitz
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 90), "A free-body diagram shows force directions and equilibrium.")
    page.draw_line((120, 180), (300, 180), width=3)
    data = pdf.tobytes()
    pdf.close()
    return data


def scanned_pdf(page_count=1):
    """Rasterize generated text so the resulting PDF has images but no text layer."""
    import fitz
    output = fitz.open()
    for number in range(1, page_count + 1):
        source = fitz.open()
        source_page = source.new_page()
        source_page.insert_text((72, 90), f"Scanned dynamics page {number}: impulse equals change in momentum.")
        image = source_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
        page = output.new_page()
        page.insert_image(page.rect, stream=image)
        source.close()
    data = output.tobytes()
    output.close()
    return data


def wait_document(client, course_id, document_id, status, timeout=3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        document = next(
            item for item in client.get(f"/api/courses/{course_id}/documents").json()
            if item["id"] == document_id
        )
        if document["status"] == status:
            return document
        time.sleep(0.02)
    raise AssertionError(f"Document did not reach {status}")


def test_chinese_sentences_split_without_spaces():
    chunks = split_page(("第一句介绍机器学习。第二句解释反向传播！第三句讨论检索？" * 160))
    assert len(chunks) > 1
    assert "。\n第二句" in chunks[0]
    assert chunks[0].endswith(("。", "！", "？"))


def test_private_formula_glyphs_are_decoded_only_for_known_fonts():
    text = "a(t) \uf03d \uf026\uf026s\uf074 \uf02b s\uf0262/\uf072"
    fonts = {
        "\uf03d": {"SymbolMT"}, "\uf074": {"SymbolMT"}, "\uf02b": {"SymbolMT"},
        "\uf072": {"SymbolMT"}, "\uf026": {"MT-Extra"},
    }
    assert normalize_private_glyphs(text, fonts) == "a(t) = ¨sτ + s˙2/ρ"
    assert normalize_private_glyphs("x \uf03d y", {"\uf03d": {"PrivateMathFont"}}) == "x \uf03d y"


def test_legacy_symbol_operators_used_in_mechanics_are_decoded():
    text = "F \uf0a3 μN, α \uf0b3 θ, \uf0e5M = 0, \uf0f2F\uf0d7dr, \uf0d0ABC = 90\uf0b0"
    fonts = {glyph: {"Symbol"} for glyph in set(text) if "\ue000" <= glyph <= "\uf8ff"}
    assert normalize_private_glyphs(text, fonts) == "F ≤ μN, α ≥ θ, ∑M = 0, ∫F⋅dr, ∠ABC = 90°"


def test_legacy_symbol_operator_is_not_guessed_for_ambiguous_fonts():
    glyph = "\uf0e5"
    assert normalize_private_glyphs(glyph, {glyph: {"Symbol", "Wingdings"}}) == glyph


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


def test_visual_page_gate_is_local_and_selective():
    import fitz
    pdf = fitz.open()
    plain = pdf.new_page()
    plain.insert_text((72, 90), "A plain paragraph with no diagram.")
    assert visual_page_reason(plain, plain.get_text()) is None
    diagram = pdf.new_page()
    diagram.insert_text((72, 90), "A mechanics diagram.")
    diagram.draw_line((100, 160), (260, 160), width=2)
    assert visual_page_reason(diagram, diagram.get_text()) == "vector_diagram"
    pdf.close()


def test_visual_analysis_is_cached_and_marks_its_citation(client, monkeypatch):
    http, main, db_module = client
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    course_id = create_course(http)
    document = upload(http, course_id, visual_pdf())
    calls = {"describe": 0, "answer": 0}

    def describe(*_):
        calls["describe"] += 1
        return '{"summary":"One force arrow.","confidence":0.9}'

    def answer_with_images(_question, _evidence, _history, images):
        calls["answer"] += 1
        assert images[0]["image"].startswith(b"\x89PNG")
        return {"answer": "The diagram shows a force direction [1].", "citation_numbers": [1], "insufficient": False}

    monkeypatch.setattr(main.ai, "describe_page", describe)
    monkeypatch.setattr(main.ai, "answer_with_images", answer_with_images)
    for _ in range(2):
        response = http.post(f"/api/courses/{course_id}/ask", json={"query": "What does the diagram show?"})
        assert response.status_code == 200, response.text
        assert response.json()["vision_used"] is True
        assert response.json()["citations"][0]["visual"] is True
    assert calls == {"describe": 1, "answer": 2}
    with db_module.connect() as db:
        cached = db.execute(
            "SELECT description,model FROM page_visuals WHERE document_id=? AND page_number=1",
            (document["id"],),
        ).fetchone()
    assert "force arrow" in cached["description"]
    assert cached["model"] == main.ai.VISION_INDEX_MODEL()


def test_current_page_reference_pins_and_sends_the_displayed_page(client, sample_pdf, monkeypatch):
    http, main, db_module = client
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    course_id = create_course(http)
    document = upload(http, course_id, sample_pdf)
    with db_module.connect() as db:
        unrelated = dict(db.execute(
            """SELECT c.*,d.title,d.filename FROM chunks c JOIN documents d ON d.id=c.document_id
               WHERE c.document_id=? AND c.page_number=1""",
            (document["id"],),
        ).fetchone())
    captured = {}
    monkeypatch.setattr(main, "search_chunks", lambda *_: [unrelated])
    monkeypatch.setattr(main.ai, "describe_page", lambda *_: '{"summary":"Displayed example","confidence":0.9}')
    monkeypatch.setattr(main.ai, "answer_with_images", lambda _q, evidence, _h, images: captured.update(
        evidence=evidence, images=images,
    ) or {"answer": "This page is explained here [1].", "citation_numbers": [1], "insufficient": False})

    response = http.post(f"/api/courses/{course_id}/ask", json={
        "query": "Explain this page",
        "context_document_id": document["id"],
        "context_page_number": 2,
    })

    assert response.status_code == 200, response.text
    assert captured["evidence"][0]["page_number"] == 2
    assert captured["evidence"][0]["current_page"] is True
    assert captured["images"][0]["number"] == 1
    assert response.json()["citations"][0]["page_number"] == 2
    assert response.json()["citations"][0]["visual"] is True


def test_visual_failure_falls_back_to_text_answer(client, monkeypatch):
    http, main, _ = client
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    course_id = create_course(http)
    upload(http, course_id, visual_pdf())
    monkeypatch.setattr(main.ai, "describe_page", lambda *_: (_ for _ in ()).throw(main.ai.AIError("unavailable")))
    monkeypatch.setattr(
        main.ai, "answer_with_images",
        lambda *_: (_ for _ in ()).throw(main.ai.AIError("unavailable")),
    )
    monkeypatch.setattr(main.ai, "answer", lambda *_: {
        "answer": "Text evidence remains available [1].", "citation_numbers": [1], "insufficient": False,
    })
    response = http.post(f"/api/courses/{course_id}/ask", json={"query": "Explain the diagram"})
    assert response.status_code == 200
    assert response.json()["vision_used"] is False
    assert response.json()["citations"][0]["visual"] is False


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


def test_scanned_pdf_is_transcribed_with_original_page_numbers(client, monkeypatch):
    http, main, db_module = client
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    calls = []

    def transcribe(image):
        calls.append(image)
        page = len(calls)
        return (
            f"Scanned dynamics page {page}: impulse equals change in momentum.",
            json.dumps({"summary": f"Scanned page {page}", "confidence": 0.96}),
        )

    monkeypatch.setattr(main.ai, "transcribe_scan_page", transcribe)
    course_id = create_course(http)
    response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "notes"},
        files={"file": ("scan.pdf", scanned_pdf(2), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "processing"
    document = wait_document(http, course_id, response.json()["id"], "ready")
    assert document["processed_pages"] == 2
    assert len(calls) == 2
    assert all(image.startswith(b"\x89PNG") for image in calls)
    with db_module.connect() as db:
        chunks = db.execute("SELECT page_number,content FROM chunks ORDER BY page_number").fetchall()
        visuals = db.execute(
            "SELECT page_number,reason,description,model FROM page_visuals ORDER BY page_number"
        ).fetchall()
    assert [row["page_number"] for row in chunks] == [1, 2]
    assert "change in momentum" in chunks[1]["content"]
    assert [row["reason"] for row in visuals] == ["scan_ocr", "scan_ocr"]
    assert visuals[0]["model"] == main.ai.VISION_INDEX_MODEL()


def test_scanned_pdf_retry_continues_after_last_completed_page(client, monkeypatch):
    http, main, _ = client
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    calls = []
    fail = {"enabled": True}

    def transcribe(image):
        calls.append(image)
        if len(calls) == 2 and fail["enabled"]:
            raise main.ai.AIError("temporary OCR failure")
        return "Recovered scan text", '{"summary":"scan","confidence":0.9}'

    monkeypatch.setattr(main.ai, "transcribe_scan_page", transcribe)
    course_id = create_course(http)
    upload_response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "notes"},
        files={"file": ("retry-scan.pdf", scanned_pdf(2), "application/pdf")},
    )
    document_id = upload_response.json()["id"]
    failed = wait_document(http, course_id, document_id, "failed")
    assert failed["processed_pages"] == 1
    assert "temporary OCR failure" in failed["error"]
    assert http.post(
        f"/api/courses/{course_id}/search", json={"query": "Recovered scan text"}
    ).json() == []

    fail["enabled"] = False
    retry = http.post(f"/api/documents/{document_id}/retry")
    assert retry.status_code == 202
    ready = wait_document(http, course_id, document_id, "ready")
    assert ready["processed_pages"] == 2
    assert len(calls) == 3


def test_scanned_pdf_without_api_key_is_rejected_and_cleaned_up(client):
    http, _, db_module = client
    course_id = create_course(http)
    response = http.post(
        f"/api/courses/{course_id}/documents",
        data={"kind": "notes"},
        files={"file": ("scan.pdf", scanned_pdf(), "application/pdf")},
    )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
    assert list(db_module.FILES_DIR.iterdir()) == []


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


def test_document_order_is_persisted_and_validated(client, sample_pdf):
    http, _, _ = client
    course_id = create_course(http)
    first = upload(http, course_id, sample_pdf)
    second = upload(http, course_id, sample_pdf)
    assert [item["id"] for item in http.get(f"/api/courses/{course_id}/documents").json()] == [second["id"], first["id"]]

    response = http.put(
        f"/api/courses/{course_id}/documents/order",
        json={"document_ids": [first["id"], second["id"]]},
    )
    assert response.status_code == 204
    assert [item["id"] for item in http.get(f"/api/courses/{course_id}/documents").json()] == [first["id"], second["id"]]
    invalid = http.put(
        f"/api/courses/{course_id}/documents/order",
        json={"document_ids": [first["id"], first["id"]]},
    )
    assert invalid.status_code == 422


def test_rephrased_chinese_query_uses_local_bigram_retrieval(client):
    http, _, db_module = client
    course_id = create_course(http)
    with db_module.connect() as db:
        cursor = db.execute(
            """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,status)
               VALUES (?,?,?,?,?,?,?,'ready')""",
            (course_id, "中文课程", "lecture", "zh.pdf", "zh-test.pdf", 100, 2),
        )
        document_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO chunks(document_id,course_id,page_number,content) VALUES (?,?,?,?)",
            [
                (document_id, course_id, 1, "神经网络使用反向传播计算梯度，学习率控制参数更新步长。"),
                (document_id, course_id, 2, "混合检索融合关键词和语义信号，对包含专业术语的课程资料更加可靠。"),
            ],
        )
    response = http.post(
        f"/api/courses/{course_id}/search",
        json={"query": "为什么混合检索更适合课程资料？", "document_id": document_id},
    )
    assert response.status_code == 200
    assert response.json()[0]["page_number"] == 2


def test_cjk_retrieval_prioritizes_rare_concept_terms(client):
    http, main, db_module = client
    course_id = create_course(http)
    with db_module.connect() as db:
        cursor = db.execute(
            """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,status)
               VALUES (?,?,?,?,?,?,?,'ready')""",
            (course_id, "点的运动学", "lecture", "motion.pdf", "motion-rare.pdf", 100, 8),
        )
        document_id = cursor.lastrowid
        pages = [
            "点的加速度说明" if page != 2 else "加速度分解包含切向加速度与法向加速度"
            for page in range(1, 9)
        ]
        db.executemany(
            "INSERT INTO chunks(document_id,course_id,page_number,content) VALUES (?,?,?,?)",
            [(document_id, course_id, page, text) for page, text in enumerate(pages, 1)],
        )
        ranked = main._cjk_results(
            db, course_id, "点的加速度如何分解为切向和法向", None, 8
        )
    assert ranked[0]["page_number"] == 2


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


def test_ask_adds_neighbor_pages_to_heading_matches(client, monkeypatch):
    http, main, db_module = client
    course_id = create_course(http)
    with db_module.connect() as db:
        cursor = db.execute(
            """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,status)
               VALUES (?,?,?,?,?,?,?,'ready')""",
            (course_id, "Motion", "lecture", "motion.pdf", "motion-test.pdf", 100, 4),
        )
        document_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO chunks(document_id,course_id,page_number,content) VALUES (?,?,?,?)",
            [(document_id, course_id, page, text) for page, text in [
                (1, "Introduction"),
                (2, "Angular velocity composition"),
                (3, "Definitions"),
                (4, "The explicit formula is omega equals omega relative plus omega transport."),
            ]],
        )
    with db_module.connect() as db:
        seed_rows = db.execute(
            "SELECT id,page_number,content FROM chunks WHERE page_number IN (2,3) ORDER BY page_number"
        ).fetchall()
    seeds = [
        {"id": row["id"], "document_id": document_id, "course_id": course_id,
         "page_number": row["page_number"], "content": row["content"],
         "title": "Motion", "filename": "motion.pdf"}
        for row in seed_rows
    ]
    captured = {}
    monkeypatch.setattr(main, "search_chunks", lambda *_: seeds)
    monkeypatch.setattr(main.ai, "answer", lambda _q, evidence, _h: captured.update(evidence=evidence) or {
        "answer": "Supported [3].", "citation_numbers": [3], "insufficient": False
    })
    response = http.post(f"/api/courses/{course_id}/ask", json={"query": "formula"})
    assert response.status_code == 200
    assert 4 in {item["page_number"] for item in captured["evidence"]}


def test_formula_query_prefers_page_with_an_explicit_equation(client):
    http, _, db_module = client
    course_id = create_course(http)
    with db_module.connect() as db:
        cursor = db.execute(
            """INSERT INTO documents(course_id,title,kind,filename,stored_name,size_bytes,page_count,status)
               VALUES (?,?,?,?,?,?,?,'ready')""",
            (course_id, "Motion", "lecture", "motion.pdf", "formula-test.pdf", 100, 3),
        )
        document_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO chunks(document_id,course_id,page_number,content) VALUES (?,?,?,?)",
            [
                (document_id, course_id, 1, "\u52a0\u901f\u5ea6\u5408\u6210\u516c\u5f0f \u76ee\u5f55"),
                (document_id, course_id, 2, "\u52a0\u901f\u5ea6\u5408\u6210\u516c\u5f0f a \uf03d ae + ar + ac"),
                (document_id, course_id, 3, "\u89d2\u901f\u5ea6\u5408\u6210\u516c\u5f0f w \uf03d we + wr"),
            ],
        )
    response = http.post(
        f"/api/courses/{course_id}/search",
        json={"query": "\u52a0\u901f\u5ea6\u5408\u6210\u516c\u5f0f\u662f\u4ec0\u4e48\uff1f", "top_k": 2},
    )
    assert response.status_code == 200
    assert response.json()[0]["page_number"] == 2
