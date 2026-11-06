# 金門空品看板

金門的空氣品質常常跟台灣本島不一樣：秋冬吹東北季風時，對岸的污染物和沙塵一下子就飄過來，AQI 可能一天之內從綠燈跳到橘燈。環境部每天會發布空品預報，但沒有地方告訴你「這個預報到底準不準」。

這個網站架在 **Cloudflare Workers** 上，每小時自動記錄金門測站的 AQI 和環境部預報，除了顯示現在和明天的空氣品質，還會長期統計**預報準確度**。我在資料探勘課期中報告訓練的「金門明日 AQI 預測模型」也放在上面：**GitHub Actions 每天下午自動預測明天的 AQI**，和環境部預報放在同一張表比較。

網址：<https://kinmen-aqi.nickh2k6.workers.dev>

## 價值

- **使用價值**：金門居民、學生出門前一眼看到現在的 AQI、過去三天的變化和明天的預報；有氣喘或過敏的人可以提早準備。
- **學術價值**：環境部的資料平台只給「現在」的即時值，這個網站把每一版預報、每一天的官方日 AQI 都存下來，才能事後算出預報誤差，並公平地比較自己的模型有沒有比官方預報好。
- **商業／延伸價值**：同一套架構換個測站名稱就能做馬祖、澎湖或任何縣市版本；也可以加上 LINE 通知，在預報轉橘燈時提醒訂閱者。

## 功能

| 功能 | 說明 |
|------|------|
| 現在的空氣品質 | 金門測站最新 AQI、等級、主要污染物、PM2.5、PM10、臭氧、二氧化氮、風向風速、今天到目前最高值 |
| 72 小時色帶 | 過去三天每小時一條，高度是 AQI、顏色是官方分級色；缺資料的小時畫成虛線，不會用前後值補 |
| 明天 | 環境部對金門空品區明天的預報、我的模型的預測、今天到目前的最高值並排；也顯示今天和後天的預報 |
| 預報準不準 | 每天的實測值、環境部預報、「明天＝今天」基準線、我的模型畫在同一張圖；實測可切換官方日 AQI／每小時最大／每小時平均，期間可選 30 天、90 天、1 年、全部 |
| 準確度統計 | 每個預測來源的 MAE、RMSE、等級猜對率，以及**大幅變動日**（比前一天變動 ≥ 30）的誤差和漲跌方向猜對率 |
| 每日自動預測 | GitHub Actions 每天 16:40 用 16 時版模型預測明天，上傳到看板 |
| 上傳模型預測 | `POST /api/predictions`，用 `API_TOKEN` 驗證；附 Colab 可直接用的上傳程式，可以同時比較好幾個模型 |
| 補抓歷史資料 | `POST /api/backfill?days=28`，一次補回過去幾天的資料；更長的歷史附 SQL 檔可直接匯入 |

### 怎麼比較才公平

設計跟期中報告 notebook 相同，網站和 notebook 算出來的數字完全一致（見「結果」）。

- **實測值是官方日 AQI**：環境部每天隔天早上公布前一天的官方日 AQI（`aqx_p_434`，由臭氧 8 小時、PM2.5 等日值換算），這是模型的訓練目標，也是預設的比較基準。每小時 AQI 的日最大值、日平均也可以切換來看。
- **大家都只用前一天下午就知道的資訊**：我的模型是 16 時版，只用當天 16:00 以前的觀測預測明天；環境部預報也只採用前一天 **16:30（含）以前**發布的最後一版（通常就是 16:30 那一版）。晚上 22:00 那一版看到更多資料，拿來比不公平。這個時刻可以在 `wrangler.toml` 的 `FORECAST_ISSUE` 改。
- **比較的日子完全相同**：只比較實測和每個來源都有值的日子，所以表格裡每一列的天數一樣。
- **基準線**：最簡單的猜法是「明天跟今天一樣」。一個預測如果平均誤差打不贏它，就沒有實用價值。基準線的「漲跌方向猜對」一定是 0%，因為它永遠預測不變，正好凸顯有沒有抓到變化。
- **回測和正式預測分開**：2025-01-01～2026-11-05 的模型預測是測試期回測，模型只用 2024 年以前的資料訓練，沒看過這些日子。之後每天的預測則來自用全部資料重新訓練的正式版，預測的是還沒發生的明天。

