@echo off
rem 啟動 Flask 開發伺服器（Windows cmd 或 PowerShell 皆可執行）
cd /d "%~dp0"
uv run flask run
