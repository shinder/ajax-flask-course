"""水果：In-Memory CRUD、搜尋排序分頁、慢速回應、檔案上傳（對應講義 3-4、5-8、4-3、6-1）。

資料存在模組層級的 list，重啟伺服器就歸零。
注意：list 與 _next_id 都不是執行緒安全的，多個請求同時新增可能出錯；
這是教學用的簡化，正式環境要用資料庫（第 7 章）或加鎖。
"""

import math
import time
import uuid
from pathlib import Path

from flask import Blueprint, abort, current_app, request, url_for

from my_ajax_api.errors import ProblemError, parse_body
from my_ajax_api.schemas import FruitDto

# 藍圖名稱 "fruits" 也是端點的命名空間：url_for("fruits.get_fruit") 才找得到底下的函式
bp = Blueprint("fruits", __name__, url_prefix="/api/fruits")

fruits: list[dict] = [
    {"id": 1, "name": "蘋果", "price": 30},
    {"id": 2, "name": "香蕉", "price": 15},
    {"id": 3, "name": "芒果", "price": 50},
    {"id": 4, "name": "鳳梨", "price": 45},
    {"id": 5, "name": "西瓜", "price": 120},
    {"id": 6, "name": "葡萄", "price": 80},
    {"id": 7, "name": "草莓", "price": 150},
    {"id": 8, "name": "芭樂", "price": 25},
    {"id": 9, "name": "木瓜", "price": 35},
    {"id": 10, "name": "荔枝", "price": 90},
    {"id": 11, "name": "柳丁", "price": 20},
    {"id": 12, "name": "奇異果", "price": 40},
]
_next_id = 13


def count() -> int:
    """給 notifications.py 的 SSE 推送用：目前的水果總數。"""
    return len(fruits)


def _find(fruit_id: int) -> dict:
    """找不到就直接 404；找到回傳該筆 dict（可就地修改）。"""
    for f in fruits:
        if f["id"] == fruit_id:
            return f
    abort(404)


# 允許上傳的圖片格式：key 是副檔名，value 是對應的 MIME 類型
ALLOWED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


# 取得列表：GET /api/fruits?name=果&sort=price_desc&page=1&size=5 → 200
# 路徑寫 "" 代表「就是前綴本身」。若寫 "/" 會變成 /api/fruits/，少了斜線的請求會被 308 轉址。
# 搜尋、排序、分頁都是「條件」而不是「資源」，一律放查詢字串（講義 1-4、5-8）。
# request.args.get 的 type= 參數會幫忙轉型，轉不過去就用預設值。
@bp.get("")
def get_fruits():
    name = request.args.get("name", "").strip()
    sort = request.args.get("sort", "id")
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 5, type=int)

    # 篩選：名稱包含關鍵字（不分大小寫）
    result = [f for f in fruits if name.lower() in f["name"].lower()] if name else list(fruits)

    # 排序：只接受白名單裡的值，其他一律回到預設
    match sort:
        case "name":
            result.sort(key=lambda f: f["name"])
        case "price":
            result.sort(key=lambda f: f["price"])
        case "price_desc":
            result.sort(key=lambda f: f["price"], reverse=True)
        case _:
            result.sort(key=lambda f: f["id"])

    # 分頁：防止前端送 page=0 或 size=100000 這種值
    page = max(page, 1)
    size = min(max(size, 1), 100)
    total = len(result)

    # 頁碼超過最後一頁就退回最後一頁，避免前端顯示「第 999 / 3 頁」
    total_pages = max(math.ceil(total / size), 1)
    page = min(page, total_pages)

    start = (page - 1) * size
    items = result[start : start + size]

    return {"items": items, "total": total, "page": page, "size": size, "totalPages": total_pages}


# 慢速回應：GET /api/fruits/slow?seconds=10 → 等待指定秒數後才回傳全部水果
# 教學用：用同步的 XHR（xhr.open(..., false)）呼叫這支，可以看到整個頁面在等待期間完全卡死；
# 改用非同步呼叫則頁面照常可以操作，這就是 AJAX 的 A（Asynchronous）存在的理由。
# 這條路由要放在 /<int:fruit_id> 之前或之後都可以，Werkzeug 會優先比對不含變數的規則。
@bp.get("/slow")
def get_fruits_slow():
    seconds = request.args.get("seconds", 10, type=int)
    seconds = min(max(seconds, 1), 30)
    time.sleep(seconds)  # 開發伺服器是多執行緒的，sleep 只卡住這個請求，不影響其他請求
    return {"waitedSeconds": seconds, "items": fruits}


