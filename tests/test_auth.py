"""JWT：註冊、登入、token 驗證與受保護的 todos（講義第 9 章）。"""

import jwt


def test_register_201_then_409(client):
    creds = {"username": "newbie", "password": "secret123"}
    res = client.post("/api/auth/register", json=creds)
    assert res.status_code in (201, 409)   # 其他測試可能已建過同一個帳號
    res = client.post("/api/auth/register", json=creds)
    assert res.status_code == 409
    assert res.json["title"] == "帳號已被使用"


def test_register_validation(client):
    res = client.post("/api/auth/register", json={"username": "a", "password": "123"})
    assert res.status_code == 400
    assert res.json["errors"]["username"] == ["帳號長度須為 3 到 20 字"]
    assert res.json["errors"]["password"] == ["密碼至少 6 個字元"]


def test_login_returns_token(client, user):
    res = client.post("/api/auth/login", json=user)
    assert res.status_code == 200
    body = res.json
    assert body["username"] == user["username"]
    assert body["expiresAt"].endswith("Z")
    # 9-1：Payload 只是編碼，不驗簽章也能讀；sub 是字串
    claims = jwt.decode(body["token"], options={"verify_signature": False})
    assert claims["name"] == user["username"] and isinstance(claims["sub"], str)


def test_login_wrong_password_and_unknown_user_same_message(client, user):
    """帳號列舉防範：兩種失敗回同一句話。"""
    wrong = client.post("/api/auth/login", json={**user, "password": "nope"})
    unknown = client.post("/api/auth/login", json={"username": "ghost_user", "password": "x"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json["title"] == unknown.json["title"] == "帳號或密碼錯誤"
    assert wrong.headers["WWW-Authenticate"] == "Bearer"


def test_me_requires_valid_token(client, auth_headers):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401

    tampered = auth_headers["Authorization"][:-4] + "xxxx"
    res = client.get("/api/auth/me", headers={"Authorization": tampered})
    assert res.status_code == 401 and res.json["title"] == "無效的 token"

    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200 and res.json["username"] == "tester"


def test_expired_token(client, app, user):
    """自己簽一個已過期的 token，驗證要回「登入已過期」。"""
    from datetime import datetime, timedelta, timezone
    cfg = app.config
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "1", "name": user["username"], "iss": cfg["JWT_ISSUER"],
         "aud": cfg["JWT_AUDIENCE"], "iat": past - timedelta(minutes=1), "exp": past},
        cfg["JWT_KEY"], algorithm="HS256",
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401 and res.json["title"] == "登入已過期，請重新登入"


def test_todos_need_login(client, auth_headers):
    assert client.get("/api/todos").status_code == 401
    assert client.post("/api/todos", json={"title": "x"}).status_code == 401

    res = client.post("/api/todos", json={"title": "買菜"}, headers=auth_headers)
    assert res.status_code == 201
    todo = res.json
    assert todo["isDone"] is False
    assert res.headers["Location"].endswith(f"/api/todos/{todo['id']}")

    assert client.patch(f"/api/todos/{todo['id']}", json={"isDone": True},
                        headers=auth_headers).status_code == 204
    assert client.get(f"/api/todos/{todo['id']}", headers=auth_headers).json["isDone"] is True
    assert client.delete(f"/api/todos/{todo['id']}", headers=auth_headers).status_code == 204


def test_todo_title_required(client, auth_headers):
    res = client.post("/api/todos", json={"title": "  "}, headers=auth_headers)
    assert res.status_code == 400
    assert res.json["errors"]["title"] == ["標題不可為空"]