## 資料來源

| 資料 | API |
|------|-----|
| 即時 AQI 與各項污染物 | 環境部環境資料開放平臺 `aqx_p_432`「空氣品質指標(AQI)」，篩選測站「金門」 |
| 官方日 AQI | 環境部環境資料開放平臺 `aqx_p_434`「日空氣品質指標(AQI)」，隔天早上公布 |
| 空品預報（今天起 3 天） | 環境部環境資料開放平臺 `aqf_p_01`「空氣品質預報資料」，篩選空品區「金門」 |
| 補抓過去的 AQI、模型特徵 | 環境部環境資料開放平臺 `aqx_p_488`「空氣品質指標(AQI)(歷史資料)」，每小時一筆，包含今天；模型另外用到馬祖、馬公站 |

都是 `https://data.moenv.gov.tw/api/v2/<資料集>?format=JSON&api_key=...&filters=sitename,EQ,金門`，需要免費註冊取得 API 金鑰。一次最多 1000 筆，用 `offset` 翻頁。環境部約在每個整點後 10～15 分鐘更新即時資料，所以排程設在每小時第 20 分。

踩過的坑：

- **API 預設不排序**：不指定 `sort` 時，分頁之間的資料會重複也會漏。程式一律加上 `sort=datacreationdate desc` 這類排序，補抓時再用 `filters=sitename,EQ,金門|datacreationdate,GR,2025-01-01 00:00` 限定日期範圍，翻到最後一頁為止，存檔時依日期去重。用這個方法補抓的筆數，和期中報告 notebook 把整個資料集翻完再去重的結果完全相同。
- **官方日 AQI 有重複列**：同一天會出現好幾筆相同的資料，要依日期去重。
- **舊的預報補得回來**：`aqf_p_01` 雖然叫「預報資料」，其實保留了過去每一版預報（每天 10:30、16:30、22:00 各一版），往回可以翻到 2019 年 12 月。
- **欄位名稱不一致**：歷史資料集的時間是 `datacreationdate`、風速是 `windspeed`，即時資料是 `publishtime`、`wind_speed`，解析程式兩種都能讀。

## 架構

```
                 每小時第 20 分（Cron Trigger）
                            │
環境部開放資料 ──────► Worker: collect() ──► D1 資料庫
 aqx_p_432 即時 AQI                          ├ observations    每小時觀測
 aqx_p_434 官方日 AQI                        ├ daily_official  官方日 AQI
 aqf_p_01  空品預報                          ├ forecasts       每一版預報都保留
                                             ├ predictions     模型的預測
GitHub Actions（每天 16:40）                 └ fetch_log       抓取紀錄
  predict_daily.py：抓今天的觀測 → 算特徵             │
  → 16 時版模型 → POST /api/predictions ─────────────►│
                                                       │
瀏覽器 ◄── public/index.html（靜態檔案）               │
       ◄── GET /api/latest、/hourly、/daily ◄──────────┘
```

- **Cloudflare Workers**：同一支程式處理排程（`scheduled`）和 HTTP 請求（`fetch`），不用自己架伺服器。
- **D1**：Cloudflare 的 SQLite 資料庫，存歷史資料。免費額度遠超過這個專案的用量：每小時只寫入幾筆。
- **Static Assets**：`public/` 裡的檔案直接當網站，找不到檔案的路徑（`/api/*`）才交給 Worker。
- **GitHub Actions**：Worker 跑不了 Python 和 scikit-learn，所以模型放在 GitHub 上用 Actions 每天執行，算完再上傳到看板。
- **容錯**：三個資料集分開抓，一個失敗不影響另一個；失敗原因記在 `fetch_log`，頁面底部會顯示「最近一次抓取失敗：…」。環境部金鑰錯誤時回傳的是中文純文字而不是 JSON，程式會辨識出來並記錄。
- **安全**：環境部金鑰和 `API_TOKEN` 用 `wrangler secret`、GitHub Secrets 保管，不在程式碼裡也不會送到瀏覽器。寫入用的 API 沒設定 `API_TOKEN` 時一律拒絕；比對 token 用固定時間比較。所有讀取 API 都是唯讀的公開資料。

