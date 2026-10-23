# 跨樓層 AMR 導航 — Docker 環境

- **第 1 步**：ROS 2 Humble 開發容器 + rosbridge。Gazebo 和 RViz2 留在主機原生執行，容器透過 host 網路與它們互通。
- **第 2 步**：Nginx 監控網頁，即時顯示樓層與機器人位姿。
- **第 3 步**：FastAPI + PostgreSQL，自動記錄樓層變化、手動記錄巡檢事件，網頁加上歷史紀錄頁。

```
  瀏覽器 http://localhost:8080
        │
┌───────┼─────────────────────── 主機 (Ubuntu 22.04) ─────────────────────────┐
│       ▼ :8080（唯一對外的 port）                                            │
│  ┌─ nginx ─────────────────┐                                                │
│  │ /           → 靜態網頁   │                          ── web 網路 (bridge) ──│
│  │ /api/       → api:8000 ──┼──► ┌─ api (FastAPI) ─┐                         │
│  │ /rosbridge/ → 主機 :9090 ┼─┐  │ 訂閱樓層/位姿    ├──┐                      │
│  └─────────────────────────┘ │  └───────┬─────────┘  │                      │
│                              │          │ SQL         │                      │
│                              │  ┌───────▼─────────┐  │ ─ backend 網路 ─      │
│                              │  │ postgres        │  │   (internal,         │
│                              │  │ volume: pgdata  │  │    不對外)           │
│                              │  └─────────────────┘  │                      │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│                              ▼ host.docker.internal  ▼        ── host 網路 ── │
│   Gazebo  RViz2     ┌─ ros_dev ─────────────┐  ┌─ rosbridge :9090 ┐          │
│   (原生執行)         │ Nav2 / SLAM / 自己節點 │  └────────┬─────────┘          │
│      └──────────────┴────── DDS (UDP) ──────┴───────────┘                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 目錄結構

```
step3-api-db/
├── docker-compose.yml       # 五個 service：ros_dev、rosbridge、nginx、api、postgres
├── .env.example             # UID/GID、ROS_DOMAIN_ID、資料庫帳密
├── docker/
│   ├── Dockerfile           # ROS 2 Humble + Nav2 + SLAM Toolbox + rosbridge
│   ├── entrypoint.sh        # 啟動時 source ROS 環境
│   └── fastdds_udp.xml      # 強制 DDS 走 UDP（避開 shared memory 問題）
├── src/                     # ROS 2 套件（bind mount 進容器的 /ws/src）
│   └── floor_status/        # 範例：發布 /current_floor
├── nginx/
│   └── default.conf         # 靜態網頁 + /rosbridge/ 和 /api/ 反向代理
├── web/
│   ├── index.html           # 即時監控（原生 rosbridge JSON 協定，不用 roslib）
│   └── history.html         # 歷史紀錄 + 新增巡檢事件
├── api/
│   ├── Dockerfile           # python:3.12-slim，不需要 ROS
│   ├── requirements.txt
│   └── app/main.py          # FastAPI + rosbridge 監聽背景任務
├── db/
│   └── init.sql             # 第一次建立資料庫時自動建表
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
cd step3-api-db
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

# 容器內：存地圖 → 主機的 step3-api-db/maps/ 會直接出現檔案
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

---

# 第 2 步：Nginx 監控網頁

## 啟動

```bash
docker compose up -d          # 會多啟動 amr_nginx 容器
docker compose ps             # amr_nginx 狀態要是 running (healthy)
```

瀏覽器開 **http://localhost:8080**，右上角要顯示「已連線 rosbridge」。

## 驗證

**樓層**：容器內跑 `floor_publisher`，網頁的大數字應該顯示 1；改參數後要即時變 2。

```bash
# 容器內
ros2 run floor_status floor_publisher

# 另一個終端機
ros2 param set /floor_publisher floor 2
```

**位姿**：沒開 Gazebo 也能測，手動發一個假的 `/odom`：

```bash
ros2 topic pub -r 5 /odom nav_msgs/msg/Odometry \
  "{pose: {pose: {position: {x: 2.0, y: 1.0}, orientation: {z: 0.383, w: 0.924}}}}"
```

網頁應該顯示 x=2.000、y=1.000、θ≈45°，軌跡圖上出現三角形。
開 Gazebo 遙控機器人時，軌跡會跟著畫出來；跑 AMCL 時可以把下拉選單切到 `/amcl_pose`。

**看 WebSocket 的實際內容**：瀏覽器按 F12 → Network → 點 `rosbridge/` → Messages，
可以看到送出的 `subscribe` 和收到的 `publish` JSON。

