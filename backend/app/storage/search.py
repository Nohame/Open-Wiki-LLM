import sqlite3
from pathlib import Path


class SearchIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS wiki_pages_fts
                USING fts5(slug, title, content, tags)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS page_references (
                    page_slug TEXT NOT NULL,
                    source_slug TEXT NOT NULL,
                    PRIMARY KEY (page_slug, source_slug)
                )
            """)

    def index_page(self, slug: str, title: str, content: str, tags: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM wiki_pages_fts WHERE slug = ?", (slug,)
            )
            conn.execute(
                "INSERT INTO wiki_pages_fts(slug, title, content, tags) VALUES (?, ?, ?, ?)",
                (slug, title, content, tags),
            )

    def search(self, query: str, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT slug, title,
                       snippet(wiki_pages_fts, 2, '<b>', '</b>', '...', 20) as snippet,
                       rank
                FROM wiki_pages_fts
                WHERE wiki_pages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [
            {"slug": r[0], "title": r[1], "snippet": r[2], "score": r[3]}
            for r in rows
        ]

    def rebuild(self, pages: list[dict]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM wiki_pages_fts")
        for page in pages:
            self.index_page(
                slug=page["slug"],
                title=page["title"],
                content=page["content"],
                tags=" ".join(page.get("tags", [])),
            )
