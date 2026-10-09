"""Session 登入（對應講義第 10 章，補充資料）。

和第 9 章的 JWT 用同一張 users 資料表、同一個註冊端點（/api/auth/register），
差別只在「登入狀態」怎麼運送：JWT 由前端存起來、每次放進 Authorization 標頭；
Session 則寫進 Cookie，瀏覽器自動帶，前端沒有東西要存。

  POST /api/session/login   比對密碼，成功就把使用者寫進 session（回應帶 Set-Cookie）
  POST /api/session/logout  清掉 session（回應帶 Set-Cookie 把 Cookie 刪掉）
  GET  /api/session/me      Cookie 有效才回 200，否則 401

Flask 的 session 預設是「用 SECRET_KEY 簽章過的 Cookie」：資料存在瀏覽器，不在伺服器。
和 JWT 一樣，內容只是編碼不是加密，任何人都能解開來看，但改了簽章就對不上。
要把 session 存在伺服器端（資料庫或 Redis），另外裝 Flask-Session 即可，程式碼不用改。
"""

from functools import wraps

from flask import Blueprint, g, session
from werkzeug.security import check_password_hash

from my_ajax_api.db import get_db
from my_ajax_api.errors import ProblemError, parse_body
from my_ajax_api.schemas import LoginDto

bp = Blueprint("session_auth", __name__, url_prefix="/api/session")


def session_required(view):
    """路由裝飾器：session 裡沒有使用者就回 401，不會進到路由本體。

    和 tokens.py 的 login_required 對照：那邊要自己從 Authorization 標頭取出 token 再驗簽章；
    這邊 Flask 在讀取 Cookie 時已經驗過簽章（對不上就當成空的 session），
    所以只要看 session 裡有沒有 user_id。通過後同樣把使用者放進 g.user。
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            raise ProblemError(401, "請先登入")
        g.user = {"id": user_id, "username": session["username"]}
        return view(*args, **kwargs)

    return wrapper


# POST /api/session/login → 200 + Set-Cookie、400 或 401
@bp.post("/login")
def login():
    dto = parse_body(LoginDto)
    row = (
        get_db()
        .execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (dto.username,)
        )
        .fetchone()
    )

    # 和 JWT 版一樣：帳號不存在與密碼錯誤回同一句話，避免帳號列舉
    if row is None or not check_password_hash(row["password_hash"], dto.password):
        raise ProblemError(401, "帳號或密碼錯誤")

    # 先清掉再寫入，不讓上一個使用者的資料殘留在同一個 session 裡
    session.clear()
    session["user_id"] = row["id"]
    session["username"] = row["username"]

    # Flask 會在回應加上 Set-Cookie: session=<簽章過的內容>; HttpOnly; Path=/; SameSite=Lax
    # 沒設 session.permanent，所以是「關閉瀏覽器就消失」的工作階段 Cookie；
    # 要保留幾天可設 session.permanent = True，並在 app.config 設 PERMANENT_SESSION_LIFETIME
    return {"id": row["id"], "username": row["username"]}


# POST /api/session/logout → 204
# 用 POST 而不是 GET：登出會改變狀態，而且 GET 可以被 <img src> 之類的標籤觸發（CSRF）
@bp.post("/logout")
def logout():
    # 清空後 Flask 會回 Set-Cookie 把瀏覽器那份 Cookie 刪掉。
    # 注意：預設的 session 存在用戶端，伺服器沒有名單可以註銷，
    # 被複製走的 Cookie 在伺服器眼裡仍然有效，這點和 JWT 一樣；
    # 要做到「伺服器端立即失效」，得把 session 存到伺服器（Flask-Session）。
    session.clear()
    return "", 204


# GET /api/session/me → 200 或 401
@bp.get("/me")
@session_required
def me():
    return {"id": g.user["id"], "username": g.user["username"]}
