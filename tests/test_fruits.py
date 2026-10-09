"""水果：In-Memory CRUD、搜尋排序分頁、檔案上傳（講義 3-4、5-8、6-1、8-4）。"""

from io import BytesIO


def test_list_default_page(client):
    res = client.get("/api/fruits")
    assert res.status_code == 200
    body = res.json
    assert body["page"] == 1 and body["size"] == 5
    assert len(body["items"]) == 5
    assert body["total"] == 12 and body["totalPages"] == 3


def test_list_search_sort_page(client):
    res = client.get("/api/fruits?name=果&sort=price_desc&page=1&size=3")
    body = res.json
    names = [f["name"] for f in body["items"]]
    assert all("果" in n for n in names)
    prices = [f["price"] for f in body["items"]]
    assert prices == sorted(prices, reverse=True)
    assert len(body["items"]) <= 3


def test_page_out_of_range_falls_back_to_last_page(client):
    res = client.get("/api/fruits?page=999")
    assert res.json["page"] == res.json["totalPages"]


def test_chinese_is_not_escaped(client):
    """app.json.ensure_ascii = False：中文直接輸出，不轉成 \\uXXXX。"""
    res = client.get("/api/fruits/1")
    assert "蘋果" in res.get_data(as_text=True)


def test_get_one_and_404(client):
    assert client.get("/api/fruits/1").status_code == 200
    res = client.get("/api/fruits/999")
    assert res.status_code == 404
    assert res.json == {"title": "找不到資源", "status": 404}   # 8-3：404 也是 JSON


def test_route_converter_rejects_non_int(client):
    assert client.get("/api/fruits/abc").status_code == 404


def test_create_returns_201_with_location(client):
    res = client.post("/api/fruits", json={"name": "龍眼", "price": 60})
    assert res.status_code == 201
    assert res.headers["Location"].endswith("/api/fruits/13")
    assert res.json == {"id": 13, "name": "龍眼", "price": 60}
    assert client.get("/api/fruits/13").status_code == 200


def test_create_validation_error_format(client):
    """8-4 的契約：400 + errors，key 是欄位名，value 是訊息陣列。"""
    res = client.post("/api/fruits", json={"name": "", "price": -1})
    assert res.status_code == 400
    assert res.json["title"] == "輸入資料有誤"
    assert res.json["errors"]["name"] == ["名稱不可為空"]
    assert res.json["errors"]["price"] == ["價格必須大於 0"]


def test_create_missing_field(client):
    res = client.post("/api/fruits", json={"name": "龍眼"})
    assert res.status_code == 400
    assert res.json["errors"]["price"] == ["此欄位為必填"]


def test_create_without_json_body(client):
    res = client.post("/api/fruits", data="not json", content_type="text/plain")
    assert res.status_code == 400
    assert res.json["title"] == "請求本文必須是 JSON 物件"


def test_update_and_delete(client):
    assert client.put("/api/fruits/1", json={"name": "紅蘋果", "price": 35}).status_code == 204
    assert client.get("/api/fruits/1").json["name"] == "紅蘋果"
    assert client.delete("/api/fruits/1").status_code == 204
    assert client.get("/api/fruits/1").status_code == 404
    assert client.delete("/api/fruits/1").status_code == 404


def test_method_not_allowed_is_json(client):
    res = client.patch("/api/fruits/1", json={})
    assert res.status_code == 405
    assert res.json["status"] == 405


def test_upload_png(client, app):
    data = {"file": (BytesIO(b"\x89PNG fake"), "photo.PNG", "image/png"), "note": "測試"}
    res = client.post("/api/fruits/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.json["url"].startswith("/uploads/") and res.json["url"].endswith(".png")
    assert res.json["note"] == "測試"


def test_upload_rejects_html_and_mismatched_mime(client):
    res = client.post("/api/fruits/upload",
                      data={"file": (BytesIO(b"<script>"), "evil.html", "text/html")},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "只接受" in res.json["errors"]["file"][0]

    res = client.post("/api/fruits/upload",
                      data={"file": (BytesIO(b"x"), "a.png", "image/jpeg")},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert "不符" in res.json["errors"]["file"][0]


def test_upload_without_file(client):
    res = client.post("/api/fruits/upload", data={"note": "沒檔案"},
                      content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.json["errors"]["file"] == ["沒有收到檔案"]


def test_upload_too_large_returns_413(client):
    big = BytesIO(b"0" * (2 * 1024 * 1024 + 1))
    res = client.post("/api/fruits/upload",
                      data={"file": (big, "big.png", "image/png")},
                      content_type="multipart/form-data")
    assert res.status_code == 413
    assert res.json["status"] == 413
