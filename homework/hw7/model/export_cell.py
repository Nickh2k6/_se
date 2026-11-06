# ===== 15. 匯出 16 時版模型給看板使用 =====
# 把這整段貼到期中報告 notebook 的最後一個 cell（需要先跑完第 1～7 節）。
# 會產生 model/ 資料夾，裡面的檔案複製到 hw7/model/ 後 commit、push，GitHub Actions 就會用新模型。
#
# 產生的檔案：
#   model_16.joblib         正式版模型：同一種學習器，用到目前為止的全部資料重新訓練，給每天的預測用
#   model_meta.json         特徵順序、設定、學習器名稱、套件版本
#   features_reference.csv  最近 30 天的特徵，predict_daily.py --check 用來確認兩邊算法一致
#   backtest_16.csv         測試期每一天的預測（模型只用 2024 年以前的資料訓練），上傳到看板當作回測
#   requirements.txt        跟這次訓練相同的套件版本（模型檔換版本可能讀不出來）
import joblib, platform, scipy
from importlib.metadata import version

os.makedirs("model", exist_ok=True)
cut = 16
R, df = results[cut], datasets[cut]
main = R["main"]

# 1) 回測：測試期每一天的預測都是「訓練時沒看過」的日子，可以公平地跟官方預報比
bt = pd.DataFrame({"date": (R["test"].index + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                   "pred": R["pred"]["主要模型"].to_numpy()})
bt.to_csv("model/backtest_16.csv", index=False)

# 2) 正式版：跟主要模型同一種學習器，用 2017 年起的全部資料重新訓練（篩選條件與訓練集相同）
tgt = df.index + pd.Timedelta(days=1)
ok = df["h_aqi_mean"].notna() & df["d1_aqi"].notna()
full = df[(tgt >= CONFIG["train_start"]) & ok]
final = clone(MODELS[main]).fit(full[FEATURES], full["y"])
joblib.dump(final, "model/model_16.joblib", compress=3)

# 3) 特徵參考：最近 30 天（predict_daily.py --check 會用 API 重算這幾天，逐欄比對）
df[FEATURES].tail(30).to_csv("model/features_reference.csv")

# 4) 說明檔與套件版本
meta = {
    "model_name": "我的模型",
    "learner": main,
    "cutoff": cut,
    "features": FEATURES,
    "config": {k: CONFIG[k] for k in ["site", "upstream", "min_valid_hours", "train_start", "train_end", "test_start"]},
    "trained_on": {"from": str((full.index.min() + pd.Timedelta(days=1)).date()),
                   "to": str((full.index.max() + pd.Timedelta(days=1)).date()), "days": int(len(full))},
    "cv_mae": R["cv"][main],
    "test_mae": float(tables[cut].loc["主要模型", "MAE"]),
    "model_file": "model_16.joblib",
    "python": platform.python_version(),
}
json.dump(meta, open("model/model_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pkgs = ["numpy", "pandas", "scikit-learn", "scipy", "joblib", "requests"]
open("model/requirements.txt", "w").write("\n".join(f"{p}=={version(p)}" for p in pkgs) + "\n")

print(f"主要模型：{main}；正式版訓練 {meta['trained_on']}；回測 {len(bt)} 天（測試 MAE {meta['test_mae']:.1f}）")
print(open("model/requirements.txt").read())
