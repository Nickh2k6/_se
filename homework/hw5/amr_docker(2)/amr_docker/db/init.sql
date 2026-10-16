-- PostgreSQL 初始化腳本
--
-- 注意：放在 /docker-entrypoint-initdb.d/ 的腳本「只有在資料庫第一次建立時」才會執行。
-- 也就是 pgdata volume 是空的時候。之後改這個檔案不會有任何效果，
-- 除非 docker compose down -v 把 volume 刪掉（資料會全部清空）。

-- 樓層變化紀錄：API 從 rosbridge 收到 /current_floor 改變時自動寫入
CREATE TABLE IF NOT EXISTS floor_changes (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    from_floor  INTEGER,                 -- 第一筆紀錄沒有「從哪層來」，所以可以是 NULL
    to_floor    INTEGER NOT NULL,
    x           DOUBLE PRECISION,        -- 切換當下機器人在舊地圖上的位置
    y           DOUBLE PRECISION
);

-- 巡檢事件：網頁表單、curl，或之後的 ROS 節點透過 POST /api/events 寫入
CREATE TABLE IF NOT EXISTS patrol_events (
    id       BIGSERIAL PRIMARY KEY,
    ts       TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind     TEXT NOT NULL CHECK (kind IN ('info', 'warning', 'error')),
    message  TEXT NOT NULL,
    floor    INTEGER,
    x        DOUBLE PRECISION,
    y        DOUBLE PRECISION
);

-- 歷史頁都是「最新的在前面」，依時間倒序建索引
CREATE INDEX IF NOT EXISTS idx_floor_changes_ts ON floor_changes (ts DESC);
CREATE INDEX IF NOT EXISTS idx_patrol_events_ts ON patrol_events (ts DESC);
