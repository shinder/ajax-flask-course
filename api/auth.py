"""JWT 登入流程的三個端點（對應講義 9-6）：
  POST /api/auth/register  註冊（密碼雜湊後存入 users）
  POST /api/auth/login     登入（比對密碼，成功就簽發 token）
  GET  /api/auth/me        需帶 token，回傳目前登入者（用來確認 token 有效）
"""

import sqlite3

from flask import Blueprint, g
from werkzeug.security import check_password_hash, generate_password_hash

from auth import create_token, login_required
from db import get_db, utc_now_iso
from errors import ProblemError, parse_body
from schemas import LoginDto, RegisterDto

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# POST /api/auth/register → 201、400 或 409
@bp.post("/register")
def register():
    dto = parse_body(RegisterDto)
    db = get_db()

    # 先查一次帳號是否重複，給使用者友善的 409 訊息
    exists = db.execute("SELECT 1 FROM users WHERE username = ?", (dto.username,)).fetchone()
    if exists:
        raise ProblemError(409, "帳號已被使用")

    # generate_password_hash 會自動產生隨機 salt，和演算法參數一起編進結果字串，
    # 所以同一組密碼每次雜湊出來的字串都不同，也不需要另外存 salt。
    # Werkzeug 預設用 scrypt；結果長得像 scrypt:32768:8:1$<salt>$<hash>
    password_hash = generate_password_hash(dto.password)
    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (dto.username, password_hash, utc_now_iso()),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # 兩個請求同時註冊同一個帳號時，上面的 SELECT 可能都通過，
        # 最後靠資料表的 UNIQUE 約束擋下第二筆；這裡把它轉成同樣的 409
        raise ProblemError(409, "帳號已被使用") from None

    # 註冊成功回 201。不直接回 token，讓「註冊」和「登入」兩個動作分開，流程比較清楚
    return {"id": cursor.lastrowid, "username": dto.username}, 201, {"Location": "/api/auth/me"}


# POST /api/auth/login → 200 + token、400 或 401
@bp.post("/login")
def login():
    dto = parse_body(LoginDto)
    row = get_db().execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?", (dto.username,)
    ).fetchone()

    # 帳號不存在與密碼錯誤「一律」回同一句話，
    # 不要讓攻擊者能透過訊息差異判斷哪些帳號存在（帳號列舉攻擊）。
    # check_password_hash 會從雜湊字串取出 salt 與參數，用同樣的方式重算後比對。
    if row is None or not check_password_hash(row["password_hash"], dto.password):
        raise ProblemError(401, "帳號或密碼錯誤")

    token, expires_at = create_token(row["id"], row["username"])
    return {
        "token": token,
        "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
        "username": row["username"],
    }


# GET /api/auth/me → 200 或 401
# @login_required：沒有帶 token、token 過期或簽章不符，裝飾器會直接回 401，
# 根本不會進到這個函式。能進來就代表 token 有效，使用者資訊已放在 g.user。
@bp.get("/me")
@login_required
def me():
    return {"id": g.user["id"], "username": g.user["username"]}
