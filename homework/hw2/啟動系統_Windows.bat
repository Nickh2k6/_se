@echo off
REM 國立金門大學 校務行政資訊系統 - 本機啟動（Windows）
REM 用法：雙擊本檔，或在命令提示字元執行「啟動系統_Windows.bat 8080」指定其他埠
chcp 65001 >nul
cd /d "%~dp0"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"
set "URL=http://localhost:%PORT%/index.html"

set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo 找不到 Python，請直接用瀏覽器開啟 index.html
  pause
  exit /b 1
)

echo ============================================
echo   校務行政資訊系統 - 本機伺服器
echo   網址： %URL%
echo   關掉這個視窗或按 Ctrl+C 可停止伺服器
echo ============================================

start "" "%URL%"
%PY% -m http.server %PORT%
pause
