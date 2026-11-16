@echo off
cd /d "%~dp0"
uv run flask run --host=0.0.0.0
