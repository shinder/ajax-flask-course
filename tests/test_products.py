"""商品：SQLite CRUD 與 camelCase 輸出（講義 5-7、7-4、8-2）。"""


def test_create_and_get(client):
    res = client.post("/api/products", json={"name": "香蕉", "price": 15})
    assert res.status_code == 201
    product = res.json
    assert res.headers["Location"].endswith(f"/api/products/{product['id']}")
    # 5-7：輸出是 camelCase、createdAt 是 UTC 的 ISO 8601 字串（結尾 Z）
    assert product["imageUrl"] is None
    assert product["createdAt"].endswith("Z")
    assert "image_url" not in product

    assert client.get(f"/api/products/{product['id']}").json == product


def test_list_newest_first(client):
    a = client.post("/api/products", json={"name": "A", "price": 1}).json
    b = client.post("/api/products", json={"name": "B", "price": 2}).json
    ids = [p["id"] for p in client.get("/api/products").json]
    assert ids.index(b["id"]) < ids.index(a["id"])


def test_image_url_conditional_validation(client):
    """8-2：imageUrl 有填才驗證，空字串視同沒填。"""
    res = client.post("/api/products", json={"name": "X", "price": 1, "imageUrl": ""})
    assert res.status_code == 201 and res.json["imageUrl"] is None

    res = client.post("/api/products", json={"name": "X", "price": 1, "imageUrl": "http://a/b.png"})
    assert res.status_code == 400
    assert res.json["errors"]["imageUrl"] == ["圖片 URL 必須使用 https"]   # key 用 camelCase


def test_update_delete_404(client):
    pid = client.post("/api/products", json={"name": "C", "price": 3}).json["id"]
    assert client.put(f"/api/products/{pid}", json={"name": "C2", "price": 4}).status_code == 204
    assert client.get(f"/api/products/{pid}").json["name"] == "C2"
    assert client.delete(f"/api/products/{pid}").status_code == 204
    assert client.get(f"/api/products/{pid}").status_code == 404
    assert client.put("/api/products/999999", json={"name": "C", "price": 1}).status_code == 404


def test_sql_injection_is_just_a_string(client):
    """SQL 用 ? 參數，惡意字串只會被當成名稱存起來。"""
    name = "x'); DROP TABLE products; --"
    res = client.post("/api/products", json={"name": name, "price": 1})
    assert res.status_code == 201
    assert client.get(f"/api/products/{res.json['id']}").json["name"] == name
