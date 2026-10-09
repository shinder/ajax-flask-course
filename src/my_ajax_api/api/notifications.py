"""Server-Sent Events（SSE）範例，對應講義 6-2。

一條 HTTP 連線不關閉，伺服器每 2 秒推一筆資料，瀏覽器用 EventSource 接收。
Flask 用「產生器函式」做串流：每次 yield 就送出一段，函式不結束連線就不關。
"""

import json
import time
from datetime import datetime, timezone

from flask import Blueprint, Response, stream_with_context

from my_ajax_api.api import fruits

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


# GET /api/notifications/stream
@bp.get("/stream")
def stream_notifications():
    def generate():
        seq = 0
        try:
            while True:
                seq += 1
                payload = {
                    "seq": seq,
                    "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "fruitCount": fruits.count(),
                }
                # SSE 的格式：每則訊息是一行以 "data: " 開頭的文字，用「空一行」結尾
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                time.sleep(2)
        except GeneratorExit:
            # 瀏覽器關閉連線（source.close() 或關掉分頁）時，下一次 yield 會收到 GeneratorExit，
            # 這是正常結束，不是錯誤；這裡可以做清理工作（本範例不需要）
            pass

    # SSE 的三個必要條件：Content-Type 是 text/event-stream、不要快取、不要緩衝。
    # stream_with_context 讓產生器執行期間仍能存取 request / g（本範例沒用到，但是慣用寫法）。
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 若前面有 nginx 之類的反向代理，叫它不要緩衝
        },
    )
