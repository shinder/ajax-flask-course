"""應用程式入口：建立 Flask app、載入設定、掛上各個模組（對應講義第 2 章）。

啟動方式（擇一）：
    uv run flask run        # 讀 .flaskenv 的 FLASK_RUN_PORT=5269、FLASK_DEBUG=1
    uv run app.py           # 跑最底下的 app.run()

第一次啟動前先把 .env.example 複製成 .env 並填入 JWT_KEY（見 README）。
"""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS

import db
import errors
from api import auth, basics, fruits, notifications, products, todos

BASE_DIR = Path(__file__).parent

# 讀取 .env（JWT_KEY 等機密）。用 flask run 啟動時 Flask 會自己讀，
# 這裡再讀一次是為了 uv run app.py 也能用。已存在的環境變數不會被覆蓋。
load_dotenv(BASE_DIR / ".env")

# static_url_path="" 讓 static/ 底下的檔案直接對應到網站根目錄：
#   static/css/style.css → /css/style.css、static/020-xhr.html → /020-xhr.html
# 效果等同 .NET 的 wwwroot + UseStaticFiles()
app = Flask(__name__, static_folder="static", static_url_path="")

# ════════════════════════════════════════════════════════════
# 第一區：設定
# ════════════════════════════════════════════════════════════
app.config.update(
    DATABASE=str(BASE_DIR / "app.db"),
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,    # 整個請求最多 2 MB，超過時 Flask 回 413（6-1 檔案上傳）
    JWT_ISSUER="FlaskAjaxApi",              # 簽發者，通常填 API 的名稱或網址
    JWT_AUDIENCE="FlaskAjaxApiClient",      # 接收者，通常填前端的名稱或網址
    JWT_EXPIRE_MINUTES=int(os.environ.get("JWT_EXPIRE_MINUTES", "60")),
    JWT_KEY=os.environ.get("JWT_KEY", ""),  # 簽章用的對稱金鑰，放 .env 不進 git
)
app.json.ensure_ascii = False   # JSON 裡的中文直接輸出，不轉成 \uXXXX
app.json.sort_keys = False      # 維持 dict 原本的欄位順序，方便教學時對照（Flask 預設會依字母排序）

# 金鑰沒設定或太短就在啟動時直接失敗，比執行到登入才出錯好找問題（HMAC-SHA256 至少 32 bytes）
if len(app.config["JWT_KEY"].encode()) < 32:
    raise RuntimeError(
        "JWT_KEY 未設定或太短。請把 .env.example 複製成 .env，並填入至少 32 個字元的隨機字串，例如：\n"
        f"  JWT_KEY={secrets.token_urlsafe(48)}"
    )

# ════════════════════════════════════════════════════════════
# 第二區：掛上各個模組（順序不影響路由比對）
# ════════════════════════════════════════════════════════════

# CORS（跨來源資源共用，6-5）：瀏覽器的同源政策會擋住不同 port 的請求，
# 例如前端在 :5500、後端在 :5269，需要明確允許才能通。只開放 /api/ 底下的路徑；
# always_send=False：同源請求（沒有 Origin 標頭）就不加 CORS 標頭，DevTools 看起來才乾淨。
CORS(app, always_send=False, resources={r"/api/*": {"origins": [
    "http://localhost:5500",      # VS Code Live Server
    "http://127.0.0.1:5500",
    "http://localhost:3000",      # 其他常見開發 port
]}})

db.init_app(app)          # 請求結束關連線、flask init-db 指令、啟動時建表
errors.register(app)      # 400/401/404/500 統一回 JSON（8-3）

basics.register(app)          # GET  /api/basics                 3-1
fruits.register(app)          # CRUD /api/fruits（In-Memory）      3-4、5-8、4-3、6-1
todos.register(app)           # CRUD /api/todos（SQLite，需登入）   6-6、7-4、9-5
products.register(app)        # CRUD /api/products（SQLite）        7-4
notifications.register(app)   # SSE  /api/notifications/stream    6-2
auth.register(app)            # JWT  /api/auth/*                  9-6


# 根路徑導向首頁：/ → static/index.html（等同 .NET 的 UseDefaultFiles）
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# API 文件（2-5）：Swagger UI 讀 static/openapi.yaml。規格是手寫的，不像 ASP.NET Core 會自動產生
@app.get("/swagger")
def swagger():
    return send_from_directory(app.static_folder, "swagger.html")


if __name__ == "__main__":
    # 直接執行 python app.py 時用這裡的設定；flask run 則讀 .flaskenv
    app.run(port=5269, debug=True)