## 這一步的重點：bridge 網路怎麼連到 host 網路

| | nginx | rosbridge |
|---|---|---|
| 網路模式 | bridge（`web` 網路） | host |
| 容器裡的 `localhost` | nginx 容器自己 | 主機 |
| 對外 port | 用 `ports: 8080:80` 映射 | 直接用主機的 9090 |

所以在 nginx 裡寫 `proxy_pass http://localhost:9090` 是**連不到**的。
解法是 compose 加上 `extra_hosts: host.docker.internal:host-gateway`，
讓 `host.docker.internal` 指向主機的 docker0 介面（通常是 `172.17.0.1`），再從那裡連到 9090。

自己驗證看看：

```bash
docker compose exec nginx cat /etc/hosts                       # 看到 host.docker.internal 對應的 IP
docker compose exec nginx wget -qO- http://localhost:9090
# → Connection refused：localhost 是 nginx 自己，上面沒有 9090

docker compose exec nginx wget -qO- http://host.docker.internal:9090
# → 400 Bad Request：連到 rosbridge 了，只是它只接受 WebSocket，不接受一般 HTTP
```

兩個都是錯誤，但意義完全不同：**Connection refused 是「找不到人」，400 是「有人接，只是格式不對」**。
除錯網路問題時，分辨這兩種錯誤非常重要。

## 第 2 步常見問題

| 症狀 | 原因與解法 |
|---|---|
| 網頁顯示「已斷線」，nginx log 出現 `502 Bad Gateway` | rosbridge 沒開（`docker compose logs rosbridge`），或防火牆擋住 docker 網段連主機 9090：`sudo ufw status` 若為 active，執行 `sudo ufw allow from 172.16.0.0/12 to any port 9090` |
| 已連線但數字一直是 `–` | 該 topic 沒有人發布。用 `ros2 topic list` 確認；事件紀錄區有 rosbridge 錯誤訊息的話照著看 |
| 改了 `index.html` 沒變化 | 瀏覽器快取，按 `Ctrl+Shift+R` 強制重新整理（網頁是 bind mount，不用重啟容器） |
| 改了 `default.conf` 沒變化 | `docker compose restart nginx` |
| 連線一陣子後自己斷掉 | 正常會自動重連；如果很頻繁，檢查 `proxy_read_timeout` |

## 第 2 步練到的 Docker 觀念

- **混用網路模式**：host 網路 vs bridge 網路，以及 `host-gateway` 這個特殊值
- **Port 映射**：`ports:` 只對 bridge 網路有意義，host 網路的容器直接佔用主機 port
- **唯讀掛載**：`:ro` 讓容器不能改動設定檔和網頁
- **Healthcheck**：`docker compose ps` 看到的 `(healthy)` 從哪裡來
- **反向代理**：WebSocket 需要 `Upgrade` / `Connection` 標頭才能穿過 Nginx

---

# 第 3 步：FastAPI + PostgreSQL 巡檢紀錄

## 啟動

如果你的 `.env` 是第 1 步建立的，把 `.env.example` 裡「第 3 步」那幾行補進去
（不補也可以，compose 裡有預設值）。

```bash
docker compose up -d --build     # 會多 build 一個 api image，並下載 postgres
docker compose ps
```

五個容器都要是 running，其中 `amr_postgres`、`amr_api`、`amr_nginx` 要顯示 `(healthy)`。
啟動順序是 **postgres healthy → api 啟動並 healthy → nginx 啟動**，由 `depends_on` 的 `condition` 控制。

## 驗證

**1. API 文件**：瀏覽器開 http://localhost:8080/docs ，FastAPI 自動產生的 Swagger 頁面，每個 API 都可以直接按「Try it out」測試。

**2. 用 curl 打 API**

```bash
curl http://localhost:8080/api/health
curl http://localhost:8080/api/status

curl -X POST http://localhost:8080/api/events \
  -H "Content-Type: application/json" \
  -d '{"kind": "warning", "message": "2F 走廊有障礙物"}'

curl "http://localhost:8080/api/events?kind=warning"
```

**3. 樓層變化自動記錄**：容器內跑 `floor_publisher`，然後改幾次樓層：

```bash
ros2 run floor_status floor_publisher            # 容器內
ros2 param set /floor_publisher floor 2          # 另一個終端機
ros2 param set /floor_publisher floor 3
```

開 http://localhost:8080/history.html ，「樓層變化」應該出現 `–F → 1F`、`1F → 2F`、`2F → 3F` 三筆。
右上角「API ↔ rosbridge」是綠燈，代表 api 容器有連上 rosbridge。

