"""商品：SQLite CRUD（對應講義 7-4）。

和 fruits.py 的差別只在資料來源：fruits 是記憶體裡的 list，這裡每個操作都是一句 SQL。
SQL 一律用 ? 佔位參數，絕對不要用字串格式化把使用者輸入拼進 SQL（SQL Injection）。
"""

from flask import Blueprint, abort, url_for

from db import get_db, utc_now_iso
from errors import parse_body
from schemas import Product, ProductDto

bp = Blueprint("products", __name__, url_prefix="/api/products")


def _row_to_product(row) -> dict:
    """資料庫列 → Product 模型 → camelCase 的 dict。
    經過 Pydantic 這一層的好處：欄位名自動轉 camelCase、created_at 轉成帶 Z 的 ISO 字串。"""
    return Product.model_validate(dict(row)).to_json()


def _fetch(product_id: int):
    row = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        abort(404)
    return row


# GET /api/products：取得所有商品，最新的在前
@bp.get("")
def get_products():
    rows = get_db().execute("SELECT * FROM products ORDER BY created_at DESC, id DESC").fetchall()
    return [_row_to_product(r) for r in rows]


# GET /api/products/5 → 200 或 404
@bp.get("/<int:product_id>")
def get_product(product_id: int):
    return _row_to_product(_fetch(product_id))


# POST /api/products → 201 + Location 或 400
@bp.post("")
def create_product():
    dto = parse_body(ProductDto)
    db = get_db()
    cursor = db.execute(
        "INSERT INTO products (name, price, image_url, created_at) VALUES (?, ?, ?, ?)",
        # 時間由伺服器決定，不信任用戶端
        (dto.name, dto.price, dto.image_url, utc_now_iso()),
    )
    db.commit()                       # sqlite3 預設開啟交易，要 commit 才會真的寫入
    product_id = cursor.lastrowid     # 自動產生的主鍵。型別是 int | None，INSERT 之後一定有值
    assert product_id is not None
    product = _row_to_product(_fetch(product_id))
    return product, 201, {"Location": url_for("products.get_product", product_id=product_id)}


# PUT /api/products/5：完整更新（所有欄位都要送，即使沒改）→ 204、404 或 400
@bp.put("/<int:product_id>")
def update_product(product_id: int):
    _fetch(product_id)                # 不存在就 404
    dto = parse_body(ProductDto)
    db = get_db()
    db.execute(
        "UPDATE products SET name = ?, price = ?, image_url = ? WHERE id = ?",
        (dto.name, dto.price, dto.image_url, product_id),
    )
    db.commit()
    return "", 204


# DELETE /api/products/5 → 204 或 404
@bp.delete("/<int:product_id>")
def delete_product(product_id: int):
    _fetch(product_id)
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return "", 204
