#!/bin/sh
# 啟動金門返台交通助手，預設 8000 埠：./start.sh 或 ./start.sh 8080
cd "$(dirname "$0")"
[ -f .env ] || echo "提醒：找不到 .env，即時資料無法使用，請參考 .env.example（模擬模式仍可使用）"
exec python3 server.py "${1:-8000}"
