@echo off
cd /d "%~dp0"
uv run --env-file .env waitress-serve --listen=0.0.0.0:8000 --threads=4 --call my_ajax_api:create_app
