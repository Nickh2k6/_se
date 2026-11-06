-- 官方日 AQI（環境部 aqx_p_434），隔天早上公布；預測模型的目標就是這個數字
CREATE TABLE IF NOT EXISTS daily_official (
  site  TEXT NOT NULL,
  date  TEXT NOT NULL,
  aqi   INTEGER,
  o38   INTEGER,   -- 臭氧 8 小時副指標
  pm25  INTEGER,   -- PM2.5 副指標
  pm10  INTEGER,   -- PM10 副指標
  no2   INTEGER,   -- 二氧化氮副指標
  PRIMARY KEY (site, date)
);
