-- 資料表結構（對應講義第 7 章）。
-- 用 IF NOT EXISTS 讓這份腳本可以重複執行：app.py 啟動時會跑一次，確保資料表存在；
-- 要整個重建（清空資料）用 `uv run flask init-db`。
--
-- SQLite 的型別是「親和性」而非嚴格型別：
--   NUMERIC 存 15 會是整數、存 15.5 會是浮點數，讀回 Python 時分別是 int 與 float，
--   序列化成 JSON 就是 15 與 15.5，和前端送來的樣子一致。
--   沒有布林與日期型別：is_done 用 INTEGER 0/1，created_at 用 ISO 8601 的 TEXT。

CREATE TABLE IF NOT EXISTS products (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    price      NUMERIC NOT NULL,
    image_url  TEXT,                        -- 可為 NULL（選填）
    created_at TEXT    NOT NULL             -- UTC，例如 2026-10-08T03:17:31.123456+00:00
);

CREATE TABLE IF NOT EXISTS todos (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    title   TEXT    NOT NULL,
    is_done INTEGER NOT NULL DEFAULT 0      -- 0 = 未完成，1 = 已完成
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,  -- 唯一索引：兩個請求同時註冊同一帳號也擋得住
    password_hash TEXT    NOT NULL,         -- 只存雜湊，絕不存明文
    created_at    TEXT    NOT NULL
);
