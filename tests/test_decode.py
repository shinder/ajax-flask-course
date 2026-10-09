"""flask decode jwt / session 終端機工具（講義 9-8、10-1）。"""

from flask import session as flask_session


def _login_token(client, user):
    return client.post("/api/auth/login", json=user).json["token"]


def test_decode_jwt_valid(app, client, user):
    token = _login_token(client, user)
    result = app.test_cli_runner().invoke(args=["decode", "jwt", token])
    assert result.exit_code == 0, result.output
    assert '"alg": "HS256"' in result.output
    assert f'"name": "{user["username"]}"' in result.output
    assert "exp =" in result.output and "還有" in result.output
    assert "用 JWT_KEY 驗證：正確" in result.output


def test_decode_jwt_tampered(app, client, user):
    token = _login_token(client, user)
    header, payload, sig = token.split(".")
    tampered = f"{header}.{payload}.{sig[:-3]}abc"
    result = app.test_cli_runner().invoke(args=["decode", "jwt", tampered])
    assert result.exit_code == 0
    assert "不正確" in result.output


def test_decode_jwt_wrong_shape(app):
    result = app.test_cli_runner().invoke(args=["decode", "jwt", "not-a-token"])
    assert result.exit_code != 0
    assert "三段" in result.output


def test_decode_session_valid(app, client, user):
    res = client.post("/api/session/login", json=user)
    cookie = res.headers["Set-Cookie"].split(";")[0].removeprefix("session=")
    result = app.test_cli_runner().invoke(args=["decode", "session", cookie])
    assert result.exit_code == 0, result.output
    assert f'"username": "{user["username"]}"' in result.output
    assert "Timestamp" in result.output
    assert "用 SECRET_KEY 驗證：正確" in result.output


def test_decode_session_tampered(app, client, user):
    res = client.post("/api/session/login", json=user)
    cookie = res.headers["Set-Cookie"].split(";")[0].removeprefix("session=")
    payload, ts, sig = cookie.split(".")
    # 把 user_id 改掉：內容解得開，但簽章對不上
    result = app.test_cli_runner().invoke(
        args=["decode", "session", f"eyJ1c2VyX2lkIjo5OTl9.{ts}.{sig}"])
    assert result.exit_code == 0
    assert '"user_id": 999' in result.output
    assert "不正確" in result.output


def test_decode_session_compressed(app):
    """內容長的 session 會被 zlib 壓縮，Cookie 值以 . 開頭。"""
    with app.test_request_context():
        flask_session["blob"] = "x" * 2000
        serializer = app.session_interface.get_signing_serializer(app)
        cookie = serializer.dumps(dict(flask_session))
    assert cookie.startswith(".")
    result = app.test_cli_runner().invoke(args=["decode", "session", cookie])
    assert result.exit_code == 0, result.output
    assert "zlib 壓縮過" in result.output and "正確" in result.output
