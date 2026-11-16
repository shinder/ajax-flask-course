#!/bin/sh
# 用 gunicorn 啟動正式環境伺服器（macOS / Linux）。以腳本所在目錄為基準，在哪裡執行都可以。
# gunicorn 不像 flask run 會自動讀 .env，所以交給 uv 的 --env-file 先載入 JWT_KEY 與 SECRET_KEY。
# 沒有 debug 模式也不會自動重載，改程式要重新執行；平常開發請用 ./start.sh。
cd "$(dirname "$0")" && uv run --env-file .env gunicorn --workers 4 --bind 0.0.0.0:8000 "my_ajax_api:create_app()"
