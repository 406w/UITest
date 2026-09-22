import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Account:
    username: str
    password: str = field(repr=False)
    expected_display_name: str = ""


class Database:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)

    def initialize(self, yaml_path):
        data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("测试数据必须为映射")
        seen = set()
        for kind, records in data.items():
            if kind not in {"accounts", "orders"} or not isinstance(records, list):
                raise ValueError(f"未知数据类型：{kind}")
            for row in records:
                if not isinstance(row, dict) or not row.get("key"):
                    raise ValueError("数据行缺少 key")
                identity = kind, row["key"]
                if identity in seen:
                    raise ValueError(f"重复数据 key：{identity}")
                seen.add(identity)
                if kind == "accounts" and ("password" in row or not row.get("password_env")):
                    raise ValueError("账号只能保存 password_env，不保存明文密码")
        with self.connection:
            self.connection.execute("CREATE TABLE IF NOT EXISTS test_data(kind TEXT, key TEXT, payload TEXT NOT NULL, PRIMARY KEY(kind,key))")
            for kind, records in data.items():
                for row in records:
                    self._save(kind, row)

    def _save(self, kind, row):
        self.connection.execute("INSERT INTO test_data VALUES(?,?,?) ON CONFLICT(kind,key) DO UPDATE SET payload=excluded.payload",
                                (kind, row["key"], json.dumps(row, ensure_ascii=False)))

    def get(self, kind, key):
        row = self.connection.execute("SELECT payload FROM test_data WHERE kind=? AND key=?", (kind, key)).fetchone()
        if row is None:
            raise KeyError(f"未找到测试数据：{kind}/{key}")
        return json.loads(row[0])

    def account(self, key: str) -> Account:
        row = self.get("accounts", key)
        password = os.environ.get(row["password_env"])
        if not password:
            raise ValueError(f"请设置环境变量 {row['password_env']}")
        return Account(row["username"], password, row["expected_display_name"])

    def save_account(self, row):
        if "password" in row or not all(row.get(k) for k in ("key", "username", "password_env", "expected_display_name")):
            raise ValueError("账号字段不完整或包含明文密码")
        with self.connection:
            self._save("accounts", row)

    def close(self):
        self.connection.close()
