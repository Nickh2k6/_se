# ===== 15. 匯出 16 時版模型給看板使用 =====
# 把這整段貼到期中報告 notebook 的最後一個 cell（需要先跑完第 1～7 節）。
# 會產生 model/ 資料夾，裡面的檔案複製到 hw7/model/ 後 commit、push，GitHub Actions 就會用新模型。
#
# 產生的檔案：
#   model_16.joblib         「我的模型」正式版：同一種學習器，用到目前為止的全部資料重新訓練，給每天的預測用
#   model_16_fc.joblib      「模型＋預報」正式版：多一個特徵 forecast（今天 16:30 發布的明日官方預報）
#   model_meta.json         特徵順序、設定、學習器名稱、套件版本（兩個模型都記在裡面）
#   features_reference.csv  最近 30 天的特徵（含 forecast），predict_daily.py --check 用來確認兩邊算法一致
#   backtest_16.csv         「我的模型」測試期每一天的預測（模型只用 2024 年以前的資料訓練），上傳到看板當作回測
#   backtest_16_fc.csv      「模型＋預報」測試期每一天的預測，同上
#   requirements.txt        跟這次訓練相同的套件版本（模型檔換版本可能讀不出來）
import joblib, platform, scipy
from importlib.metadata import version

os.makedirs("model", exist_ok=True)
cut = 16
R, df = results[cut], datasets[cut]
main = R["main"]
HYBRID = "模型＋預報"                       # notebook 第 6 節裡的名稱，也是上傳到看板的模型名稱
FC_FEATURES = FEATURES + ["forecast"]       # 順序與第 6 節訓練「模型＋預報」時相同
hybrid = R["learner"][HYBRID]               # 第 6 節用交叉驗證挑出的學習器

# 1) 回測：測試期每一天的預測都是「訓練時沒看過」的日子，可以公平地跟官方預報比
test_dates = (R["test"].index + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
bt = pd.DataFrame({"date": test_dates, "pred": R["pred"]["主要模型"].to_numpy()})
bt.to_csv("model/backtest_16.csv", index=False)
# 「模型＋預報」的回測用同一批測試日（測試集本來就要求有官方預報），看板上的天數才會一樣
bt_fc = pd.DataFrame({"date": test_dates, "pred": R["pred"][HYBRID].to_numpy()})
assert bt_fc["pred"].notna().all(), "模型＋預報的回測有缺值"
bt_fc.to_csv("model/backtest_16_fc.csv", index=False)

# 2) 正式版：跟各自的回測同一種學習器，用 2017 年起的全部資料重新訓練（篩選條件與訓練集相同）
tgt = df.index + pd.Timedelta(days=1)
ok = df["h_aqi_mean"].notna() & df["d1_aqi"].notna()
full = df[(tgt >= CONFIG["train_start"]) & ok]
final = clone(MODELS[main]).fit(full[FEATURES], full["y"])
joblib.dump(final, "model/model_16.joblib", compress=3)

# 「模型＋預報」只用有官方預報的日子訓練（跟第 6 節的 trh 相同；預報從 2019 年 12 月才有）
full_fc = full[full["forecast"].notna()]
final_fc = clone(MODELS[hybrid]).fit(full_fc[FC_FEATURES], full_fc["y"])
joblib.dump(final_fc, "model/model_16_fc.joblib", compress=3)

# 第 6 節只留下學習器名稱，沒存交叉驗證 MAE，這裡用同樣的訓練集重算一次
trh = R["train"][R["train"]["forecast"].notna()]
cv_fc = cv_mae(MODELS[hybrid], trh, FC_FEATURES)

# 3) 特徵參考：最近 30 天（predict_daily.py --check 會用 API 重算這幾天，逐欄比對）
df[FC_FEATURES].tail(30).to_csv("model/features_reference.csv")

# 4) 說明檔與套件版本
def trained_range(x):
    return {"from": str((x.index.min() + pd.Timedelta(days=1)).date()),
            "to": str((x.index.max() + pd.Timedelta(days=1)).date()), "days": int(len(x))}

meta = {
    # 最上層是「我的模型」，跟舊版 model_meta.json 相同，舊的 predict_daily.py 也讀得懂
    "model_name": "我的模型",
    "learner": main,
    "cutoff": cut,
    "features": FEATURES,
    "config": {k: CONFIG[k] for k in ["site", "upstream", "min_valid_hours", "train_start", "train_end", "test_start"]},
    "trained_on": trained_range(full),
    "cv_mae": R["cv"][main],
    "test_mae": float(tables[cut].loc["主要模型", "MAE"]),
    "model_file": "model_16.joblib",
    # 「模型＋預報」：多一個特徵 forecast＝今天 forecast_issue 發布、預報明天的官方 AQI
    "hybrid": {
        "model_name": HYBRID,
        "learner": hybrid,
        "features": FC_FEATURES,
        "forecast_issue": CONFIG["forecast_issue"][cut],
        "trained_on": trained_range(full_fc),
        "cv_mae": cv_fc,
        "test_mae": float(tables[cut].loc[HYBRID, "MAE"]),
        "model_file": "model_16_fc.joblib",
    },
    "python": platform.python_version(),
}
json.dump(meta, open("model/model_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pkgs = ["numpy", "pandas", "scikit-learn", "scipy", "joblib", "requests"]
open("model/requirements.txt", "w").write("\n".join(f"{p}=={version(p)}" for p in pkgs) + "\n")

print(f"我的模型：{main}；正式版訓練 {meta['trained_on']}；回測 {len(bt)} 天（測試 MAE {meta['test_mae']:.1f}）")
H = meta["hybrid"]
print(f"{HYBRID}：{hybrid}；正式版訓練 {H['trained_on']}；回測 {len(bt_fc)} 天"
      f"（交叉驗證 MAE {H['cv_mae']:.1f}，測試 MAE {H['test_mae']:.1f}）")
print(open("model/requirements.txt").read())