# 取得單筆：GET /api/fruits/5 → 200 或 404
# <int:fruit_id> 是路由轉換器：只接受整數，/api/fruits/abc 直接 404，不會進到函式
@bp.get("/<int:fruit_id>")
def get_fruit(fruit_id: int):
    return _find(fruit_id)


# 新增：POST /api/fruits → 201 Created（附 Location）或 400
@bp.post("")
def create_fruit():
    global _next_id
    dto = parse_body(FruitDto)  # 驗證失敗會在這裡丟出 400，後面不會執行
    fruit = {"id": _next_id, "name": dto.name, "price": dto.price}
    _next_id += 1
    fruits.append(fruit)
    # 回傳 (body, status, headers)：201 並在 Location 標頭告訴用戶端新資源在哪。
    # 端點名稱是「藍圖名.函式名」，所以是 fruits.get_fruit 而不是 get_fruit
    return fruit, 201, {"Location": url_for("fruits.get_fruit", fruit_id=fruit["id"])}


# 更新：PUT /api/fruits/5 → 204 No Content 或 404 / 400
@bp.put("/<int:fruit_id>")
def update_fruit(fruit_id: int):
    fruit = _find(fruit_id)
    dto = parse_body(FruitDto)
    fruit["name"] = dto.name
    fruit["price"] = dto.price
    return "", 204


# 刪除：DELETE /api/fruits/5 → 204 No Content 或 404
@bp.delete("/<int:fruit_id>")
def delete_fruit(fruit_id: int):
    fruit = _find(fruit_id)
    fruits.remove(fruit)
    return "", 204


# 上傳：POST /api/fruits/upload（multipart/form-data）→ 200、400 或 413
# 對應講義 6-1。檔案在 request.files、其他欄位在 request.form。
# 上傳的檔案會放進 static/uploads 讓瀏覽器直接開，所以「只收圖片」是安全底線：
# 若放行 .html 或 .svg，任何人都能上傳一個含 script 的檔案，再用同源的網址讓別人開啟（儲存型 XSS）。
# 超過 MAX_CONTENT_LENGTH（create_app() 設 2 MB）時 Flask 會在讀取表單前就回 413。
@bp.post("/upload")
def upload_fruit_image():
    file = request.files.get("file")
    note = request.form.get("note", "")
    errors: dict[str, list[str]] = {}

    if file is None or not file.filename:  # 沒有 file 欄位，或有欄位但沒選檔案
        errors["file"] = ["沒有收到檔案"]
        raise ProblemError(400, "輸入資料有誤", errors)

    # 副檔名與 MIME 類型都要對，而且副檔名由伺服器決定（不信任用戶端的檔名）
    ext = Path(file.filename).suffix.lower()
    expected_mime = ALLOWED_IMAGE_TYPES.get(ext)
    if expected_mime is None:
        errors["file"] = ["只接受 jpg、png、gif、webp 圖片"]
    elif file.mimetype != expected_mime:
        errors["file"] = [f"檔案內容類型 {file.mimetype} 與副檔名不符"]

    # 回 400 + errors，格式與其他驗證錯誤一致，前端才能統一處理
    if errors:
        raise ProblemError(400, "輸入資料有誤", errors)

    # 藍圖裡拿不到 app 變數，要用 current_app 取得「目前正在處理請求的 app」再讀設定
    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 隨機檔名 + 白名單裡的副檔名，避免覆蓋、路徑穿越與奇怪的大小寫
    saved_name = f"{uuid.uuid4()}{ext}"
    full_path = upload_dir / saved_name
    file.save(full_path)

    # static 資料夾由 Flask 提供，回傳的 url 可直接在瀏覽器開啟
    return {"url": f"/uploads/{saved_name}", "size": full_path.stat().st_size, "note": note}
