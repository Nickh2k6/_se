"""
把自己模型的「明日 AQI 預測」上傳到看板。可以直接貼進 Google Colab 執行。

用法：
    SITE  = "https://kinmen-aqi.<你的帳號>.workers.dev"
    TOKEN = "<部署時設定的 API_TOKEN>"
    upload(SITE, TOKEN, [{"date": "2026-11-07", "aqi": 82.5}], model="隨機森林")

在 Colab 建議把 TOKEN 放在左側「密鑰」（🔑）裡，用
    from google.colab import userdata; TOKEN = userdata.get("AQI_API_TOKEN")
讀出來，不要直接寫在 notebook 裡，免得分享時外流。
"""
import json
import urllib.request


def upload(site, token, predictions, model="我的模型"):
    """predictions: [{"date": "YYYY-MM-DD", "aqi": 數字}, ...]，date 是被預測的那一天"""
    body = [{"date": p["date"], "aqi": float(p["aqi"]), "model": model} for p in predictions]
    req = urllib.request.Request(
        site.rstrip("/") + "/api/predictions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"上傳失敗（HTTP {e.code}）：{e.read().decode('utf-8', 'replace')}") from None


def upload_dataframe(site, token, df, date_col="date", aqi_col="pred", model="我的模型"):
    """直接上傳 pandas DataFrame，例如 df = pd.DataFrame({"date": 日期, "pred": model.predict(X)})"""
    rows = [{"date": str(d)[:10], "aqi": a} for d, a in zip(df[date_col], df[aqi_col])]
    results = []
    for i in range(0, len(rows), 400):  # API 一次最多 400 筆
        results.append(upload(site, token, rows[i:i + 400], model=model))
    return results


if __name__ == "__main__":
    import os
    import sys

    site, token = os.environ.get("AQI_SITE"), os.environ.get("AQI_API_TOKEN")
    if not site or not token or len(sys.argv) != 3:
        print("用法：AQI_SITE=https://... AQI_API_TOKEN=... python3 upload_prediction.py 2026-11-07 82.5")
        sys.exit(1)
    print(upload(site, token, [{"date": sys.argv[1], "aqi": sys.argv[2]}]))
