"""請求與回應的資料形狀（DTO），用 Pydantic 定義與驗證（對應講義第 3、8 章）。

與資料庫結構分開定義的理由（講義 3-3）：
  1. 不讓用戶端設定不該由外部決定的欄位（id、created_at）
  2. 驗證規則集中在一處
  3. API 介面和資料表可以獨立演進

命名：Python 慣用 snake_case（image_url），JSON 慣用 camelCase（imageUrl）。
CamelModel 用 alias_generator 自動對應，前端送 imageUrl、後端寫 dto.image_url，輸出時再轉回去。
"""

from datetime import datetime
from typing import LiteralString

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError


class CamelModel(BaseModel):
    """所有 DTO 的共同基底：欄位名用 snake_case，JSON 用 camelCase。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # 允許用 Python 欄位名建立（從資料庫列轉換時用）
        str_strip_whitespace=True,  # 字串自動去頭尾空白
    )

    def to_json(self) -> dict:
        """轉成要回給前端的 dict：key 用 camelCase，datetime 轉成 ISO 8601 字串（UTC 會帶 Z）。"""
        return self.model_dump(by_alias=True, mode="json")


def _require(value: str, message: LiteralString) -> str:
    """共用的「不可為空」檢查。PydanticCustomError 的第二個參數就是回給前端的訊息，
    它要求是字面字串（LiteralString），不能是執行期組出來的字串。"""
    if not value:
        raise PydanticCustomError("required", message)
    return value


# ── Fruits（第 3 章 In-Memory CRUD） ────────────────────────────────


class FruitDto(CamelModel):
    """新增與更新共用同一組欄位與規則；若日後規則分歧，再拆成兩個類別。"""

    name: str
    price: int | float  # JSON 只有一種數字型別；用 int | float 讓 30 維持 30、30.5 維持 30.5

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        _require(v, "名稱不可為空")
        if len(v) > 20:
            raise PydanticCustomError("max_length", "名稱不超過 20 字")
        return v

    @field_validator("price")
    @classmethod
    def check_price(cls, v: float) -> float:
        if v <= 0:
            raise PydanticCustomError("greater_than", "價格必須大於 0")
        if v > 10_000:
            raise PydanticCustomError("less_than_or_equal", "價格不超過 10,000")
        return v


# ── Products（第 7 章 SQLite CRUD） ────────────────────────────────


class ProductDto(CamelModel):
    name: str
    price: int | float
    image_url: str | None = None  # 選填；前端送 imageUrl

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        _require(v, "名稱不可為空")
        if len(v) > 100:
            raise PydanticCustomError("max_length", "名稱不超過 100 字")
        return v

    @field_validator("price")
    @classmethod
    def check_price(cls, v: float) -> float:
        if v <= 0:
            raise PydanticCustomError("greater_than", "價格必須大於 0")
        if v > 1_000_000:
            raise PydanticCustomError("less_than_or_equal", "價格不超過 1,000,000")
        return v

    @field_validator("image_url")
    @classmethod
    def check_image_url(cls, v: str | None) -> str | None:
        # 條件驗證：有填才檢查，空字串視同沒填
        if not v:
            return None
        if not v.startswith("https://"):
            raise PydanticCustomError("https_required", "圖片 URL 必須使用 https")
        return v


class Product(CamelModel):
    """回給前端的商品：由資料庫列轉換而來，created_at 是 UTC 時間，輸出會帶 Z。"""

    id: int
    name: str
    price: int | float
    image_url: str | None
    created_at: datetime


# ── Todos（第 6 章 Todo App） ──────────────────────────────────────


class CreateTodoDto(CamelModel):
    title: str

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        return _require(v, "標題不可為空")


class UpdateTodoDto(CamelModel):
    """PATCH 用：只更新 is_done 這一個欄位。前端送 { "isDone": true }。"""

    is_done: bool


class Todo(CamelModel):
    id: int
    title: str
    is_done: bool  # SQLite 沒有布林，存 0/1；Pydantic 會自動轉成 True/False


# ── Auth（第 9 章 JWT） ───────────────────────────────────────────


class RegisterDto(CamelModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        _require(v, "帳號不可為空")
        if not 3 <= len(v) <= 20:
            raise PydanticCustomError("length", "帳號長度須為 3 到 20 字")
        if not v.replace("_", "").isalnum() or not v.isascii():
            raise PydanticCustomError("pattern", "帳號只能包含英文、數字與底線")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        _require(v, "密碼不可為空")
        if len(v) < 6:
            raise PydanticCustomError("min_length", "密碼至少 6 個字元")
        if len(v) > 64:
            raise PydanticCustomError("max_length", "密碼不超過 64 個字元")
        return v


class LoginDto(CamelModel):
    """登入只檢查「有沒有填」。長度、格式不在這裡重複，
    否則等於告訴攻擊者「這種格式的帳號一定不存在」，而且改規則時要改兩處。"""

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        return _require(v, "請輸入帳號")

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _require(v, "請輸入密碼")
