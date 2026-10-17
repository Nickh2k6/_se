# hw5：跨樓層 AMR 導航 — Docker 化 ROS 2 開發環境

用 Docker 建立 ROS 2 Humble 開發環境（Nav2、SLAM Toolbox、rosbridge），Gazebo 和 RViz2 留在主機原生執行，兩邊透過 host 網路的 DDS 互通。
並寫了一個 ROS 2 範例節點 `floor_status`，發布目前樓層到 `/current_floor`，用來測試容器和主機之間的通訊。

完整的安裝、啟動、驗證步驟請看 [amr_docker/README.md](amr_docker/README.md)。

## 檔案結構

| 檔案 | 說明 |
|------|------|
| `amr_docker/docker-compose.yml` | 兩個 service：`ros_dev`（開發容器）、`rosbridge`（WebSocket :9090） |
| `amr_docker/.env.example` | UID/GID、`ROS_DOMAIN_ID` 設定範本 |
| `amr_docker/docker/Dockerfile` | ROS 2 Humble + Nav2 + SLAM Toolbox + rosbridge，建立和主機相同 UID 的使用者 |
| `amr_docker/docker/entrypoint.sh` | 容器啟動時載入 ROS 2 環境 |
| `amr_docker/docker/fastdds_udp.xml` | 強制 DDS 只走 UDP，避開 shared memory 收不到資料的問題 |
| `amr_docker/src/floor_status/` | ROS 2 Python 套件，`floor_publisher` 節點發布 `/current_floor` |
| `amr_docker/maps/` | 各樓層地圖（bind mount 到容器的 `/ws/maps`） |

## 快速開始

```bash
cd amr_docker
cp .env.example .env            # 填入 id -u / id -g 的值
docker compose up -d --build
docker compose exec ros_dev bash
```

## 驗證項目

1. 主機 → 容器：主機跑 `talker`，容器內 `ros2 topic echo /chatter` 收得到
2. 容器 → 主機：容器內 build 並執行 `floor_publisher`，主機 `ros2 topic echo /current_floor` 收得到
3. rosbridge：`docker compose logs rosbridge` 看到 WebSocket server 在 9090 啟動

## 學到的觀念

- **Dockerfile**：`RUN` 合併與清快取、`ARG` 建置參數、非 root 使用者、`ENTRYPOINT` vs `CMD`
- **Volume**：bind mount（`src/`、`maps/`）vs named volume（`build/`、`install/`、`log/`）
- **網路**：ROS 2 的 DDS 需要 multicast，所以用 `network_mode: host`
- **Compose**：YAML anchor 共用設定、`.env` 環境變數
