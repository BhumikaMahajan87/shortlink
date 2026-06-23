"""Storage backends for links and click analytics.

Two interchangeable implementations sit behind the ``Storage`` interface:

* ``MemoryStorage`` - thread-safe in-memory store, zero configuration
* ``SqliteStorage`` - persistent store backed by SQLite

The service layer depends only on the interface, so swapping in PostgreSQL,
Redis, or a sharded store later means writing one new class.
"""

from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Link:
    code: str
    long_url: str
    created_at: str
    clicks: int = 0


@dataclass
class ClickEvent:
    code: str
    timestamp: str
    referer: str | None = None
    user_agent: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage(ABC):
    @abstractmethod
    def next_id(self) -> int:
        """Return a unique, monotonically increasing id."""

    @abstractmethod
    def save_link(self, link: Link) -> None: ...

    @abstractmethod
    def get_link(self, code: str) -> Link | None: ...

    @abstractmethod
    def find_by_url(self, long_url: str) -> Link | None: ...

    @abstractmethod
    def record_click(self, event: ClickEvent) -> None: ...

    @abstractmethod
    def recent_clicks(self, code: str, limit: int = 50) -> list[ClickEvent]: ...

    @abstractmethod
    def total_links(self) -> int: ...


class MemoryStorage(Storage):
    def __init__(self, id_start: int = 100_000) -> None:
        self._lock = threading.Lock()
        self._counter = id_start
        self._links: dict[str, Link] = {}
        self._by_url: dict[str, str] = {}
        self._clicks: dict[str, list[ClickEvent]] = {}

    def next_id(self) -> int:
        with self._lock:
            value = self._counter
            self._counter += 1
            return value

    def save_link(self, link: Link) -> None:
        with self._lock:
            self._links[link.code] = link
            self._by_url[link.long_url] = link.code

    def get_link(self, code: str) -> Link | None:
        return self._links.get(code)

    def find_by_url(self, long_url: str) -> Link | None:
        code = self._by_url.get(long_url)
        return self._links.get(code) if code else None

    def record_click(self, event: ClickEvent) -> None:
        with self._lock:
            link = self._links.get(event.code)
            if link:
                link.clicks += 1
            self._clicks.setdefault(event.code, []).append(event)

    def recent_clicks(self, code: str, limit: int = 50) -> list[ClickEvent]:
        return list(reversed(self._clicks.get(code, [])))[:limit]

    def total_links(self) -> int:
        return len(self._links)


class SqliteStorage(Storage):
    def __init__(self, path: str, id_start: int = 100_000) -> None:
        self._path = path
        self._id_start = id_start
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS links (
                    code TEXT PRIMARY KEY,
                    long_url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    clicks INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_links_url ON links(long_url);

                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    referer TEXT,
                    user_agent TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_clicks_code ON clicks(code);

                CREATE TABLE IF NOT EXISTS counter (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    value INTEGER NOT NULL
                );
                """
            )
            row = self._conn.execute("SELECT value FROM counter WHERE id = 1").fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO counter (id, value) VALUES (1, ?)", (self._id_start,)
                )

    def next_id(self) -> int:
        with self._lock, self._conn:
            row = self._conn.execute("SELECT value FROM counter WHERE id = 1").fetchone()
            value = int(row["value"])
            self._conn.execute("UPDATE counter SET value = ? WHERE id = 1", (value + 1,))
            return value

    def save_link(self, link: Link) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO links (code, long_url, created_at, clicks) "
                "VALUES (?, ?, ?, ?)",
                (link.code, link.long_url, link.created_at, link.clicks),
            )

    def get_link(self, code: str) -> Link | None:
        row = self._conn.execute(
            "SELECT code, long_url, created_at, clicks FROM links WHERE code = ?", (code,)
        ).fetchone()
        return self._row_to_link(row)

    def find_by_url(self, long_url: str) -> Link | None:
        row = self._conn.execute(
            "SELECT code, long_url, created_at, clicks FROM links WHERE long_url = ?",
            (long_url,),
        ).fetchone()
        return self._row_to_link(row)

    def record_click(self, event: ClickEvent) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO clicks (code, timestamp, referer, user_agent) VALUES (?, ?, ?, ?)",
                (event.code, event.timestamp, event.referer, event.user_agent),
            )
            self._conn.execute("UPDATE links SET clicks = clicks + 1 WHERE code = ?", (event.code,))

    def recent_clicks(self, code: str, limit: int = 50) -> list[ClickEvent]:
        rows = self._conn.execute(
            "SELECT code, timestamp, referer, user_agent FROM clicks "
            "WHERE code = ? ORDER BY id DESC LIMIT ?",
            (code, limit),
        ).fetchall()
        return [
            ClickEvent(
                code=r["code"],
                timestamp=r["timestamp"],
                referer=r["referer"],
                user_agent=r["user_agent"],
            )
            for r in rows
        ]

    def total_links(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM links").fetchone()["c"])

    @staticmethod
    def _row_to_link(row: sqlite3.Row | None) -> Link | None:
        if row is None:
            return None
        return Link(
            code=row["code"],
            long_url=row["long_url"],
            created_at=row["created_at"],
            clicks=int(row["clicks"]),
        )


def build_storage(backend: str, sqlite_path: str, id_start: int) -> Storage:
    if backend == "sqlite":
        return SqliteStorage(sqlite_path, id_start=id_start)
    return MemoryStorage(id_start=id_start)
