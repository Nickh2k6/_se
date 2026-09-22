#!/usr/bin/env bash
# 國立金門大學 校務行政資訊系統 - 本機啟動（macOS / Linux / WSL）
set -e
cd "$(dirname "$0")"

PORT="${1:-8000}"
URL="http://localhost:${PORT}/index.html"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "找不到 Python，請直接用瀏覽器開啟 index.html"
  exit 1
fi

echo "============================================"
echo "  校務行政資訊系統 - 本機伺服器"
echo "  網址： ${URL}"
echo "  按 Ctrl+C 可停止伺服器"
echo "============================================"

# 嘗試自動開啟瀏覽器（WSL 會用 Windows 的預設瀏覽器）
( sleep 1
  if command -v wslview >/dev/null 2>&1; then wslview "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  elif command -v open >/dev/null 2>&1; then open "$URL"
  fi ) >/dev/null 2>&1 &

exec "$PY" -m http.server "$PORT"
