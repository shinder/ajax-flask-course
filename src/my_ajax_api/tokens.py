"""JWT 的簽發與驗證（對應講義第 9 章）。

JWT 由三段組成：Header.Payload.Signature，各自 Base64Url 編碼後用 . 連接。
  Header    ：演算法（HS256）與型別（JWT）
  Payload   ：claims，也就是「這個 token 代表誰、什麼時候到期」。注意 Payload 只是編碼不是加密，
              任何人都能解開來看（login.html 就示範了），所以不要放密碼等敏感資料。
  Signature ：用金鑰對前兩段做 HMAC，伺服器驗證時重算一次比對，確保內容沒被竄改。

金鑰（JWT_KEY）放在 .env，不進 git；create_app() 啟動時檢查長度，沒設就直接失敗，比執行到登入才出錯好找問題。
"""

import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request

from my_ajax_api.errors import ProblemError


def create_token(user_id: int, username: str) -> tuple[str, datetime]:
    """簽發 token，回傳 (token 字串, 到期時間)。"""
    cfg = current_app.config
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=cfg["JWT_EXPIRE_MINUTES"])

    # claims：放進 Payload 的鍵值對。
    #   sub（subject）放使用者 id（RFC 7519 規定要是字串）、name 放帳號，
    #   jti（JWT ID）給每個 token 唯一識別碼，正式專案可用來做登出黑名單。
    #   iss / aud / iat / exp 是標準欄位，驗證時會逐一檢查。
    payload = {
        "sub": str(user_id),
        "name": username,
        "jti": uuid.uuid4().hex,
        "iss": cfg["JWT_ISSUER"],
        "aud": cfg["JWT_AUDIENCE"],
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, cfg["JWT_KEY"], algorithm="HS256")
    return token, expires_at


def _decode_token(token: str) -> dict:
    """驗證簽章、簽發者、接收者與到期時間；任何一項不符都丟出 InvalidTokenError。"""
    cfg = current_app.config
    return jwt.decode(
        token,
        cfg["JWT_KEY"],
        algorithms=["HS256"],          # 明確指定，避免「alg: none」之類的攻擊
        issuer=cfg["JWT_ISSUER"],
        audience=cfg["JWT_AUDIENCE"],
        leeway=0,                      # 不容許時鐘誤差，讓到期時間精準（前後端在同一台機器）
    )


def login_required(view):
    """路由裝飾器：沒帶 token、token 過期或簽章不符，一律回 401，不會進到路由本體。

    驗證通過後把使用者資訊放進 g.user，路由裡用 g.user["id"] 取得。
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ProblemError(401, "請先登入")
        try:
            claims = _decode_token(token)
        except jwt.ExpiredSignatureError:
            raise ProblemError(401, "登入已過期，請重新登入") from None
        except jwt.InvalidTokenError:
            raise ProblemError(401, "無效的 token") from None

        g.user = {"id": int(claims["sub"]), "username": claims["name"]}
        return view(*args, **kwargs)

    return wrapper
