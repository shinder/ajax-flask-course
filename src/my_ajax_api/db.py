"""SQLite 連線管理（對應講義第 7 章）。

用標準庫 sqlite3 直接寫 SQL，不用 ORM：
  - get_db()：取得「這個請求專用」的連線，存在 flask.g 裡，同一請求內重複呼叫拿到同一條
  - 請求結束時 close_db() 自動關閉，連線不會洩漏
  - init_db()：依 schema.sql 建表；`flask init-db` 指令會先刪掉舊檔再重建
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import Flask, current_app, g

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        # 查詢結果可以用欄位名存取（row["name"]），也能直接 dict(row) 轉成字典
        g.db.row_factory = sqlite3.Row
        # 啟用外鍵約束（SQLite 預設關閉）；本範例沒有外鍵，但養成習慣
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """依 schema.sql 建立資料表（已存在的不會動）。"""
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    db.commit()


def utc_now_iso() -> str:
    """寫入資料庫用的現在時間：UTC、ISO 8601。
    一律存 UTC、顯示時才轉本地，前端 new Date() 會依使用者時區換算（講義 5-7）。"""
    return datetime.now(timezone.utc).isoformat()


@click.command("init-db")
def init_db_command():
    """刪掉現有資料庫並重建所有資料表（資料會清空）。"""
    db_path = Path(current_app.config["DATABASE"])
    close_db()
    db_path.unlink(missing_ok=True)
    init_db()
    click.echo(f"已重建資料庫：{db_path}")


def init_app(app: Flask):
    """掛到 app 上：請求結束關連線、註冊 CLI 指令、啟動時確保資料表存在。"""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # 第一次啟動自動建表，不必手動跑指令。
    # schema.sql 用了 IF NOT EXISTS，所以每次啟動執行也安全。
    with app.app_context():
        init_db()
