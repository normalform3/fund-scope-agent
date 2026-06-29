import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class SQLiteCache:
    def __init__(self, path: str = "data/fundscope.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def get(self, key: str, max_age_seconds: int) -> Optional[Any]:
        with sqlite3.connect(str(self.path)) as conn:
            row = conn.execute("select payload, updated_at from cache where key = ?", (key,)).fetchone()
        if not row:
            return None
        payload, updated_at = row
        if time.time() - float(updated_at) > max_age_seconds:
            return None
        return json.loads(payload)

    def set(self, key: str, payload: Any) -> None:
        serialized = json.dumps(payload, ensure_ascii=False)
        with sqlite3.connect(str(self.path)) as conn:
            conn.execute(
                """
                insert into cache(key, payload, updated_at)
                values(?, ?, ?)
                on conflict(key) do update set payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (key, serialized, time.time()),
            )
            conn.commit()

    def _init_schema(self) -> None:
        with sqlite3.connect(str(self.path)) as conn:
            conn.execute(
                """
                create table if not exists cache (
                    key text primary key,
                    payload text not null,
                    updated_at real not null
                )
                """
            )
            conn.commit()

