# 跨樓層 AMR 導航 — Docker 環境（第 1 步）

ROS 2 Humble 開發容器 + rosbridge。Gazebo 和 RViz2 留在主機原生執行，容器透過 host 網路與它們互通。

```
┌──────────────── 主機 (Ubuntu 22.04) ────────────────┐
│                                                      │
│   Gazebo   RViz2         ← 原生執行（有 GUI、GPU）    │
│      │       │                                       │
│      └───────┴──── DDS (UDP, host 網路) ─────┐       │
│                                              │       │
│   ┌─ ros_dev 容器 ─────────┐  ┌─ rosbridge 容器 ─┐   │
│   │ Nav2 / SLAM Toolbox    │  │ WebSocket :9090  │   │
│   │ 自己的節點 (src/)       │  │ (給第 2 步網頁)   │   │
│   └────────────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────┘
```

## 目錄結構

```
amr_docker/
├── docker-compose.yml       # 兩個 service：ros_dev、rosbridge
├── .env.example             # UID/GID、ROS_DOMAIN_ID
├── docker/
│   ├── Dockerfile           # ROS 2 Humble + Nav2 + SLAM Toolbox + rosbridge
│   ├── entrypoint.sh        # 啟動時 source ROS 環境
│   └── fastdds_udp.xml      # 強制 DDS 走 UDP（避開 shared memory 問題）
├── src/                     # ROS 2 套件（bind mount 進容器的 /ws/src）
│   └── floor_status/        # 範例：發布 /current_floor
└── maps/                    # 地圖（bind mount 進容器的 /ws/maps）
```

---

## 0. 安裝 Docker（只需做一次）

```bash
# Docker Engine + Compose plugin（官方 apt 源）
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 讓自己不用 sudo 就能跑 docker（登出再登入才生效）
sudo usermod -aG docker $USER
```

確認：`docker run --rm hello-world`

## 1. 設定與啟動

```bash
cd amr_docker
cp .env.example .env
id -u && id -g          # 把這兩個數字填進 .env 的 USER_UID / USER_GID

docker compose up -d --build     # 第一次 build 約 5–10 分鐘
docker compose ps                # 應看到 ros_dev、rosbridge 都是 running
```

## 2. 驗證：主機 ↔ 容器 能互通

**主機 → 容器**

```bash
# 主機終端機 A
ros2 run demo_nodes_cpp talker

# 主機終端機 B：進入容器
docker compose exec ros_dev bash
ros2 topic echo /chatter         # 要能看到 "Hello World: N"
```

**容器 → 主機**（順便練習在容器內 build）

```bash
# 容器內
cd /ws
colcon build --symlink-install
source install/setup.bash
ros2 run floor_status floor_publisher

# 主機
ros2 topic echo /current_floor   # 要看到 data: 1

# 改樓層（主機或容器都可以）
ros2 param set /floor_publisher floor 2
```

**rosbridge**

```bash
docker compose logs rosbridge    # 要看到 "Rosbridge WebSocket server started on port 9090"
```

三項都通過，第 1 步就完成了。

## 3. 實際用途：主機跑 Gazebo，容器跑 SLAM 建圖

```bash
# 主機：照平常方式啟動你的 Gazebo 模擬

# 容器內：確認看得到模擬器的 topic
ros2 topic list                  # 應該有 /scan、/odom、/tf ...

# 容器內：SLAM Toolbox 建圖（模擬器記得用 sim time）
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true

# 主機：開 RViz2 看建圖結果、用鍵盤遙控機器人繞一圈

# 容器內：存地圖 → 主機的 amr_docker/maps/ 會直接出現檔案
ros2 run nav2_map_server map_saver_cli -f /ws/maps/floor1
```

---

## 常用指令

| 用途 | 指令 |
|---|---|
| 啟動 | `docker compose up -d` |
| 進入容器 | `docker compose exec ros_dev bash` |
| 看 log | `docker compose logs -f rosbridge` |
| 停止 | `docker compose down` |
| 停止並清掉 build 產物 | `docker compose down -v` |
| 改了 Dockerfile 後重建 | `docker compose up -d --build` |

## 常見問題

| 症狀 | 原因與解法 |
|---|---|
| `ros2 topic list` 看不到主機的 topic | 檢查兩邊 `ROS_DOMAIN_ID` 是否相同（`echo $ROS_DOMAIN_ID`）；確認容器是 `network_mode: host` |
| 看得到 topic，但 `echo` 沒有資料 | shared memory 問題。確認容器內 `echo $FASTRTPS_DEFAULT_PROFILES_FILE` 有值；主機那端如果也出問題，主機也設同一個環境變數指向一份 `fastdds_udp.xml` |
| 容器內 build 出來的檔案在主機上是 root 的 | `.env` 的 UID/GID 沒填對，修正後 `docker compose up -d --build` |
| SLAM 地圖亂跳、TF 時間錯誤 | 容器內的節點沒加 `use_sim_time:=true` |
| `permission denied ... docker.sock` | `usermod -aG docker` 之後要登出再登入 |

## 這一步練到的 Docker 觀念

- **Dockerfile**：base image、`RUN` 合併與快取清理、`ARG` 建置參數、非 root 使用者、`ENTRYPOINT` vs `CMD`
- **Volume**：bind mount（`src/`、`maps/` 雙向同步）vs named volume（`build/`、`install/` 隔離）
- **網路**：為什麼 ROS 2 要用 `network_mode: host`，以及 DDS shared memory 的陷阱
- **Compose**：多個 service 共用 image、YAML anchor 減少重複、`.env` 環境變數

## 下一步（第 2 步）

加 Nginx + 簡單網頁，透過 rosbridge 即時顯示 `/current_floor` 和機器人座標。
注意：rosbridge 用 host 網路，Nginx 用 bridge 網路，兩者怎麼接是第 2 步的重點練習。
