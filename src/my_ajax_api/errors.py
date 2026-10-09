"""統一的錯誤回應格式與全域例外處理（對應講義第 8 章）。

所有錯誤都回傳 Problem Details（RFC 9457）風格的 JSON，前端的 api.js 只要認得
title、status、errors 三個欄位，就能用同一套邏輯處理 400、401、404、409、500：

    一般錯誤  { "title": "找不到資料", "status": 404 }
    驗證錯誤  { "title": "輸入資料有誤", "status": 400,
                "errors": { "name": ["名稱不可為空"], "price": ["價格必須大於 0"] } }
"""

import logging

from flask import jsonify, request
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ProblemError(Exception):
    """在路由裡 raise 這個例外，就會由 handle_problem 轉成對應狀態碼的 JSON 回應。

    用例外而不是 return 的好處：巢狀呼叫（例如 parse_body 裡驗證失敗）可以直接中斷，
    不用一層層把錯誤回傳值往外帶。
    """

    def __init__(self, status: int, title: str, errors: dict[str, list[str]] | None = None):
        super().__init__(title)
        self.status = status
        self.title = title
        self.errors = errors


def problem(status: int, title: str, errors: dict[str, list[str]] | None = None):
    """組出 Problem Details 回應，給路由直接 return 用。"""
    body: dict = {"title": title, "status": status}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


# Pydantic 內建錯誤的 type 代碼對應中文訊息。
# 自訂規則（schemas.py 的 field_validator）會給自己的訊息，不會經過這張表。
_PYDANTIC_MESSAGES = {
    "missing": "此欄位為必填",
    "string_type": "必須是字串",
    "int_parsing": "必須是數字",
    "int_type": "必須是數字",
    "float_parsing": "必須是數字",
    "float_type": "必須是數字",
    "bool_parsing": "必須是 true 或 false",
    "bool_type": "必須是 true 或 false",
}

# Werkzeug 的 HTTP 例外名稱是英文（Not Found），常見的幾個換成中文；沒列的就用英文原名
_HTTP_TITLES = {
    400: "請求格式錯誤",
    404: "找不到資源",
    405: "不支援的 HTTP 方法",
    413: "請求內容過大（上限 2 MB）",
    415: "不支援的內容類型",
}


def _errors_from_pydantic(exc: ValidationError) -> dict[str, list[str]]:
    """把 Pydantic 的錯誤清單整理成 { 欄位: [訊息, ...] }。

    Pydantic 的 loc 是欄位路徑（巢狀物件會有多層），這裡的 DTO 都是平的，取第一層就好；
    回報時用 alias（camelCase），和前端送來的欄位名一致。
    price 宣告成 int | float 時，同一個錯誤會對 int 與 float 各報一次，所以同欄位的重複訊息只留一個。
    """
    errors: dict[str, list[str]] = {}
    for err in exc.errors():
        field = str(err["loc"][0]) if err["loc"] else ""
        message = _PYDANTIC_MESSAGES.get(err["type"], err["msg"])
        messages = errors.setdefault(field, [])
        if message not in messages:
            messages.append(message)
    return errors


def parse_body[T: BaseModel](model: type[T]) -> T:
    """讀取請求本文的 JSON 並用 Pydantic 模型驗證；失敗就丟出 400。

    用法：dto = parse_body(CreateFruitDto)
    許多框架會自動做「解析請求本文並驗證」這件事，Flask 要自己呼叫一次。
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ProblemError(
            400,
            "請求本文必須是 JSON 物件",
            {"": ["Content-Type 要是 application/json，且本文是合法的 JSON 物件"]},
        )
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ProblemError(400, "輸入資料有誤", _errors_from_pydantic(exc)) from None


def init_app(app):
    """把三個錯誤處理器掛到 app 上（和 db.init_app 一樣的慣例）。"""

    # 1. 我們自己丟的 ProblemError：400 驗證錯誤、401、409 等「預期內」的錯誤
    @app.errorhandler(ProblemError)
    def handle_problem(exc: ProblemError):
        response, status = problem(exc.status, exc.title, exc.errors)
        if status == 401:
            # RFC 6750：401 回應要告訴用戶端用哪種機制驗證
            response.headers["WWW-Authenticate"] = "Bearer"
        return response, status

    # 2. Flask / Werkzeug 的 HTTP 例外：404（路由不存在、abort(404)）、405、413、415 等。
    #    Flask 預設回 HTML 錯誤頁，這裡改成 JSON，前端 res.json() 才不會解析失敗。
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        code = exc.code or 500
        return problem(code, _HTTP_TITLES.get(code, exc.name))

    # 3. 其他沒接住的例外：程式 bug、資料庫掛掉等「預期外」的錯誤。
    #    完整堆疊記在伺服器 log，回給用戶端的只有一句通用訊息，不洩漏內部細節。
    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("未預期的錯誤")
        return problem(500, "伺服器發生錯誤，請稍後再試")
