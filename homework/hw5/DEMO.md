# hw5 課堂展示流程

用最終版 `step3-api-db` 展示，約 5 分鐘。**不需要 Gazebo，主機也不用裝 ROS**，全部在 Docker 裡完成。

## 課前準備（一定要先做）

第一次 build 要 5–10 分鐘、會下載好幾 GB，**不要在課堂上才 build**。

```bash
cd _se
git pull
cd homework/hw5/step3-api-db
cp .env.example .env              # 填入 id -u / id -g 的值
docker compose up -d --build      # 先 build 好
docker compose down               # 確認能跑就先關掉
```

> ⚠️ 請用 **Ubuntu（Linux）** 展示。專案用了 `network_mode: host`，Mac / Windows 的 Docker Desktop 上 ROS 部分可能連不通。
>
> 建議課前完整演練一次下面的流程。

## 展示步驟

需要 **3 個終端機 + 1 個瀏覽器**。

### 1. 啟動全部服務（終端機 A）

```bash
cd homework/hw5/step3-api-db
docker compose up -d
docker compose ps
```

> 💬 「5 個容器各自負責：ROS 開發環境、rosbridge、網頁、API、資料庫。」

`amr_postgres`、`amr_api`、`amr_nginx` 要顯示 `(healthy)`。

### 2. 開監控網頁

瀏覽器開 <http://localhost:8080>，右上角應顯示「已連線 rosbridge」。

### 3. 跑自己寫的 ROS 節點（終端機 B）

```bash
docker compose exec ros_dev bash
cd /ws && colcon build --symlink-install && source install/setup.bash
ros2 run floor_status floor_publisher
```

> 👉 網頁上樓層變成 **1F**。

### 4. 改樓層，網頁即時更新（終端機 C）

```bash
docker compose exec ros_dev bash
ros2 param set /floor_publisher floor 2
ros2 param set /floor_publisher floor 3
```

> 👉 網頁上的樓層即時跳成 2F、3F。

### 5. 模擬機器人位置（終端機 C）

沒有開 Gazebo，所以直接發布一個假的里程計訊息：

```bash
ros2 topic pub -r 5 /odom nav_msgs/msg/Odometry "{pose: {pose: {position: {x: 1.5, y: 2.0}}}}"
```

> 👉 網頁上出現機器人座標。按 `Ctrl+C` 停止。

### 6. 看歷史紀錄

開 <http://localhost:8080/history.html>

> 👉 「樓層變化」列出 `–F → 1F`、`1F → 2F`、`2F → 3F`，都是 API 自動寫進 PostgreSQL 的。

### 7. 展示 API

開 <http://localhost:8080/docs>（FastAPI 自動產生的 API 文件），選 `POST /api/events` → **Try it out**，填入：

```json
{"kind": "warning", "message": "2F 走廊有障礙物"}
```

按 **Execute**，回到 history.html 重新整理，就會看到這筆巡檢紀錄。

### 8. 加分：容器重建後資料還在（終端機 A）

```bash
docker compose down        # 刪掉所有容器
docker compose up -d       # 重新建立
```

> 👉 重新整理 history.html，紀錄都還在，因為資料存在 `pgdata` volume，不在容器裡。
>
> ⚠️ 展示時**不要**加 `-v`，`docker compose down -v` 會連資料一起刪掉。

## 可以講的重點

| 問題 | 回答 |
|---|---|
| 為什麼 ROS 容器用 host 網路？ | ROS 2 的 DDS 靠 multicast 找節點，bridge 網路會擋掉 |
| 為什麼對外只開 8080？ | 所有請求都經過 Nginx；PostgreSQL 放在 internal 網路，外面連不到，比較安全 |
| 為什麼 API 容器不用裝 ROS？ | 它透過 rosbridge 的 WebSocket 拿資料，用純 Python image 就夠，比 ROS image 小很多 |
| 為什麼要 `fastdds_udp.xml`？ | 容器和主機的 `/dev/shm` 不同，DDS 走 shared memory 會「看得到 topic 但收不到資料」，強制走 UDP 解決 |

## 展示時出問題

| 症狀 | 處理 |
|---|---|
| 網頁顯示沒連上 rosbridge | `docker compose logs rosbridge` 看有沒有 `started on port 9090` |
| `ros2 run` 找不到 `floor_status` | 終端機 B 忘了 `source install/setup.bash` |
| 網頁樓層不會變 | 確認終端機 B 的 `floor_publisher` 還在跑 |
| port 8080 被佔用 | `sudo lsof -i :8080` 找出佔用的程式並關掉 |

## 展示完關掉

```bash
docker compose down
```
