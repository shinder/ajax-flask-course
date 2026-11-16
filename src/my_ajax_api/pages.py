"""用 Jinja 模板產生的頁面：/pages 底下，功能與 static/ 的同名頁面相同。

static/*.html 是原封不動送出去的靜態檔，每一頁都要自己帶一份 <head> 與導覽列；
這裡改由伺服器在回應前把 templates/base.html（共用版型）與各頁的內容組起來，
導覽列只寫一份，連結用 url_for() 產生。

頁面上的資料仍然是瀏覽器載入後用 AJAX 向 /api/* 取得，模板只負責組出 HTML 骨架，
所以每個路由都只有一行 render_template()，不用查資料庫也不用傳變數。

模板放在套件旁的 templates/（Flask 預設的位置），render_template() 的路徑從那裡算起。
"""

from flask import Blueprint, render_template

# 藍圖名稱 "pages" 是端點的命名空間：模板裡寫 url_for("pages.fruits") 會得到 /pages/fruits
bp = Blueprint("pages", __name__, url_prefix="/pages")


# 待辦清單：GET /pages/
# 路徑寫 "/" 所以網址結尾有斜線；少了斜線的 /pages 會被 308 轉址過來
@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/fruits")
def fruits():
    return render_template("fruits.html")


@bp.get("/products")
def products():
    return render_template("products.html")


@bp.get("/upload")
def upload():
    return render_template("upload.html")


# 網址用連字號、函式名用底線：端點名稱是 pages.sync_demo
@bp.get("/sync-demo")
def sync_demo():
    return render_template("sync-demo.html")


@bp.get("/sse-demo")
def sse_demo():
    return render_template("sse-demo.html")


@bp.get("/login")
def login():
    return render_template("login.html")


@bp.get("/login-session")
def login_session():
    return render_template("login-session.html")
