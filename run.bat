@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [首次运行] 正在创建虚拟环境并安装依赖，请稍候...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    echo.
    echo 依赖安装完成，正在启动...
)

start "" ".venv\Scripts\pythonw.exe" app.py
