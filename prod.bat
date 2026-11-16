@echo off
chcp 65001 >nul
rem 啟動正式環境伺服器（Windows cmd 或 PowerShell 皆可執行）
rem gunicorn 依賴 Unix 專屬的 fcntl 模組，Windows 原生跑不起來，所以這裡改用 waitress，
rem 它是純 Python 的 WSGI 伺服器，功能定位和 gunicorn 相同。想用 gunicorn 請在 WSL 裡執行 ./prod.sh。
rem pyproject.toml 用環境標記讓 Windows 只裝 waitress、其他系統只裝 gunicorn，uv sync 會自動處理。
rem waitress 不像 flask run 會自動讀 .env，所以交給 uv 的 --env-file 先載入 JWT_KEY 與 SECRET_KEY。
rem 沒有 debug 模式也不會自動重載，改程式要重新執行；平常開發請用 .\start.bat。
cd /d "%~dp0"
uv run --env-file .env waitress-serve --listen=0.0.0.0:8000 --threads=4 --call my_ajax_api:create_app
