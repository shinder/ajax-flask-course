"""Jinja 模板版的頁面：/pages/*（pages.py 與 templates/）。

頁面上的資料是瀏覽器用 AJAX 取得的，test client 不會執行 JavaScript，
所以這裡只確認伺服器組出來的 HTML 骨架：版型有套上、導覽列的連結與目前頁面的標示正確。
"""

import pytest

# （網址, 分頁標題, 導覽列上的文字）
PAGES = [
    ("/pages/", "待辦清單", "待辦清單"),
    ("/pages/fruits", "水果清單", "水果清單"),
    ("/pages/products", "商品管理", "商品管理"),
    ("/pages/upload", "檔案上傳", "檔案上傳"),
    ("/pages/sync-demo", "同步 vs 非同步", "同步 vs 非同步"),
    ("/pages/sse-demo", "SSE 推送", "SSE 推送"),
    ("/pages/login", "登入", "JWT 登入"),
    ("/pages/login-session", "Session 登入", "Session 登入"),
]


@pytest.mark.parametrize(("url", "title", "nav_label"), PAGES)
def test_page_renders_with_layout(client, url, title, nav_label):
    res = client.get(url)
    assert res.status_code == 200
    assert res.mimetype == "text/html"
    html = res.text

    # 版型：標題、共用樣式表、<main> 外框都來自 base.html
    assert f"<title>{title} — Flask AJAX API</title>" in html
    assert '<link rel="stylesheet" href="/css/style.css" />' in html
    assert "<main>" in html and "</main>" in html

    # 導覽列有全部 8 個連結，而且只有目前這一頁被標成 aria-current
    for nav_url, _, _ in PAGES:
        assert f'<a href="{nav_url}"' in html
    assert f'<a href="{url}" aria-current="page">{nav_label}</a>' in html
    assert html.count('aria-current="page"') == 2  # 一個在 <style> 的選擇器，一個在導覽列

    # 模板語法與 Jinja 註解都已處理完，沒有原樣漏到瀏覽器
    for leftover in ("{%", "%}", "{{", "}}", "{#", "#}", "Jinja"):
        assert leftover not in html


def test_pages_without_trailing_slash_redirects(client):
    res = client.get("/pages")
    assert res.status_code == 308
    assert res.headers["Location"].endswith("/pages/")


def test_links_inside_content_point_to_pages(client):
    """內文裡連到登入頁的連結也要留在 /pages 底下，不能跳回靜態版。"""
    for url in ("/pages/", "/pages/login-session"):
        html = client.get(url).text
        assert '<a href="/pages/login">' in html
        assert ".html" not in html.split("<script")[0]


def test_unknown_page_is_json_404(client):
    res = client.get("/pages/nope")
    assert res.status_code == 404
    assert res.json["status"] == 404


def test_static_pages_still_served(client):
    """靜態版原封不動：兩種版本並存。"""
    res = client.get("/fruits.html")
    assert res.status_code == 200
    assert '<a href="/fruits.html">水果清單</a>' in res.text
