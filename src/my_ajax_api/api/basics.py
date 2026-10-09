"""最簡單的 API 端點（對應講義 3-1）。

每個 api/*.py 都定義一個 Blueprint（藍圖）：先把路由掛在藍圖上，
create_app() 再用 app.register_blueprint() 一次把整組路由掛進 app。
url_prefix 是這組路由共用的前綴，底下的路徑都從這裡接下去。
"""

from flask import Blueprint

bp = Blueprint("basics", __name__, url_prefix="/api")


# GET /api/basics
# 回傳 dict，Flask 會自動序列化成 JSON 並設定 Content-Type: application/json：{"message":"Hello API"}
# 若直接 return "Hello API"，回應會是 text/html 純字串，前端用 r.json() 會解析失敗
@bp.get("/basics")
def get_basics():
    return {"message": "Hello API"}
