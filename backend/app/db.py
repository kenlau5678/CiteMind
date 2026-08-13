import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATA_DIR = Path(os.getenv("CITEMIND_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
DB_PATH = DATA_DIR / "citemind.db"
FILES_DIR = DATA_DIR / "files"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 80),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('lecture', 'notes', 'paper')),
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL UNIQUE,
                size_bytes INTEGER NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                processed_pages INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'processing',
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                content='chunks',
                content_rowid='id',
                tokenize='unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.id, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.id, old.content);
                INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
            END;

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                citations TEXT NOT NULL DEFAULT '[]',
                scope_document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS page_visuals (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                reason TEXT NOT NULL,
                description TEXT,
                model TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id, page_number)
            );
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(documents)")}
        if "processed_pages" not in columns:
            db.execute("ALTER TABLE documents ADD COLUMN processed_pages INTEGER NOT NULL DEFAULT 0")
        db.execute(
            "UPDATE documents SET status='failed', error='Processing was interrupted. Retry to continue.' "
            "WHERE status='processing'"
        )


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def rows(items):
    return [dict(item) for item in items]


def decode_message(row):
    item = dict(row)
    item["citations"] = json.loads(item["citations"])
    return item
