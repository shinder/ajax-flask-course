"""最簡單的 API 端點（對應講義 3-1）。"""


def register(app):
    # GET /api/basics
    # 回傳 dict，Flask 會自動序列化成 JSON 並設定 Content-Type: application/json：{"message":"Hello API"}
    # 若直接 return "Hello API"，回應會是 text/html 純字串，前端用 r.json() 會解析失敗
    @app.get("/api/basics")
    def get_basics():
        return {"message": "Hello API"}
