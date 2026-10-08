"""待辦清單：SQLite CRUD，所有端點都要登入（對應講義 6-6、7-4、9-5）。

每條路由都加了 @login_required：沒帶或帶無效 token 一律 401（見 auth.py 與 static/login.html）。
裝飾器的順序有意義：@app.get 在最外層負責註冊路由，@login_required 包住真正的函式先檢查 token。
"""

from flask import abort, url_for

from auth import login_required
from db import get_db
from errors import parse_body
from schemas import CreateTodoDto, Todo, UpdateTodoDto


def _row_to_todo(row) -> dict:
    return Todo.model_validate(dict(row)).to_json()


def _fetch(todo_id: int):
    row = get_db().execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        abort(404)
    return row


def register(app):
    # GET /api/todos：依 id 升序，讓新增的待辦顯示在最後
    @app.get("/api/todos")
    @login_required
    def get_todos():
        rows = get_db().execute("SELECT * FROM todos ORDER BY id").fetchall()
        return [_row_to_todo(r) for r in rows]

    # GET /api/todos/5：除了給前端用，201 的 Location 標頭也靠它產生
    @app.get("/api/todos/<int:todo_id>")
    @login_required
    def get_todo(todo_id: int):
        return _row_to_todo(_fetch(todo_id))

    # POST /api/todos  Body: { "title": "買菜" } → 201
    @app.post("/api/todos")
    @login_required
    def create_todo():
        dto = parse_body(CreateTodoDto)
        db = get_db()
        cursor = db.execute("INSERT INTO todos (title) VALUES (?)", (dto.title,))   # is_done 用資料表預設值 0
        db.commit()
        todo = _row_to_todo(_fetch(cursor.lastrowid))
        return todo, 201, {"Location": url_for("get_todo", todo_id=todo["id"])}

    # PATCH /api/todos/5  Body: { "isDone": true } → 204
    # 部分更新：只改 is_done，不動 title。只更新單一欄位所以用 PATCH 而非 PUT。
    @app.patch("/api/todos/<int:todo_id>")
    @login_required
    def toggle_todo(todo_id: int):
        _fetch(todo_id)
        dto = parse_body(UpdateTodoDto)
        db = get_db()
        db.execute("UPDATE todos SET is_done = ? WHERE id = ?", (int(dto.is_done), todo_id))
        db.commit()
        return "", 204

    # DELETE /api/todos/5 → 204
    @app.delete("/api/todos/<int:todo_id>")
    @login_required
    def delete_todo(todo_id: int):
        _fetch(todo_id)
        db = get_db()
        db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        db.commit()
        return "", 204
