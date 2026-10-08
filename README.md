# AJAX + RESTful API 課程範例專案（Flask 版）

Flask 3 + 標準庫 sqlite3 + 原生 JavaScript 前端，作為課程講義《AJAX + RESTful API 使用 Flask》的對應範例。功能與端點對齊 .NET 版（ajax-dotnet-course），前端頁面與課堂示範檔兩邊共用。講義每一節標示「範例：」的地方，都可以在這裡找到對應的檔案。

## 系統需求

- [uv](https://docs.astral.sh/uv/)：Python 版本與套件管理工具，會依 `.python-version` 自動下載 Python 3.14，不必另外安裝 Python
- 本專案刻意不用 ORM 與 Blueprint，只用 Flask 本體、Pydantic 與標準庫 sqlite3，讓學員看到每一步在做什麼

建議工具（選用，對應講義附錄 D）：

| 工具 | 用途 |
| ---- | ---- |
| VS Code + Python 擴充套件 | 開發 IDE |
| REST Client（VS Code 擴充套件） | 直接開 `api.http` 逐一送出請求 |
| Postman 或 Bruno | API 測試 |
| [Letos](https://letos.org/) | 瀏覽與編輯 SQLite 資料庫 `app.db`，免安裝，前身為 SQLiteStudio |
| VS Code Live Server | 在 5500 埠開前端頁面，示範 CORS |

---

## 啟動方式

### 1. 設定 JWT 簽章金鑰（只需一次）

金鑰不放在程式碼裡（會進 git），改放在專案根目錄的 `.env`，這個檔案已在 `.gitignore`。

```bash
cp .env.example .env          # Windows：copy .env.example .env
```

打開 `.env`，把 `JWT_KEY=` 後面填上至少 32 個字元的隨機字串。產生方式擇一：

```bash
# macOS / Linux
openssl rand -base64 48

# 任何環境（含 Windows）
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

沒設定就啟動會直接報錯「JWT_KEY 未設定或太短」，錯誤訊息裡會附一組可直接複製的隨機字串。

### 2. 啟動開發伺服器

```bash
uv run flask run
```

第一次執行 uv 會自動建立 `.venv` 並安裝依賴，之後直接啟動。`.flaskenv` 已設定 port 8000 與 debug 模式，改檔會自動重啟。

專案根目錄也提供了啟動腳本，效果和上面的指令相同：

| 腳本 | 執行方式 | 說明 |
| ---- | -------- | ---- |
| `start.sh` | `./start.sh` | macOS / Linux |
| `start.bat` | `.\start.bat`（cmd 或 PowerShell 皆可） | 不受 PowerShell 執行原則限制，最省事 |
| `start.ps1` | `.\start.ps1` | 需先放行執行原則，見下方 |

Windows PowerShell 預設執行原則是 `Restricted`，直接執行 `.\start.ps1` 會出現「因為這個系統上已停用指令碼執行」的錯誤。擇一處理：

```powershell
# 只放寬這一次，不改系統設定
powershell -ExecutionPolicy Bypass -File .\start.ps1

# 或：設定一次，之後直接 .\start.ps1（只影響目前使用者，不需要系統管理員）
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

> 若專案是從網路下載的 zip 解壓出來，Windows 會把檔案標記為「來自網際網路」，RemoteSigned 仍會擋，先執行 `Unblock-File .\start.ps1` 解除封鎖。

啟動後開啟瀏覧器：

| 頁面 | 網址 | 對應講義 |
| ---- | ---- | -------- |
| 待辦清單（Todo App） | <http://localhost:8000/> | 6-6 |
| 水果清單：搜尋、排序、分頁、編輯、欄位驗證 | <http://localhost:8000/fruits.html> | 5-5 至 5-10、6-3、8-4 |
| 商品管理（SQLite 版） | <http://localhost:8000/products.html> | 5-7、7-4 |
| 檔案上傳：fetch + FormData 與 XHR 進度條 | <http://localhost:8000/upload.html> | 6-1 |
| 同步 vs 非同步 XHR | <http://localhost:8000/sync-demo.html> | 4-3 |
| SSE 伺服器推送 | <http://localhost:8000/sse-demo.html> | 6-2 |
| JWT 登入、註冊、查看 token | <http://localhost:8000/login.html> | 第 9 章 |
| Swagger API 文件 | <http://localhost:8000/swagger> | 2-5 |

`static/` 底下 `010` 到 `270` 的編號檔案是課堂示範用的最小範例，每個只聚焦一件事，對應章節與觀察重點見講義附錄 E。其中 `270-cors.html` 要用 VS Code Live Server 從 5500 埠開才看得到 CORS 錯誤；`020`、`170`、`180`、`190` 寫的是完整網址，也能從 Live Server 開。

> 第一次啟動會自動依 `schema.sql` 建立 `app.db`（SQLite），不需要手動執行指令。要清空資料重建，執行 `uv run flask init-db`。

> 待辦清單（`/api/todos`）需要登入才能操作，其餘端點不需登入。`api.js` 會自動把 localStorage 的 token 放進 `Authorization` 標頭，遇 401 則清除 token。

> `api.http` 收錄了所有端點的測試請求，用 VS Code 的 REST Client 擴充套件開啟即可逐一送出（講義 1-6）。

---

## JWT 登入

### 流程

1. `POST /api/auth/register`：密碼用 Werkzeug 的 `generate_password_hash`（預設 scrypt）雜湊後存入 `users` 資料表，明文不落地。
2. `POST /api/auth/login`：比對密碼，成功後由 `auth.py` 的 `create_token` 用 PyJWT 簽發 token，回傳 `{ token, expiresAt, username }`。
3. 前端把 token 存進 localStorage，`api.js` 之後的每個請求都帶 `Authorization: Bearer <token>`。
4. 加了 `@login_required` 的端點（`/api/auth/me`、`/api/todos`）由裝飾器驗證簽章、簽發者、接收者與到期時間，不通過直接回 401。
5. 登出只是前端丟掉 token；JWT 是無狀態的，已簽發的 token 在到期前仍然有效。

### 測試方式

**瀏覽器**

1. 開 <http://localhost:8000/>，未登入時會看到提示、表單被隱藏。
2. 到 <http://localhost:8000/login.html> 註冊（例如 `alice` / `secret123`），再登入。頁面會顯示目前帳號、token 原文與解碼後的 Payload。
3. 回待辦清單頁，可以新增、勾選、刪除。
4. 錯誤情境：帳號填 `a` 會在欄位旁顯示驗證訊息；密碼打錯回「帳號或密碼錯誤」；重複註冊回「帳號已被使用」。
5. 按「登出」後回待辦頁，會變回未登入提示。
6. 想看 token 過期，在 `.env` 加一行 `JWT_EXPIRE_MINUTES=1`，重啟後登入，等一分鐘再操作待辦頁。

**REST Client（`api.http`）**

「第 9 章：Auth」區段依序送出：註冊、登入、帶 token 查 `/me`、不帶 token、竄改 token。登入請求上方有 `# @name login`，後續請求用 `{{login.response.body.token}}` 自動帶入 token，Todos 區段的請求也一樣。這個方式能看到完整的 `Authorization` 標頭與回應 Body，最適合講解。

**Swagger UI**

1. 執行 `POST /api/auth/login` 取得 token。
2. 點右上角 Authorize，貼上 token（不用加 `Bearer ` 前綴）。
3. 之後執行 `/api/auth/me` 或 `/api/todos` 都會自動帶 token；按 Logout 再試會變 401。

**確認密碼有雜湊**

用 [Letos](https://letos.org/) 開 `app.db` 看 `users` 資料表，或用命令列：

```bash
sqlite3 app.db "select username, password_hash from users;"
```

應看到 `scrypt:32768:8:1$` 開頭的字串，而非明文。

### 常見問題

- 啟動時報「JWT_KEY 未設定或太短」：`.env` 沒建或沒填，見上方「設定 JWT 簽章金鑰」。
- 改了 `schema.sql` 但資料表沒變：`CREATE TABLE IF NOT EXISTS` 不會修改已存在的資料表，執行 `uv run flask init-db` 重建（資料會清空）。
- 上傳檔案後頁面沒有自動重新整理：這是正常的，Flask 的自動重啟只監看 Python 檔，不監看 `static/`。

### 刻意不做的事

- 沒有 refresh token、沒有登出黑名單、沒有角色權限，重點放在「簽發、攜帶、驗證」三步驟。
- 沒有用 Flask-Login 或 Flask-JWT-Extended，自己寫 `users` 資料表與 `login_required` 裝飾器才看得清楚每一步在做什麼。

---

## 專案結構

```
ajax-flask-course/
├── app.py                  # 入口：建立 app、載入設定、CORS、掛上各模組（講義第 2 章）
├── db.py                   # sqlite3 連線管理（g 物件）、init-db 指令、啟動時建表（7-2、7-3）
├── schema.sql              # 資料表結構：products、todos、users（7-2）
├── schemas.py              # Pydantic DTO 與驗證規則；snake_case 與 camelCase 自動對應（3-3、8-2）
├── errors.py               # Problem Details 格式、parse_body()、400/401/404/500 統一處理（8-3）
├── auth.py                 # JWT 簽發（create_token）與驗證（login_required 裝飾器）（9-4、9-5）
├── api/                    # 每種資源一個檔案，各自提供 register(app) 掛上路由
│   ├── basics.py           # GET /api/basics，最簡單的端點（3-1）
│   ├── fruits.py           # In-Memory CRUD /api/fruits，含搜尋/排序/分頁、slow、upload（3-4、5-8、4-3、6-1）
│   ├── todos.py            # SQLite CRUD /api/todos，需登入（6-6、7-4、9-5）
│   ├── products.py         # SQLite CRUD /api/products（7-4）
│   ├── notifications.py    # SSE /api/notifications/stream（6-2）
│   └── auth.py             # 註冊、登入、/me（9-6）
├── static/                 # 前端頁面與課堂示範檔（等同 .NET 的 wwwroot）
│   ├── index.html          # 待辦清單頁（需登入，9-7）
│   ├── login.html          # 登入、註冊、查看 token（9-7）
│   ├── fruits.html         # 水果清單頁（第 5 章前端範例的集合）
│   ├── products.html       # 商品管理頁
│   ├── upload.html         # 檔案上傳頁
│   ├── sync-demo.html      # 同步 vs 非同步示範
│   ├── sse-demo.html       # SSE 推送示範
│   ├── swagger.html        # Swagger UI（讀 openapi.yaml）
│   ├── openapi.yaml        # 手寫的 OpenAPI 規格（2-5）
│   ├── 010-alert.html … 270-cors.html   # 課堂示範檔，見講義附錄 E
│   ├── uploads/            # 上傳的檔案（已 gitignore）
│   ├── js/
│   │   ├── api.js          # fetch 封裝（5-4）
│   │   ├── toast.js        # Toast 通知（5-6）
│   │   └── utils.js        # escapeHtml、debounce（5-5、5-9）
│   └── css/style.css
├── api.http                # 所有端點的測試請求（REST Client）
├── .flaskenv               # flask run 的設定：port 8000、debug（可進 git）
├── .env.example            # 機密設定的範本，複製成 .env 後填 JWT_KEY（.env 不進 git）
├── .python-version         # 3.14，uv 依此選用 Python
├── pyproject.toml          # 專案與依賴定義
├── uv.lock                 # 鎖定的套件版本，uv sync 會完全重現
├── start.sh / start.bat / start.ps1   # 啟動腳本
└── README.md
```

### 設計取捨

| 項目 | .NET 版 | Flask 版 | 說明 |
| ---- | ------- | -------- | ---- |
| 路由組織 | Controller 類別 | 模組 + `register(app)` | 不用 Blueprint，讓學員先看到 Flask 路由就是普通函式；拆檔的動機在第 6 章才出現 |
| 資料庫 | EF Core | 標準庫 sqlite3 + `schema.sql` | 課程重點在 HTTP 與 AJAX，不另外教 ORM；SQL 直接寫，用 `?` 參數防注入 |
| 驗證 | FluentValidation | Pydantic | 錯誤格式對齊 .NET 的 ValidationProblemDetails，前端 `showFieldErrors` 不用改 |
| JSON 命名 | camelCase | camelCase | Pydantic `alias_generator=to_camel`，Python 端仍寫 snake_case |
| JWT | JwtBearer 中介軟體 | PyJWT + 裝飾器 | `@login_required` 等同 `[Authorize]` |
| 密碼雜湊 | bcrypt | Werkzeug scrypt | 都是「每次雜湊結果不同、無法還原」的做法 |
| API 文件 | Swashbuckle 自動產生 | 手寫 `openapi.yaml` + Swagger UI | Flask 不會自動產生，手寫反而能看到規格長什麼樣 |
| 請求超過 2 MB | 400 | 413 | Flask 的 `MAX_CONTENT_LENGTH` 直接回 413，是更精確的狀態碼 |

---

## 從零建立專案的指令流程

```bash
# 1. 安裝 Python 3.14 並初始化專案（--no-package：平面配置，不產生 src/ 與打包設定）
uv python install 3.14
uv init --no-package --python 3.14

# 2. 加入依賴
uv add flask pydantic pyjwt flask-cors python-dotenv

# 3. 設定 JWT 金鑰（見上方）
cp .env.example .env

# 4. 執行
uv run flask run
```

學員 clone 專案後只需要 `uv sync`（或直接 `uv run flask run`），uv 會依 `uv.lock` 安裝完全相同的版本。

---

## API 端點

測試端點前要先把伺服器跑起來，所有路徑的主機都是 <http://localhost:8000>。要逐一送出請求，用 VS Code REST Client 開 `api.http`，或開 <http://localhost:8000/swagger>。表格最後一欄是講義的對應章節。

錯誤回應一律是 Problem Details 風格的 JSON：`{ "title": "...", "status": 404 }`，驗證錯誤多一個 `errors` 物件，key 是欄位名、value 是訊息陣列。

### Basics

| 方法 | 路徑 | 說明 | 講義 |
|------|------|------|------|
| GET | `/api/basics` | 回傳 `{ "message": "Hello API" }` | 3-1 |

### Fruits（In-Memory，重啟後歸零）

| 方法 | 路徑 | 說明 | 講義 |
|------|------|------|------|
| GET | `/api/fruits?name=&sort=&page=&size=` | 列表；`sort` 可為 `id`、`name`、`price`、`price_desc`；回傳 `{ items, total, page, size, totalPages }` | 5-8、5-9 |
| GET | `/api/fruits/{id}` | 取得單筆 | 3-4 |
| POST | `/api/fruits` | 新增（名稱 1 到 20 字、價格 1 到 10000） | 3-4、8-2、8-4 |
| PUT | `/api/fruits/{id}` | 完整更新 | 3-4、5-10 |
| DELETE | `/api/fruits/{id}` | 刪除 | 3-4、6-3 |
| GET | `/api/fruits/slow?seconds=10` | 等待指定秒數（1 到 30）後回傳全部，供同步 vs 非同步示範 | 4-3 |
| POST | `/api/fruits/upload` | `multipart/form-data` 上傳圖片（jpg、png、gif、webp，最大 2 MB），存到 `static/uploads` | 6-1 |

### Auth（JWT）

| 方法 | 路徑 | 說明 | 講義 |
|------|------|------|------|
| POST | `/api/auth/register` | 註冊（帳號 3 到 20 字英數底線、密碼 6 到 64 字）；重複回 409 | 9-3、9-6 |
| POST | `/api/auth/login` | 登入，回傳 `{ token, expiresAt, username }`；失敗回 401 | 9-4、9-6 |
| GET | `/api/auth/me` | 需帶 token，回傳 `{ id, username }` | 9-5 |

### Todos（SQLite，需帶 token）

每條路由都加了 `@login_required`（講義 9-5），沒帶或帶無效 token 一律 401。

| 方法 | 路徑 | 說明 | 講義 |
|------|------|------|------|
| GET | `/api/todos` | 取得所有待辦 | 6-6、7-4 |
| GET | `/api/todos/{id}` | 取得單筆 | 6-6 |
| POST | `/api/todos` | 新增待辦 | 6-6、7-4 |
| PATCH | `/api/todos/{id}` | 更新完成狀態 | 6-6 |
| DELETE | `/api/todos/{id}` | 刪除待辦 | 6-6、6-3 |

### Products（SQLite）

| 方法 | 路徑 | 說明 | 講義 |
|------|------|------|------|
| GET | `/api/products` | 取得所有商品（最新的在前） | 7-4 |
| GET | `/api/products/{id}` | 取得單筆商品 | 7-4 |
| POST | `/api/products` | 新增商品（`imageUrl` 選填，有填必須是 https） | 7-4、8-2 |
| PUT | `/api/products/{id}` | 更新商品 | 7-4 |
| DELETE | `/api/products/{id}` | 刪除商品 | 7-4 |

### Notifications（SSE）

| 方法 | 路徑 | 說明 | 講義 |
|------|------|------|------|
| GET | `/api/notifications/stream` | `text/event-stream`，每 2 秒推送 `{ seq, time, fruitCount }` | 6-2 |
