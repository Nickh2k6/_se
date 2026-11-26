# kinmen-aqi

查金門空氣品質的 Node.js 套件與指令列工具：現在的 AQI、每小時紀錄、明天的環境部預報，以及「預報到底準不準」的統計。

資料來自[金門空品看板](https://kinmen-aqi.nickh2k6.workers.dev)（hw7，架在 Cloudflare Workers 上，每小時記錄環境部的金門測站資料）。這個套件是看板公開 API 的 client，不需要申請環境部的 API 金鑰，也沒有任何依賴。

> 軟體工程 hw8：寫一個套件發在公開套件庫（npm）。
> 發佈連結：<https://www.npmjs.com/package/kinmen-aqi>

## 安裝

需要 Node.js 18.3 以上。

```bash
npm install kinmen-aqi
```

只想用指令的話不用安裝：

```bash
npx kinmen-aqi
```

## 指令列

```text
$ kinmen-aqi
金門　2026-11-13 09:00
AQI 71　普通
主要污染物：細懸浮微粒
PM2.5 17　PM10 31　臭氧 29　二氧化氮 12
風速 1.6 m/s　風向 311°
今天到目前：最高 76、平均 70.8（10 小時）

$ kinmen-aqi accuracy --days 30
金門　2026-10-15 ～ 2026-11-13　實測值：官方日 AQI
環境部預報：24 天　MAE 13.7　RMSE 15.9　等級猜對 75%
明天＝今天（基準線）：24 天　MAE 21.3　RMSE 26.3　等級猜對 45.8%
我的模型：24 天　MAE 16.7　RMSE 20.8　等級猜對 70.8%
```

| 指令 | 說明 |
| --- | --- |
| `now`（預設） | 現在的空氣品質 |
| `tomorrow` | 明天的環境部預報與模型預測 |
| `hourly --hours 24` | 每小時 AQI，最多 1440 小時；缺資料的小時照樣列出 |
| `accuracy --days 30 --basis daily` | 預報準確度；`--basis` 可為 `daily`（官方日 AQI）、`max`、`mean` |
| `status` | 看板的資料筆數與最近一次抓取 |

共用選項：`--json` 印出 JSON、`--base-url <網址>` 改連自己部署的看板、`-h`、`-v`。
失敗時（連不上、參數超出範圍）訊息印到 stderr，結束碼為 1。

## 在程式裡使用

```js
import { KinmenAqi, aqiLevel } from 'kinmen-aqi';

const aqi = new KinmenAqi();

const now = await aqi.now();
console.log(now.aqi, now.level.name); // 71 '普通'

const t = await aqi.tomorrow();
console.log(t.date, t.forecast?.aqi); // forecast 還沒發布時是 null

const rows = await aqi.hourly({ hours: 72 }); // [{ time, aqi, pm25, pm10, o3, ... }]
const stats = await aqi.daily({ days: 90, basis: 'max' }); // { rows, metrics, ... }

aqiLevel(105); // { max: 150, name: '對敏感族群不健康', key: 'usg' }
```

### `new KinmenAqi(options)`

| 選項 | 預設 | 說明 |
| --- | --- | --- |
| `baseUrl` | 金門空品看板 | 看板網址，自己部署的版本可以換掉 |
| `token` | 無 | 看板的 `API_TOKEN`，只有 `uploadPredictions` 需要 |
| `fetch` | `globalThis.fetch` | 自訂 fetch |
| `timeoutMs` | `15000` | 每次請求的逾時 |

### 方法

| 方法 | 回傳 |
| --- | --- |
| `now()` | 最新一筆觀測，加上 `level`（等級）和 `today`（今天的最高、平均、小時數）；看板沒有資料時為 `null` |
| `tomorrow()` | `{ area, date, forecast, predictions }`；`forecast` 是環境部預報，還沒發布時為 `null` |
| `hourly({ hours })` | 每小時觀測的陣列，由舊到新；`hours` 為 1～1440 |
| `daily({ days, basis, bigChange })` | 每日彙整 `rows` 與各預測來源的誤差 `metrics`；`days` 為 2～1000 |
| `latest()`、`status()` | `/api/latest`、`/api/status` 的原始內容 |
| `uploadPredictions(預測或陣列)` | 上傳 `{ date, aqi, model }`，一次最多 400 筆，回傳 `{ saved }` |

所有方法都回傳 Promise，錯誤一律以失敗的 Promise 回報（用 `await` 加 `try/catch` 或 `.catch()` 都接得到）。參數超出範圍時丟 `RangeError`，不會送出請求。API 回傳錯誤、回傳的不是 JSON 或連不上時丟 `KinmenAqiError`，`status` 是 HTTP 狀態碼（連不上時為 `null`）。

上傳預測要用看板的 `API_TOKEN`。token 請放在環境變數，不要寫進程式：

```js
const aqi = new KinmenAqi({ token: process.env.KINMEN_AQI_TOKEN });
await aqi.uploadPredictions({ date: '2026-11-14', aqi: 62.5, model: '我的模型' });
```

## 開發

```bash
npm test
```

測試用假的 fetch，不會連到看板。

## 授權

MIT
