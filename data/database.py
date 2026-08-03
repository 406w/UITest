"""数据访问封装：读取测试所需基础数据（sqlite）。

数据文件：data/test_data.db
表结构：
- sites   站点表（一个网址一行）
- accounts 账号表（一个站点可对应多个账号密码）
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DB_PATH = DATA_DIR / "test_data.db"


class DataBase:
    """测试基础数据访问。"""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ---------------- 站点 ----------------
    def get_sites(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM sites ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def get_site(self, name: str | None = None, url: str | None = None) -> dict | None:
        with self._connect() as conn:
            if name:
                row = conn.execute("SELECT * FROM sites WHERE name = ?", (name,)).fetchone()
            elif url:
                row = conn.execute("SELECT * FROM sites WHERE url = ?", (url,)).fetchone()
            else:
                row = None
        return dict(row) if row else None

    # ---------------- 账号 ----------------
    def get_account(
        self,
        username: str,
        site_name: str | None = None,
        site_url: str | None = None,
    ) -> dict | None:
        """按指定账号名获取账号密码（可限定站点）。

        username 在数据库内唯一时可省略站点参数；否则建议传入站点名/网址。
        """
        with self._connect() as conn:
            if site_name:
                site_row = conn.execute(
                    "SELECT id FROM sites WHERE name = ?", (site_name,)
                ).fetchone()
            elif site_url:
                site_row = conn.execute(
                    "SELECT id FROM sites WHERE url = ?", (site_url,)
                ).fetchone()
            else:
                site_row = None
            if site_row is not None:
                row = conn.execute(
                    "SELECT * FROM accounts WHERE site_id = ? AND username = ?",
                    (site_row["id"], username),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM accounts WHERE username = ?", (username,)
                ).fetchone()
        return dict(row) if row else None

    def get_accounts(self, site_name: str | None = None, site_url: str | None = None) -> list[dict]:
        """获取指定站点的全部账号密码（一个网址可对应多个账号）。"""
        with self._connect() as conn:
            if site_name:
                row = conn.execute(
                    "SELECT id FROM sites WHERE name = ?", (site_name,)
                ).fetchone()
            elif site_url:
                row = conn.execute(
                    "SELECT id FROM sites WHERE url = ?", (site_url,)
                ).fetchone()
            else:
                row = None
            if row is None:
                return []
            rows = conn.execute(
                "SELECT * FROM accounts WHERE site_id = ? ORDER BY is_default DESC, id",
                (row["id"],),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_default_account(self, site_name: str | None = None, site_url: str | None = None) -> dict | None:
        """获取站点默认账号，无默认账号时返回第一个。"""
        accounts = self.get_accounts(site_name=site_name, site_url=site_url)
        if not accounts:
            return None
        return next((a for a in accounts if a["is_default"]), accounts[0])