**4. 直接查資料庫**

```bash
docker compose exec postgres psql -U amr -d amr
```

```sql
\dt                                          -- 列出資料表
SELECT * FROM floor_changes ORDER BY ts DESC;
SELECT kind, count(*) FROM patrol_events GROUP BY kind;
\q
```

## 動手實驗（這一步真正要練的東西）

**實驗 A：資料持久化 —— volume 的意義**

```bash
docker compose down              # 刪掉所有容器
docker compose up -d
# → 歷史紀錄還在！資料存在 pgdata volume 裡，不在容器裡

docker compose down -v           # -v 連 volume 一起刪
docker compose up -d
# → 紀錄全部消失，init.sql 重新執行建出空的資料表
```

**實驗 B：網路隔離 —— 誰能連到誰**

```bash
# api 在 web + backend 兩個網路 → 兩邊都連得到
docker compose exec api python -c "import socket; socket.create_connection(('postgres', 5432), 2); print('api → postgres OK')"

# nginx 只在 web 網路 → 連 "postgres" 這個名字都查不到
docker compose exec nginx nslookup postgres 127.0.0.11
docker compose exec nginx nslookup api 127.0.0.11      # 對照組：api 查得到

# 主機也連不到，因為 postgres 沒有 ports，backend 又是 internal
nc -zv -w 2 localhost 5432
```

想從主機用 DBeaver 之類的工具看資料庫的話，要在 postgres 加 `ports: ["127.0.0.1:5432:5432"]`，
而且要加在 `127.0.0.1` 上，不然整個區網都連得到你的資料庫。

**實驗 C：Docker layer cache**

隨便改一行 `api/app/main.py`（例如改 log 文字），然後：

```bash
docker compose build api
```

觀察輸出：`pip install` 那一層會顯示 `CACHED`，只有 `COPY app/` 之後的層重新執行，幾秒就完成。
再試著改 `requirements.txt` 加一個空行，重新 build，這次 `pip install` 就會整個重跑。
這就是 Dockerfile 要「先複製 requirements.txt、最後才複製程式碼」的原因。

**實驗 D：服務重啟後的 DNS**

```bash
docker compose up -d --force-recreate api    # 重建 api，IP 通常會變
curl http://localhost:8080/api/health        # 仍然正常
```

這要歸功於 `nginx/default.conf` 裡的 `resolver 127.0.0.11` + 變數寫法。
可以試著改成直接寫 `proxy_pass http://api:8000;`，再做一次實驗，看看會不會 502。

## 第 3 步常見問題

| 症狀 | 原因與解法 |
|---|---|
| `amr_api` 一直 restarting | `docker compose logs api` 看錯誤；最常見是資料庫帳密不對 |
| 改了 `.env` 的資料庫密碼後 api 連不上 | 密碼只在資料庫**第一次建立**時設定。開發階段直接 `docker compose down -v` 重建 |
| 改了 `init.sql` 沒效果 | 同上，只有空的 volume 才會執行 |
| 歷史頁「API ↔ rosbridge」紅燈 | api 連不到 9090，和第 2 步的防火牆問題相同；`docker compose logs api` 會看到重試訊息 |
| 樓層有變，但沒有新紀錄 | 確認 `/current_floor` 有在發布；api 只在樓層「改變」時才記錄，數值相同不會重複記 |
| `/docs` 打得開但 Try it out 失敗 | 看瀏覽器 F12 的 Network 分頁，通常是 422（欄位格式不對） |

## 第 3 步練到的 Docker 觀念

- **自己寫的 image**：`python:3.12-slim`、layer cache 順序、非 root、`HEALTHCHECK`
- **多網路**：一個容器同時接兩個網路；`internal: true` 讓資料庫完全不對外
- **Docker 內建 DNS**：同一網路內用 service 名稱互連（`postgres`、`api`），以及 nginx 快取 IP 的陷阱
- **啟動順序**：`depends_on` + `condition: service_healthy`，和「容器開了」≠「服務準備好了」
- **資料持久化**：named volume、`docker-entrypoint-initdb.d` 只在第一次執行
- **設定與程式分離**：帳密放 `.env`，程式只讀環境變數

## 下一步（第 4 步，選做）

YOLO 電梯按鈕辨識獨立成一個容器（需要 `nvidia-container-toolkit` 才能用 GPU），
辨識結果透過 rosbridge 發布，或直接 `POST /api/events` 記錄「按鈕按下成功 / 失敗」。
