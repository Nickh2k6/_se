"""
每天下午由 GitHub Actions 執行：用 16 時版模型預測「明天」的金門官方日 AQI，上傳到看板。

特徵的算法逐行照抄期中報告 notebook（金門明日 AQI 預測）的 parse_hourly、hourly_feats、build_features，
只是把「整段歷史」換成「最近幾天」。`--check` 會用 notebook 匯出的特徵（features_reference.csv）
逐欄比對，確認兩邊算出來的數字一樣。

環境變數：
  MOENV_API_KEY   環境部 API 金鑰
  AQI_SITE        看板網址，例如 https://kinmen-aqi.nickh2k6.workers.dev
  AQI_API_TOKEN   看板的 API_TOKEN

用法：
  python predict_daily.py            # 預測明天並上傳
  python predict_daily.py --dry-run  # 只預測、不上傳
  python predict_daily.py --check    # 比對最近幾天的特徵與 notebook 是否一致
"""
import argparse
import datetime as dt
import json
import os
import ssl
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / "model_meta.json").read_text(encoding="utf-8"))
CONFIG = META["config"]          # 與 notebook 相同的設定（測站、截止時間、最少有效小時數）
CUTOFF = META["cutoff"]          # 16：只用當天 16:00 以前的觀測
FEATURES = META["features"]      # 模型特徵，順序與訓練時相同
TZ = ZoneInfo("Asia/Taipei")


# ---------- 下載 ----------

class GovSSLAdapter(requests.adapters.HTTPAdapter):
    """環境部網站憑證缺少 Subject Key Identifier，Python 3.13 的嚴格檢查會擋下；只關閉這一項（與 notebook 相同）"""
    def init_poolmanager(self, *a, **k):
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        k["ssl_context"] = ctx
        return super().init_poolmanager(*a, **k)


def fetch(dataset, flt, sort):
    """抓符合 flt 的全部資料。環境部 API 預設不保證排序、分頁會重複也會漏，所以指定 sort 並翻到最後一頁。"""
    s = requests.Session()
    s.mount("https://", GovSSLAdapter())
    rows, off = [], 0
    while True:
        p = {"api_key": os.environ["MOENV_API_KEY"].strip(), "format": "JSON", "limit": 1000, "offset": off,
             "filters": flt, "sort": sort}
        for attempt in range(4):
            try:
                r = s.get(f"https://data.moenv.gov.tw/api/v2/{dataset}", params=p, timeout=120)
                r.raise_for_status()
                b = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                print(f"  {dataset} 第 {attempt + 1} 次失敗（{type(e).__name__}）", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"{dataset} 連續失敗 4 次")
        b = b["records"] if isinstance(b, dict) else b
        rows += b
        if len(b) < 1000:
            return pd.DataFrame(rows, dtype=str)
        off += len(b)


# ---------- 特徵（照抄 notebook）----------

def parse_hourly(df):
    x = df.copy()
    x["time"] = pd.to_datetime(x["datacreationdate"], format="mixed")
    x = x.drop_duplicates("time").set_index("time").sort_index()
    cols = {"aqi": "aqi", "pm2.5": "pm25", "no2": "no2", "windspeed": "ws", "winddirec": "wd"}
    x = x[list(cols)].rename(columns=cols).apply(pd.to_numeric, errors="coerce")
    rad = np.deg2rad(x["wd"])
    x["nwind"] = x["ws"] * np.cos(rad)
    x["ewind"] = x["ws"] * np.sin(rad)
    return x


def parse_daily(df):
    d = df.copy()
    d["date"] = pd.to_datetime(d["monitordate"], format="mixed")
    d = d.drop_duplicates("date").set_index("date").sort_index()
    dcols = {"aqi": "aqi", "o38subindex": "o38", "pm25subindex": "pm25", "pm10subindex": "pm10", "no2subindex": "no2"}
    return d[list(dcols)].rename(columns=dcols).apply(pd.to_numeric, errors="coerce")