## 執行方式

需要 Node.js 22 以上（wrangler 4 的要求）和一個免費的 [Cloudflare 帳號](https://dash.cloudflare.com/sign-up)。用 nvm 的話，在專案資料夾執行 `nvm install && nvm use` 會依 `.nvmrc` 切到正確版本。

### 1. 申請環境部 API 金鑰

到 <https://data.moenv.gov.tw> 註冊會員，在會員專區取得 API 金鑰（免費）。

### 2. 本機執行

```bash
npm install
cp .dev.vars.example .dev.vars     # 填入 MOENV_API_KEY 和自己訂的 API_TOKEN
npm run db:local                   # 在本機建立資料表
npx wrangler d1 execute kinmen-aqi --local --file=data/history.sql   # 匯入 2025 年起的歷史資料和模型回測
npm run dev                        # 開啟 http://localhost:8787
```

本機不會自動跑排程，要手動觸發一次抓資料：

```bash
curl "http://localhost:8787/__scheduled?cron=20+*+*+*+*"
```

`data/history.sql` 可以重複匯入，已經有的資料會被覆蓋，不會重複。

### 3. 部署到 Cloudflare

```bash
npx wrangler login                          # 開瀏覽器登入 Cloudflare
npx wrangler d1 create kinmen-aqi           # 把印出來的 database_id 貼到 wrangler.toml
npm run db:remote                           # 在雲端資料庫建立資料表（有新的 migration 時也要再跑一次）
npm run deploy                              # 完成後會印出網址 https://kinmen-aqi.<子網域>.workers.dev
npx wrangler secret put MOENV_API_KEY       # 貼上環境部金鑰
npx wrangler secret put API_TOKEN           # 貼上自己訂的長亂碼
npx wrangler d1 execute kinmen-aqi --remote --file=data/history.sql   # 匯入歷史資料和模型回測
```

部署後排程每小時會自動執行。`API_TOKEN` 可以用 `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` 產生。

不想匯入 SQL 檔，也可以讓 Worker 自己去環境部補抓最近幾天（最多 90 天，免費方案每次請求的 CPU 時間有限，更長的歷史請用 SQL 檔）：

```bash
curl -X POST -H "Authorization: Bearer <API_TOKEN>" "https://kinmen-aqi.<子網域>.workers.dev/api/backfill?days=28"
```

### 4. 每天自動預測（GitHub Actions）

模型和預測程式在 `model/`。設定一次之後，GitHub 每天台灣時間 16:40 會自動：抓金門、馬祖、馬公今天 16:00 以前的觀測和金門前幾天的官方日 AQI → 用跟 notebook 一模一樣的方法算特徵 → 預測明天的官方日 AQI → 上傳到看板。18:40 會再跑一次，以防 GitHub 排程延遲或官方日 AQI 晚公布（同一天重跑會覆蓋，不會重複）。

1. 把設定檔複製到 repo 根目錄的 `.github/workflows/`（GitHub 只會執行那個資料夾裡的 workflow）：
   ```bash
   mkdir -p ~/_se/.github/workflows
   cp ~/_se/homework/hw7/model/kinmen-aqi-predict.yml ~/_se/.github/workflows/
   ```
2. 到 GitHub 的 repo → Settings → Secrets and variables → Actions → New repository secret，新增兩個：
   - `MOENV_API_KEY`：環境部金鑰
   - `AQI_API_TOKEN`：跟 Cloudflare 的 `API_TOKEN` 同一串
3. commit、push 到 `main`。
4. 到 repo 的 Actions 頁面 → 「金門空品看板每日預測」→ Run workflow。「測試日期」填過去某一天（例如昨天），會用那天的資料完整跑一次預測、但不上傳，可以確認金鑰、套件和模型都正常；留空就是正式預測明天（16:00 以前執行會說明時間還沒到，正常結束）。

注意：GitHub 對超過 60 天沒有任何 commit 的 repo 會自動停用排程，停用後到 Actions 頁面按一下就能重新啟用。

本機也可以執行：

```bash
cd model
pip install -r requirements.txt
export MOENV_API_KEY=... AQI_SITE=https://kinmen-aqi.<子網域>.workers.dev AQI_API_TOKEN=...
python predict_daily.py --check              # 用 API 重算最近 30 天的特徵，跟 notebook 匯出的逐欄比對
python predict_daily.py --date 2026-11-04    # 假裝今天是某一天，只預測不上傳
python predict_daily.py --dry-run            # 預測明天，不上傳
python predict_daily.py                      # 預測明天並上傳
```

### 5. 更新模型

模型在期中報告 notebook 裡訓練。把 `model/export_cell.py` 整段貼到 notebook 最後一個 cell 執行（要先跑完第 1～7 節），會產生 `model/` 資料夾；把裡面的檔案複製到 `hw7/model/`，覆蓋舊的，然後：

1. 跑 `python predict_daily.py --check`，確認特徵一致。
2. 用 `tools/upload_prediction.py` 把新的 `backtest_16.csv` 上傳到看板（見下一節）。
3. commit、push，GitHub Actions 就會用新模型。

`requirements.txt` 由匯出 cell 依當時的套件版本產生，GitHub Actions 會安裝同樣的版本，模型檔才讀得出來。

### 6. 手動上傳其他模型的預測

```python
# 把 tools/upload_prediction.py 的內容貼進一個 cell，或上傳後 import
from google.colab import userdata
SITE  = "https://kinmen-aqi.<子網域>.workers.dev"
TOKEN = userdata.get("AQI_API_TOKEN")      # 存在 Colab 左側的「密鑰」

upload(SITE, TOKEN, [{"date": "2026-11-07", "aqi": 82.5}], model="隨機森林")

# 或一次上傳整個 DataFrame，例如回測結果
upload_dataframe(SITE, TOKEN, df, date_col="date", aqi_col="pred", model="隨機森林")
```

`date` 是**被預測的那一天**。同一個模型名稱、同一天重複上傳會覆蓋。不同 `model` 名稱會分開顯示。

### 7. 測試

```bash
npm test
```

測試涵蓋資料解析（缺值、區間、兩種時間格式、大小寫欄位、三個資料集的實際格式）、台灣時間換算、每日彙整（預報只採前一天 16:30 以前的版本）、誤差與大幅變動日計算、只比較共同日子、AQI 等級的四捨五入、上傳資料檢查。

## API

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/latest` | 最新觀測、今天統計、今天起 3 天的最新預報、模型預測 |
| GET | `/api/hourly?hours=72` | 每小時觀測（最多 1440 小時） |
| GET | `/api/daily?days=30&basis=daily&big=30` | 每日彙整與各預測來源的誤差統計；`basis` 可為 `daily`（官方日 AQI）、`max`、`mean`，`big` 是大幅變動門檻，`days` 最多 1000 |
| GET | `/api/status` | 最近 10 次抓取紀錄、資料筆數 |
| POST | `/api/predictions` | 上傳模型預測，需要 `Authorization: Bearer <API_TOKEN>`；內容 `{"date","aqi","model"}` 或陣列，一次最多 400 筆 |
| POST | `/api/collect` | 立即抓一次資料，需要 `API_TOKEN` |
| POST | `/api/backfill?days=28` | 補抓過去 N 天（最多 `MAX_BACKFILL_DAYS`，預設 90）的每小時 AQI、官方日 AQI 和各版預報，需要 `API_TOKEN` |

讀取 API 開放跨網域（CORS），也可以直接在 Colab 用 `pandas.read_json` 讀回累積的資料做分析。

## 檔案

| 檔案 | 說明 |
|------|------|
| `src/index.js` | Worker：排程抓資料、補抓、API 路由、寫入 D1 |
| `src/lib.js` | 純函式：解析環境部資料、台灣時間、每日彙整、誤差統計（不碰網路和資料庫，方便測試） |
| `public/index.html` | 前端看板（圖表用 Chart.js） |
| `migrations/` | D1 資料表 |
| `wrangler.toml` | Cloudflare 設定：排程、資料庫、測站名稱、預報比較時刻 |
| `model/predict_daily.py` | 每日預測：抓資料、算特徵（照抄 notebook）、預測、上傳 |
| `model/model_16.joblib` | 16 時版正式模型（線性回歸，用 2017-01-01～2026-11-05 共 3,479 天訓練） |
| `model/model_meta.json` | 特徵順序、設定、訓練期間、交叉驗證與測試 MAE |
| `model/features_reference.csv` | notebook 算出的最近 30 天特徵，`--check` 用來比對 |
| `model/backtest_16.csv` | 測試期 615 天的回測預測 |
| `model/export_cell.py` | 貼到 notebook 最後的匯出 cell，重新產生上面這些檔案 |
| `model/kinmen-aqi-predict.yml` | GitHub Actions 設定（要複製到 repo 根目錄的 `.github/workflows/`） |
| `model/requirements.txt` | 跟訓練時相同的套件版本 |
| `tools/upload_prediction.py` | 上傳模型預測（Colab 可用，只用標準函式庫） |
| `data/history.sql` | 2025-01 起的每小時 AQI、官方日 AQI、預報和模型回測，可直接匯入 D1 |
| `test/lib.test.js` | 單元測試 |
| `.dev.vars.example` | 本機金鑰設定範本（`.dev.vars` 不會進 git） |

想改成其他地方，只要改 `wrangler.toml` 的 `SITE_NAME`（測站名稱，例如「馬祖」）和 `FORECAST_AREA`（空品區，例如「馬祖」「北部」）。

## 結果（測試期 2025-01-01～2026-11-05，615 天）

實測是金門站官方日 AQI；大幅變動日是比前一天變動 30 以上的日子（138 天）。網站算出的數字和期中報告 notebook 的 16 時版結果逐項相同。

| 預測來源 | MAE | RMSE | 等級猜對 | 變動日 MAE | 漲跌方向猜對 |
|---------|-----|------|---------|-----------|-------------|
| 環境部預報（前一天 16:30） | **16.9** | **21.6** | **72%** | **26.0** | **92%** |
| 我的模型（16 時版，線性回歸） | 18.6 | 25.0 | 65% | 36.6 | 76% |
| 明天＝今天（基準線） | 20.0 | 28.0 | 62% | 50.4 | 0% |

我的模型比「明天＝今天」準，大幅變動日的誤差少了約四分之一，四分之三的變動日猜對漲跌方向；但整體仍輸環境部預報，差距主要在大幅變動日。環境部預報有天氣預報可用，我的模型只有觀測資料，這是預期中的差距。notebook 裡「模型＋預報」（把環境部預報也當特徵）的 MAE 是 15.7，比單用環境部預報更準，是之後值得放上網站的版本。

## 限制與未來可做

- 即時資料是環境部的初步值，事後可能修正；這裡存的是當下抓到的版本。
- 環境部預報是整個空品區，測站只有金門一站，兩者本來就有落差，所以誤差不全是預報的錯。
- 每天的預測依賴 GitHub Actions 的排程；GitHub 尖峰時段可能延遲幾十分鐘，所以安排了 18:40 的第二次執行。
- 可把「模型＋預報」版本也放上來：16:30 的環境部預報在 16:40 執行時已經公布，可以直接當特徵。
- 可加 LINE Bot 或 Email 通知：明天預報 ≥ 101（橘燈）時提醒。
