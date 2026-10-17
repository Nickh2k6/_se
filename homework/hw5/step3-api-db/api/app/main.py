"""
AMR 巡檢紀錄 API

資料流：
    ROS 2 ──DDS──► rosbridge (host 網路, :9090)
                       │ WebSocket
                       ▼
    本服務 (bridge 網路) ── 背景任務訂閱 /current_floor 和位姿 topic
                       │ 樓層改變時寫入
                       ▼
                  PostgreSQL (只在內部 backend 網路)

為什麼不在 ROS 節點裡直接寫資料庫？
→ 讓 ROS 容器保持單純（不用裝資料庫驅動），API 容器也不用裝 ROS。
  兩邊只靠 rosbridge 的 JSON 協定溝通，各自可以獨立重啟、升級。
"""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal, Optional

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from websockets.asyncio.client import connect as ws_connect

# ---------------------------------------------------------------- 設定
# 全部從環境變數讀，值寫在 docker-compose.yml / .env —— 程式碼裡不放密碼
DATABASE_URL = os.environ["DATABASE_URL"]
ROSBRIDGE_URL = os.environ.get("ROSBRIDGE_URL", "ws://host.docker.internal:9090")
POSE_TOPIC = os.environ.get("POSE_TOPIC", "/odom")
POSE_TYPE = os.environ.get("POSE_TYPE", "nav_msgs/msg/Odometry")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("amr_api")

# 最新的機器人狀態（記憶體中，給 /api/status 和新增事件時用）
state = {
    "floor": None,
    "x": None,
    "y": None,
    "rosbridge_connected": False,
    "last_message_at": None,
}


# ---------------------------------------------------------------- rosbridge 監聽
async def ros_listener(pool: asyncpg.Pool) -> None:
    """持續連線 rosbridge；斷線就指數退避重連，永不放棄。"""
    # 從資料庫讀回最後一次記錄的樓層，API 重啟後才不會重複記一筆
    last_recorded = await pool.fetchval(
        "SELECT to_floor FROM floor_changes ORDER BY ts DESC LIMIT 1"
    )
    backoff = 1

    while True:
        try:
            async with ws_connect(ROSBRIDGE_URL, open_timeout=5, ping_interval=20) as ws:
                state["rosbridge_connected"] = True
                backoff = 1
                log.info("已連線 rosbridge：%s", ROSBRIDGE_URL)

                await ws.send(json.dumps({
                    "op": "subscribe", "topic": "/current_floor",
                    "type": "std_msgs/msg/Int32",
                }))
                # 位姿只拿來附在紀錄上，每 0.5 秒一筆就夠
                await ws.send(json.dumps({
                    "op": "subscribe", "topic": POSE_TOPIC, "type": POSE_TYPE,
                    "throttle_rate": 500, "queue_length": 1,
                }))

                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("op") != "publish":
                        if data.get("op") == "status" and data.get("level") == "error":
                            log.warning("rosbridge：%s", data.get("msg"))
                        continue

                    state["last_message_at"] = datetime.now(timezone.utc)
                    topic, msg = data["topic"], data["msg"]

                    if topic == POSE_TOPIC:
                        pos = msg["pose"]["pose"]["position"]
                        state["x"], state["y"] = pos["x"], pos["y"]

                    elif topic == "/current_floor":
                        floor = int(msg["data"])
                        state["floor"] = floor
                        if floor != last_recorded:
                            await pool.execute(
                                "INSERT INTO floor_changes (from_floor, to_floor, x, y) "
                                "VALUES ($1, $2, $3, $4)",
                                last_recorded, floor, state["x"], state["y"],
                            )
                            log.info("樓層變化：%s → %s", last_recorded, floor)
                            last_recorded = floor

        except asyncio.CancelledError:
            raise   # 服務關閉時要讓任務正常結束
        except Exception as e:  # noqa: BLE001 —— 任何錯誤都只記錄然後重連
            log.warning("rosbridge 連線中斷（%s: %s），%d 秒後重試", type(e).__name__, e, backoff)

        state["rosbridge_connected"] = False
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)


# ---------------------------------------------------------------- 生命週期
async def create_pool_with_retry(retries: int = 10) -> asyncpg.Pool:
    """compose 的 depends_on 已經等資料庫 healthy，這裡再加一層保險。"""
    for attempt in range(1, retries + 1):
        try:
            return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        except (OSError, asyncpg.PostgresError) as e:
            log.warning("資料庫尚未就緒（第 %d 次）：%s", attempt, e)
            await asyncio.sleep(2)
    raise RuntimeError("無法連線資料庫")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool_with_retry()
    listener = asyncio.create_task(ros_listener(app.state.pool))
    yield
    listener.cancel()
    try:
        await listener
    except asyncio.CancelledError:
        pass
    await app.state.pool.close()


app = FastAPI(title="AMR 巡檢紀錄 API", lifespan=lifespan)


# ---------------------------------------------------------------- 資料模型
class EventIn(BaseModel):
    kind: Literal["info", "warning", "error"] = "info"
    message: str = Field(min_length=1, max_length=500)
    floor: Optional[int] = None   # 不填就用機器人目前的樓層


# ---------------------------------------------------------------- 路由
@app.get("/api/health")
async def health():
    """給 Docker healthcheck 用：資料庫連得到才算健康。"""
    try:
        await app.state.pool.fetchval("SELECT 1")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"database unavailable: {e}")
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    return state


@app.get("/api/floor-changes")
async def floor_changes(limit: int = Query(50, ge=1, le=500)):
    rows = await app.state.pool.fetch(
        "SELECT id, ts, from_floor, to_floor, x, y FROM floor_changes "
        "ORDER BY ts DESC LIMIT $1", limit,
    )
    return [dict(r) for r in rows]


@app.get("/api/events")
async def list_events(
    limit: int = Query(50, ge=1, le=500),
    floor: Optional[int] = None,
    kind: Optional[Literal["info", "warning", "error"]] = None,
):
    # 用 $n 參數化查詢，不要用字串拼接 SQL（避免 SQL injection）
    rows = await app.state.pool.fetch(
        "SELECT id, ts, kind, message, floor, x, y FROM patrol_events "
        "WHERE ($1::int IS NULL OR floor = $1) AND ($2::text IS NULL OR kind = $2) "
        "ORDER BY ts DESC LIMIT $3",
        floor, kind, limit,
    )
    return [dict(r) for r in rows]


@app.post("/api/events", status_code=201)
async def create_event(event: EventIn):
    floor = event.floor if event.floor is not None else state["floor"]
    row = await app.state.pool.fetchrow(
        "INSERT INTO patrol_events (kind, message, floor, x, y) "
        "VALUES ($1, $2, $3, $4, $5) "
        "RETURNING id, ts, kind, message, floor, x, y",
        event.kind, event.message, floor, state["x"], state["y"],
    )
    return dict(row)