def hourly_feats(x, cutoff, p, full=True):
    hh = x[x.index.hour < cutoff].copy(); hh["day"] = hh.index.normalize(); g = hh.groupby("day")
    l6 = hh[hh.index.hour >= cutoff - 6].groupby("day")
    p6 = hh[(hh.index.hour >= cutoff - 12) & (hh.index.hour < cutoff - 6)].groupby("day")
    F = {f"{p}_aqi_last": g["aqi"].last(), f"{p}_aqi_max": g["aqi"].max(), f"{p}_aqi_mean": g["aqi"].mean(),
         f"{p}_aqi_trend6": l6["aqi"].mean() - p6["aqi"].mean(),
         f"{p}_pm25_last": g["pm25"].last(), f"{p}_pm25_trend6": l6["pm25"].mean() - p6["pm25"].mean(),
         f"{p}_nwind_mean": g["nwind"].mean()}
    if full:
        F.update({f"{p}_pm25_mean": g["pm25"].mean(), f"{p}_no2_mean": g["no2"].mean(), f"{p}_ws_mean": g["ws"].mean(),
                  f"{p}_ewind_mean": g["ewind"].mean(), f"{p}_nwind_last6": l6["nwind"].mean(), f"{p}_ewind_last6": l6["ewind"].mean(),
                  "n_valid_hours": g["aqi"].count()})
    return pd.DataFrame(F)


BASE_ORDER = ["h_aqi_last", "h_aqi_max", "h_aqi_mean", "h_aqi_trend6", "h_pm25_mean", "h_pm25_last", "h_pm25_trend6", "h_no2_mean",
              "h_ws_mean", "h_nwind_mean", "h_ewind_mean", "h_nwind_last6", "h_ewind_last6"]


def build_features(h, up, d, days):
    """days：要算特徵的日期（DatetimeIndex）。d 會延伸到這些日期，讓「今天」也有一列（今天的官方日 AQI 還沒公布）。"""
    idx = pd.date_range(min(d.index.min(), days.min()), max(d.index.max(), days.max()), freq="D")
    d = d.reindex(idx)
    X = hourly_feats(h, CUTOFF, "h").reindex(d.index)
    X = X[BASE_ORDER + ["n_valid_hours"]]
    X["d1_aqi"] = d["aqi"].shift(1); X["d1_o38"] = d["o38"].shift(1); X["d1_pm25"] = d["pm25"].shift(1)
    X["d1_pm10"] = d["pm10"].shift(1); X["d1_no2"] = d["no2"].shift(1); X["d2_aqi"] = d["aqi"].shift(2)
    X["d1_change"] = X["d1_aqi"] - X["d2_aqi"]
    X["d3_mean"] = d["aqi"].shift(1).rolling(3, min_periods=3).mean()
    m = X.index.month
    X["month_sin"] = np.sin(2 * np.pi * m / 12); X["month_cos"] = np.cos(2 * np.pi * m / 12)
    n_valid = X["n_valid_hours"].fillna(0)
    bad = n_valid < CONFIG["min_valid_hours"]
    X = X.drop(columns="n_valid_hours"); X.loc[bad, :] = np.nan
    U = pd.concat([hourly_feats(up[k], CUTOFF, k, full=False) for k in CONFIG["upstream"]], axis=1).reindex(d.index)
    for k in CONFIG["upstream"]:
        U[f"{k}_minus_km"] = U[f"{k}_aqi_last"] - X["h_aqi_last"]
    out = pd.concat([X, U], axis=1)[FEATURES]
    out["n_valid_hours"] = n_valid
    return out.loc[days]


