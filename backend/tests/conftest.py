import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CITEMIND_DATA_DIR", str(tmp_path / "data"))
    for name in ["app.main", "app.db"]:
        sys.modules.pop(name, None)
    import app.db
    import app.main
    importlib.reload(app.db)
    importlib.reload(app.main)
    monkeypatch.setattr(app.main.ai, "embed", lambda texts: [[float(len(text) % 7), 1.0, 0.5] for text in texts])
    with TestClient(app.main.app) as test_client:
        yield test_client, app.main, app.db


@pytest.fixture()
def sample_pdf():
    import fitz
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 90), "Neural networks learn representations from training data. Backpropagation computes gradients.")
    page = pdf.new_page()
    page.insert_text((72, 90), "Convolution shares weights across spatial locations. This reduces the parameter count.")
    data = pdf.tobytes()
    pdf.close()
    return data

