#!/bin/sh
# 啟動 Flask 開發伺服器（macOS / Linux）。以腳本所在目錄為基準，在哪裡執行都可以。
cd "$(dirname "$0")" && uv run flask run