def load_recent(since):
    """since 以後（含）的逐時觀測與官方日 AQI；since 是 pd.Timestamp（日期）"""
    site = CONFIG["site"]
    after = (since - pd.Timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")   # GR 是「大於」，往前一小時才會包含 since 00:00
    hourly = lambda name: parse_hourly(fetch("aqx_p_488", f"sitename,EQ,{name}|datacreationdate,GR,{after}", "datacreationdate desc"))
    h = hourly(site)
    up = {k: hourly(v) for k, v in CONFIG["upstream"].items()}
    day_before = (since - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    d = parse_daily(fetch("aqx_p_434", f"sitename,EQ,{site}|monitordate,GR,{day_before}", "monitordate desc"))
    return h, up, d


# ---------- 主程式 ----------

def check():
    """用最近的資料重算特徵，跟 notebook 匯出的 features_reference.csv 逐欄比對"""
    ref = pd.read_csv(HERE / "features_reference.csv", index_col=0, parse_dates=True)
    h, up, d = load_recent(ref.index.min() - pd.Timedelta(days=4))   # d3_mean 要往前 3 天的官方日 AQI
    mine = build_features(h, up, d, ref.index)
    diff = (mine[FEATURES] - ref[FEATURES]).abs()
    both_nan = mine[FEATURES].isna() & ref[FEATURES].isna()
    bad = (diff > 1e-6) & ~both_nan
    one_nan = mine[FEATURES].isna() ^ ref[FEATURES].isna()
    print(f"比對 {len(ref)} 天 × {len(FEATURES)} 個特徵（{ref.index.min().date()}～{ref.index.max().date()}）")
    if bad.values.any() or one_nan.values.any():
        print("不一致的欄位：")
        for c in FEATURES:
            if bad[c].any() or one_nan[c].any():
                print(f"  {c}：{int(bad[c].sum() + one_nan[c].sum())} 天")
        sys.exit(1)
    print("全部一致")


def predict(dry_run, date=None):
    if date:   # 測試用：假裝今天是 date（只預測、不上傳）
        today, dry_run = pd.Timestamp(date), True
    else:
        today = pd.Timestamp.now(TZ).tz_localize(None).normalize()
        now_hour = pd.Timestamp.now(TZ).hour
        if now_hour < CUTOFF:
            sys.exit(f"現在 {now_hour} 點，還沒到 {CUTOFF}:00，當天的 {CUTOFF} 時版特徵還不完整")

    h, up, d = load_recent(today - pd.Timedelta(days=4))   # d3_mean 要往前 3 天的官方日 AQI
    d = d[d.index < today]   # 假裝今天時，看不到今天以後才公布的官方日 AQI
    X = build_features(h, up, d, pd.DatetimeIndex([today]))
    row = X.iloc[[0]]
    print(f"今天 {today.date()}：金門 {CUTOFF}:00 前有效 {int(row['n_valid_hours'].iloc[0])} 小時；"
          f"最新官方日 AQI {d['aqi'].dropna().index.max().date()}")

    # 與 notebook 的資料篩選相同：今天觀測不足、或昨天的官方日 AQI 還沒公布，就不預測
    if pd.isna(row["h_aqi_mean"].iloc[0]):
        sys.exit(f"金門今天 {CUTOFF}:00 前的有效觀測少於 {CONFIG['min_valid_hours']} 小時，不預測")
    if pd.isna(row["d1_aqi"].iloc[0]):
        sys.exit("昨天的官方日 AQI 還沒公布，不預測（稍後重跑）")

    model = joblib.load(HERE / META["model_file"])
    pred = float(model.predict(row[FEATURES])[0])
    target = (today + pd.Timedelta(days=1)).date().isoformat()
    print("特徵：", json.dumps({k: (None if pd.isna(v) else round(float(v), 3)) for k, v in row[FEATURES].iloc[0].items()},
                              ensure_ascii=False))
    print(f"預測 {target} 的官方日 AQI：{pred:.1f}（{META['learner']}，{META['model_name']}）")

    if dry_run:
        return
    site, token = os.environ["AQI_SITE"].rstrip("/"), os.environ["AQI_API_TOKEN"]
    r = requests.post(f"{site}/api/predictions", timeout=30,
                      headers={"Authorization": f"Bearer {token}", "User-Agent": "kinmen-aqi-predictor"},
                      json={"date": target, "aqi": round(pred, 1), "model": META["model_name"]})
    if not r.ok:
        sys.exit(f"上傳失敗（HTTP {r.status_code}）：{r.text}")
    print("已上傳：", r.json())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只預測、不上傳")
    ap.add_argument("--check", action="store_true", help="比對特徵與 notebook 是否一致")
    ap.add_argument("--date", help="測試用：假裝今天是這一天（YYYY-MM-DD），只預測不上傳")
    a = ap.parse_args()
    check() if a.check else predict(a.dry_run, a.date)
