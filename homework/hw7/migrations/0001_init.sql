-- 每小時即時 AQI（環境部 aqx_p_432），時間為台灣時間 'YYYY-MM-DD HH:MM'
CREATE TABLE IF NOT EXISTS observations (
  site        TEXT NOT NULL,
  time        TEXT NOT NULL,
  aqi         INTEGER,
  pm25        REAL,
  pm10        REAL,
  o3          REAL,
  o3_8hr      REAL,
  no2         REAL,
  co          REAL,
  so2         REAL,
  wind_speed  REAL,
  wind_dir    REAL,
  pollutant   TEXT,
  status      TEXT,
  PRIMARY KEY (site, time)
);

-- 空品預報（環境部 aqf_p_01）；同一天會發布好幾版，全部保留才能公平比較
CREATE TABLE IF NOT EXISTS forecasts (
  area            TEXT NOT NULL,
  forecast_date   TEXT NOT NULL,
  publish_time    TEXT NOT NULL,
  aqi             INTEGER,
  major_pollutant TEXT,
  content         TEXT,
  PRIMARY KEY (area, forecast_date, publish_time)
);

-- 自己的模型（例如 Colab 訓練的）上傳的明日 AQI 預測
CREATE TABLE IF NOT EXISTS predictions (
  forecast_date TEXT NOT NULL,
  model         TEXT NOT NULL,
  aqi           REAL NOT NULL,
  created_at    TEXT NOT NULL,
  PRIMARY KEY (forecast_date, model)
);

-- 排程執行紀錄，頁面底部顯示最近一次抓取是否成功
CREATE TABLE IF NOT EXISTS fetch_log (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  time         TEXT NOT NULL,
  ok           INTEGER NOT NULL,
  observations INTEGER NOT NULL DEFAULT 0,
  forecasts    INTEGER NOT NULL DEFAULT 0,
  message      TEXT
);
