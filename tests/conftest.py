"""pytest 的共用設定與 fixture。

用 Flask 內建的 test client 直接呼叫路由，不用啟動伺服器、不用瀏覽器，
每個測試對應 api.http 裡的一條請求，是「API 契約的程式碼版」。
執行：uv run pytest

create_app() 接受 test_config，所以測試用的金鑰、資料庫路徑直接傳進去，
不碰 .env 也不碰開發用的 instance/app.db。這就是工廠函式比模組層級的 app 好測的地方。
"""

import pytest

from my_ajax_api import create_app
from my_ajax_api.api import fruits as fruits_module


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """整個測試過程共用一個 app，資料庫與上傳目錄指到暫存資料夾。"""
    tmp = tmp_path_factory.mktemp("data")
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp / "test.db"),
            "UPLOAD_DIR": str(tmp / "uploads"),
            # 固定的測試金鑰，和 .env 無關，CI 環境沒有 .env 也能跑
            "JWT_KEY": "test-jwt-key-" + "x" * 32,
            "SECRET_KEY": "test-secret-key-" + "y" * 32,
            "JWT_EXPIRE_MINUTES": 60,
        }
    )


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
