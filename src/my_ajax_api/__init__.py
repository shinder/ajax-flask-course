"""my_ajax_api 套件的進入點：create_app() 工廠函式（對應講義第 2 章）。

啟動方式（擇一）：
    uv run flask run        # .flaskenv 的 FLASK_APP=my_ajax_api，Flask 會自動呼叫 create_app()
    uv run my-ajax-api      # pyproject.toml [project.scripts] 指到下面的 main()

第一次啟動前先把 .env.example 複製成 .env 並填入 JWT_KEY 與 SECRET_KEY（見 README）。

為什麼用工廠函式而不是模組層級的 app = Flask(__name__)：
  - 測試可以用不同的設定建立多個 app（tests/conftest.py），不必靠環境變數繞路
  - import 這個套件不會有副作用（不會連資料庫、不會讀 .env）
  - Flask 的 flask run 看到套件名會自動找 create_app，不用多設定
"""

import os
import secrets
from pathlib import Path

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS

from my_ajax_api import db, errors
from my_ajax_api.api import auth, basics, fruits, notifications, products, session_auth, todos

# 這個檔案在 src/my_ajax_api/ 底下，往上兩層就是專案根目錄（有 pyproject.toml 的那層）
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(test_config: dict | None = None) -> Flask:
    """建立並組裝 Flask app。test_config 給測試用，會覆蓋預設設定。"""

    # static_url_path="" 讓套件裡 static/ 底下的檔案直接對應到網站根目錄：
    #   static/css/style.css → /css/style.css、static/020-xhr.html → /020-xhr.html
    # static_folder 預設就是套件旁的 static/
    # instance_path：Flask 慣例的「執行期資料」資料夾，放資料庫這類不進 git 的檔案
    app = Flask(__name__, static_url_path="", instance_path=str(PROJECT_ROOT / "instance"))

    # ════════════════════════════════════════════════════════════
    # 第一區：設定
    # ════════════════════════════════════════════════════════════
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "app.db"),
        UPLOAD_DIR=os.path.join(app.root_path, "static", "uploads"),   # 6-1 上傳檔案放 static 底下讓瀏覽器能直接開
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,    # 整個請求最多 2 MB，超過時 Flask 回 413（6-1 檔案上傳）
        JWT_ISSUER="FlaskAjaxApi",              # 簽發者，通常填 API 的名稱或網址
        JWT_AUDIENCE="FlaskAjaxApiClient",      # 接收者，通常填前端的名稱或網址
        JWT_EXPIRE_MINUTES=int(os.environ.get("JWT_EXPIRE_MINUTES", "60")),
        JWT_KEY=os.environ.get("JWT_KEY", ""),  # 簽章用的對稱金鑰，放 .env 不進 git
        # Session 登入（第 10 章）：Flask 的 session 是簽章過的 Cookie，SECRET_KEY 就是簽章金鑰。
        # 和 JWT_KEY 分開設，兩種機制各用各的金鑰，其中一把外洩不影響另一邊
        SECRET_KEY=os.environ.get("SECRET_KEY", ""),
        SESSION_COOKIE_HTTPONLY=True,     # JavaScript 讀不到這個 Cookie（Flask 預設就是 True，寫出來強調）
        SESSION_COOKIE_SAMESITE="Lax",    # 跨站的 POST 不會帶上 Cookie，擋掉大部分 CSRF（10-4）
        SESSION_COOKIE_SECURE=False,      # 本機用 http 所以關閉；正式環境走 https 一定要 True
    )
    if test_config:
        app.config.update(test_config)

    # JSON 輸出設定。app.json 的型別標註是抽象的 JSONProvider，上面沒有這兩個屬性；
    # 明確換成 Flask 內建的 DefaultJSONProvider，型別檢查器才認得
    app.json = DefaultJSONProvider(app)
    app.json.ensure_ascii = False   # JSON 裡的中文直接輸出，不轉成 \uXXXX
    app.json.sort_keys = False      # 維持 dict 原本的欄位順序，方便對照（Flask 預設會依字母排序）

    # 金鑰沒設定或太短就在啟動時直接失敗，比執行到登入才出錯好找問題（HMAC-SHA256 至少 32 bytes）
    for key_name in ("JWT_KEY", "SECRET_KEY"):
        if len(app.config[key_name].encode()) < 32:
            raise RuntimeError(
                f"{key_name} 未設定或太短。請把 .env.example 複製成 .env，並填入至少 32 個字元的隨機字串，例如：\n"
                f"  {key_name}={secrets.token_urlsafe(48)}"
            )

    # instance/ 不進 git，第一次啟動時要先建出來，資料庫才有地方放
    os.makedirs(app.instance_path, exist_ok=True)

    # ════════════════════════════════════════════════════════════
    # 第二區：掛上擴充與各個 Blueprint（順序不影響路由比對）
    # ════════════════════════════════════════════════════════════

    # CORS（跨來源資源共用，6-5）：瀏覽器的同源政策會擋住不同 port 的請求，
    # 例如前端在 :5500、後端在 :8000，需要明確允許才能通。只開放 /api/ 底下的路徑；
    # always_send=False：同源請求（沒有 Origin 標頭）就不加 CORS 標頭，DevTools 看起來才乾淨。
    # supports_credentials=True：允許跨來源請求帶 Cookie（第 10 章的 Session 登入從 Live Server 測時需要），
    # 此時 origins 不能用 "*"，瀏覽器會拒絕「萬用字元 + 憑證」的組合（6-4）。
    CORS(app, always_send=False, supports_credentials=True, resources={r"/api/*": {"origins": [
        "http://localhost:5500",      # VS Code Live Server
        "http://127.0.0.1:5500",
        "http://localhost:3000",      # 其他常見開發 port
    ]}})

    db.init_app(app)          # 請求結束關連線、flask init-db 指令、啟動時建表
    errors.init_app(app)      # 400/401/404/500 統一回 JSON（8-3）

    # 每個 api/*.py 定義一個 Blueprint（變數名統一叫 bp），這裡一行掛一組路由（3-5）
    app.register_blueprint(basics.bp)          # GET  /api/basics                 3-1
    app.register_blueprint(fruits.bp)          # CRUD /api/fruits（In-Memory）      3-4、5-8、4-3、6-1
    app.register_blueprint(todos.bp)           # CRUD /api/todos（SQLite，需登入）   6-6、7-4、9-5
    app.register_blueprint(products.bp)        # CRUD /api/products（SQLite）        7-4
    app.register_blueprint(notifications.bp)   # SSE  /api/notifications/stream    6-2
    app.register_blueprint(auth.bp)            # JWT  /api/auth/*                  9-6
    app.register_blueprint(session_auth.bp)    # Session /api/session/*            10-2（補充）

    # 根路徑導向首頁：/ → static/index.html
    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    # API 文件（2-5）：Swagger UI 讀 static/openapi.yaml。規格是手寫的，Flask 不會自動產生
    @app.get("/swagger")
    def swagger():
        return app.send_static_file("swagger.html")

    return app


def main():
    """uv run my-ajax-api 的進入點：不經過 flask 指令，直接跑開發伺服器。"""
    from dotenv import load_dotenv

    # flask run 會自己讀 .env；這裡自己跑所以要手動讀。已存在的環境變數不會被覆蓋
    load_dotenv(PROJECT_ROOT / ".env")
    create_app().run(port=8000, debug=True)
