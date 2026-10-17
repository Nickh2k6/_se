# hw5：跨樓層 AMR 導航 — Docker 化開發環境

用 Docker 建立跨樓層 AMR（自主移動機器人）的開發與監控環境。分三步逐步完成，每一步都是在前一步的基礎上加功能，所以三個資料夾都保留，方便對照每一步改了什麼。

| 資料夾 | 內容 | 新增的服務 |
|---|---|---|
| [step1-ros-docker](step1-ros-docker/README.md) | ROS 2 Humble 開發容器（Nav2、SLAM Toolbox）+ rosbridge，Gazebo / RViz2 留在主機原生執行 | `ros_dev`、`rosbridge` |
| [step2-nginx-web](step2-nginx-web/README.md) | Nginx 監控網頁，透過 rosbridge 即時顯示樓層與機器人位姿 | `nginx` |
| [step3-api-db](step3-api-db/README.md) | FastAPI + PostgreSQL，自動記錄樓層變化、手動記錄巡檢事件，網頁加上歷史紀錄頁 | `api`、`postgres` |

**最終版本是 `step3-api-db`**，裡面包含前兩步的所有東西。每個資料夾的 README 都有完整的安裝、啟動、驗證步驟。

## 架構（第 3 步）

```
瀏覽器 http://localhost:8080
        │
        ▼
     nginx ──/api/──────► api (FastAPI) ──► postgres
        │                    │
        └──/rosbridge/──┐    │ WebSocket
                        ▼    ▼
                     rosbridge :9090 ◄── DDS ──► ros_dev / Gazebo / RViz2
```

- `nginx`、`api` 在 `web` 網路；`api`、`postgres` 在 `backend` 網路（internal，不對外）
- `ros_dev`、`rosbridge` 用 host 網路，因為 ROS 2 的 DDS 需要 multicast
- 對外只開 8080 一個 port

## 快速開始（以第 3 步為例）

```bash
cd step3-api-db
cp .env.example .env            # 填入 id -u / id -g 的值
docker compose up -d --build
```

打開 http://localhost:8080 看即時監控頁，http://localhost:8080/history.html 看歷史紀錄。

## ROS 2 範例節點：floor_status

三個步驟共用同一個套件 `src/floor_status/`，`floor_publisher` 節點會把目前樓層發布到 `/current_floor`（`std_msgs/Int32`），用來測試容器和主機的通訊：

```bash
ros2 run floor_status floor_publisher
ros2 param set /floor_publisher floor 2   # 改樓層
```

## 學到的觀念

| 步驟 | 重點 |
|---|---|
| 第 1 步 | Dockerfile（`RUN` 合併、`ARG`、非 root 使用者、`ENTRYPOINT` vs `CMD`）、bind mount vs named volume、`network_mode: host`、DDS shared memory 陷阱 |
| 第 2 步 | bridge 網路怎麼連到 host 網路（`host.docker.internal`）、Nginx 反向代理 WebSocket |
| 第 3 步 | 多個網路隔離服務、`depends_on` + healthcheck、named volume 保存資料庫、layer cache 加速 build |
