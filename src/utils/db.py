"""
数据库接口
SQLite (开发) / PostgreSQL (生产)
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class Database:
    """轻量级数据库封装"""

    def __init__(self, db_path: str = "data/ops.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS collected_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                data_type TEXT NOT NULL,
                sku_id TEXT DEFAULT '',
                title TEXT DEFAULT '',
                value TEXT DEFAULT '',
                extra TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                action TEXT NOT NULL,
                params TEXT DEFAULT '{}',
                status TEXT DEFAULT 'pending',
                approved_by TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER REFERENCES decisions(id),
                result TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def insert_data(self, platform: str, data_type: str, title: str, value: str, **kwargs):
        self.conn.execute(
            "INSERT INTO collected_data (platform, data_type, title, value, extra) VALUES (?,?,?,?,?)",
            (platform, data_type, title, value, json.dumps(kwargs, ensure_ascii=False))
        )
        self.conn.commit()

    def query_recent(self, platform: str = None, limit: int = 100) -> List[Dict]:
        if platform:
            rows = self.conn.execute(
                "SELECT * FROM collected_data WHERE platform=? ORDER BY id DESC LIMIT ?",
                (platform, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM collected_data ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
