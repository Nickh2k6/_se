# FastAPI 服務：不需要 ROS！
# 它透過 rosbridge 的 WebSocket 拿 ROS 資料，所以 image 只要純 Python，
# 比 ROS image 小非常多（約 200 MB vs 數 GB）
FROM python:3.12-slim

# 不產生 .pyc、log 立刻輸出（不然 docker logs 會看不到即時訊息）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先只複製 requirements.txt 再安裝 —— 這是 Docker layer cache 的關鍵：
# 只改程式碼時，這一層會直接用快取，不用每次重新 pip install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 程式碼最後才複製（最常改的放最後）
COPY app/ ./app/

# 非 root 執行
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# slim image 沒有 curl，用 Python 自己打 health endpoint
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
