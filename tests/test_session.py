"""Session 登入：Set-Cookie 屬性、登出、CORS 憑證（講義第 10 章）。"""


def test_login_sets_httponly_samesite_cookie(client, user):
    res = client.post("/api/session/login", json=user)
    assert res.status_code == 200
    assert res.json["username"] == user["username"]
    assert "token" not in res.json            # 登入狀態在 Cookie，不在 Body

    set_cookie = res.headers["Set-Cookie"]
    assert set_cookie.startswith("session=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie
    assert "Secure" not in set_cookie         # 本機 http，SESSION_COOKIE_SECURE=False
    assert "Expires" not in set_cookie        # 沒設 permanent：關瀏覽器就消失


def test_me_with_and_without_cookie(client, user):
    assert client.get("/api/session/me").status_code == 401

    client.post("/api/session/login", json=user)   # test client 會自動保存並帶上 Cookie
    res = client.get("/api/session/me")
    assert res.status_code == 200 and res.json["username"] == user["username"]


def test_tampered_cookie_is_ignored(client):
    client.set_cookie("session", "eyJ1c2VyX2lkIjo5OTl9.abc.def")
    assert client.get("/api/session/me").status_code == 401


def test_logout_clears_cookie(client, user):
    client.post("/api/session/login", json=user)
    res = client.post("/api/session/logout")
    assert res.status_code == 204
    assert "Max-Age=0" in res.headers["Set-Cookie"]
    assert client.get("/api/session/me").status_code == 401


def test_wrong_password(client, user):
    res = client.post("/api/session/login", json={**user, "password": "nope"})
    assert res.status_code == 401
    assert "Set-Cookie" not in res.headers


def test_cors_allows_credentials_for_known_origin(client):
    """6-5、10-3：允許清單內的來源，preflight 與正式回應都要帶 Allow-Credentials。"""
    res = client.options("/api/session/login", headers={
        "Origin": "http://127.0.0.1:5500",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert res.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5500"
    assert res.headers["Access-Control-Allow-Credentials"] == "true"

    res = client.get("/api/session/me", headers={"Origin": "http://127.0.0.1:5500"})
    assert res.headers["Access-Control-Allow-Credentials"] == "true"


def test_cors_unknown_origin_gets_no_headers(client):
    res = client.get("/api/fruits", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in res.headers

    # always_send=False：同源請求（沒有 Origin）也不加 CORS 標頭
    res = client.get("/api/fruits")
    assert "Access-Control-Allow-Origin" not in res.headers
