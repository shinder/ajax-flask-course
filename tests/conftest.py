"""pytest 的共用設定與 fixture。

用 Flask 內建的 test client 直接呼叫路由，不用啟動伺服器、不用瀏覽器，
每個測試對應 api.http 裡的一條請求，是「API 契約的程式碼版」。
執行：uv run pytest

app.py 在 import 時就會讀 .env 並檢查金鑰，所以環境變數要在 import 之前設好；
這也是 app 在模組層級建立的不便之處，正式專案常改成 create_app() 工廠函式（講義附錄 B）。
"""

import os

import pytest

# 必須在 import app 之前：固定的測試金鑰，和 .env 無關，CI 環境沒有 .env 也能跑
os.environ["JWT_KEY"] = "test-jwt-key-" + "x" * 32
os.environ["SECRET_KEY"] = "test-secret-key-" + "y" * 32
os.environ["JWT_EXPIRE_MINUTES"] = "60"

from app import app as flask_app  # noqa: E402
from api import fruits as fruits_module  # noqa: E402
from db import init_db  # noqa: E402


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """整個測試過程共用一個 app，但資料庫與上傳目錄指到暫存資料夾，不碰開發用的 app.db。"""
    tmp = tmp_path_factory.mktemp("data")
    flask_app.config.update(
        TESTING=True,
        DATABASE=str(tmp / "test.db"),
        UPLOAD_DIR=str(tmp / "uploads"),
    )
    with flask_app.app_context():
        init_db()
    return flask_app


@pytest.fixture
def client(app):
    """每個測試一個新的 client：Cookie 不會跨測試殘留。"""
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_fruits():
    """水果是模組層級的 list，測試之間要還原，否則新增、刪除會互相影響。"""
    original = [dict(f) for f in fruits_module.fruits]
    original_next_id = fruits_module._next_id
    yield
    fruits_module.fruits[:] = original
    fruits_module._next_id = original_next_id


@pytest.fixture
def user(client):
    """註冊一個帳號並回傳帳密；帳號已存在（同一個 session 的其他測試建過）也沒關係。"""
    creds = {"username": "tester", "password": "secret123"}
    client.post("/api/auth/register", json=creds)
    return creds


@pytest.fixture
def auth_headers(client, user):
    """用 JWT 登入，回傳可直接塞進請求的 Authorization 標頭。"""
    res = client.post("/api/auth/login", json=user)
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json['token']}"}
