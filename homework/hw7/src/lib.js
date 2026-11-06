// 純函式：解析環境部資料、時間處理、統計比較。
// 不碰 D1 或網路，方便用 node --test 單獨測試。

const TZ_OFFSET_MS = 8 * 60 * 60 * 1000; // 台灣時間 UTC+8，沒有日光節約

/** 取得台灣時間的 { date: 'YYYY-MM-DD', hour: 0-23, stamp: 'YYYY-MM-DD HH:MM' } */
export function taipeiNow(now = new Date()) {
  const t = new Date(now.getTime() + TZ_OFFSET_MS);
  const date = t.toISOString().slice(0, 10);
  const hh = String(t.getUTCHours()).padStart(2, '0');
  const mm = String(t.getUTCMinutes()).padStart(2, '0');
  return { date, hour: t.getUTCHours(), stamp: `${date} ${hh}:${mm}` };
}

/** 'YYYY-MM-DD' 加減天數 */
export function addDays(date, n) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** 環境部 API 有時回傳 { records: [...] }，有時直接是陣列 */
export function extractRecords(json) {
  if (Array.isArray(json)) return json;
  if (json && Array.isArray(json.records)) return json.records;
  return [];
}

/** 不分大小寫取欄位，依序嘗試多個名稱 */
export function pick(rec, ...names) {
  const lower = {};
  for (const k of Object.keys(rec)) lower[k.toLowerCase()] = rec[k];
  for (const n of names) {
    const v = lower[n.toLowerCase()];
    if (v !== undefined) return v;
  }
  return undefined;
}

/** 數值欄位：空字串、'-'、'ND'、'x' 等都當成缺值 */
export function num(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (s === '' || /^(-|nd|na|x|n\/a)$/i.test(s)) return null;
  const f = Number(s);
  return Number.isFinite(f) ? f : null;
}

/** 預報 AQI 可能是 '65' 或區間 '51-70'，區間取中間值 */
export function parseAqiValue(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  const m = s.match(/^(\d+)\s*[-~～]\s*(\d+)$/);
  if (m) return Math.round((Number(m[1]) + Number(m[2])) / 2);
  const n = num(s);
  return n === null ? null : Math.round(n);
}

/** '2026/11/06 9:00:00'、'2026-11-06 09:00' → '2026-11-06 09:00'；看不懂回傳 null */
export function normTime(v) {
  if (!v) return null;
  const m = String(v).trim().match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:[ T](\d{1,2}):(\d{2}))?/);
  if (!m) return null;
  const [, y, mo, d, h = '0', mi = '00'] = m;
  return `${y}-${mo.padStart(2, '0')}-${d.padStart(2, '0')} ${h.padStart(2, '0')}:${mi}`;
}

/**
 * AQI 一筆 → 我們的欄位；時間看不懂時回傳 null。
 * 即時資料（aqx_p_432）和歷史資料（aqx_p_488）欄位名稱有點不同：
 *   時間 publishtime / datacreationdate、風速 wind_speed / windspeed、風向 wind_direc / winddirec
 */
export function parseObservation(rec) {
  const time = normTime(pick(rec, 'publishtime', 'datacreationdate'));
  if (!time) return null;
  return {
    site: String(pick(rec, 'sitename', 'SiteName') ?? '').trim(),
    time,
    aqi: parseAqiValue(pick(rec, 'aqi', 'AQI')),
    pm25: num(pick(rec, 'pm2.5', 'pm2_5', 'PM2.5')),
    pm10: num(pick(rec, 'pm10', 'PM10')),
    o3: num(pick(rec, 'o3', 'O3')),
    o3_8hr: num(pick(rec, 'o3_8hr', 'O3_8hr')),
    no2: num(pick(rec, 'no2', 'NO2')),
    co: num(pick(rec, 'co', 'CO')),
    so2: num(pick(rec, 'so2', 'SO2')),
    wind_speed: num(pick(rec, 'wind_speed', 'windspeed')),
    wind_dir: num(pick(rec, 'wind_direc', 'winddirec')),
    pollutant: String(pick(rec, 'pollutant', 'Pollutant') ?? '').trim(),
    status: String(pick(rec, 'status', 'Status') ?? '').trim(),
  };
}

/** 空品預報（aqf_p_01）的一筆 → 我們的欄位 */
export function parseForecast(rec) {
  const forecastDate = normTime(pick(rec, 'forecastdate', 'ForecastDate'))?.slice(0, 10);
  const publishTime = normTime(pick(rec, 'publishtime', 'PublishTime'));
  if (!forecastDate || !publishTime) return null;
  return {
    area: String(pick(rec, 'area', 'Area') ?? '').trim(),
    forecast_date: forecastDate,
    publish_time: publishTime,
    aqi: parseAqiValue(pick(rec, 'aqi', 'AQI')),
    major_pollutant: String(pick(rec, 'majorpollutant', 'MajorPollutant') ?? '').trim(),
    content: String(pick(rec, 'content', 'Content') ?? '').trim(),
  };
}

export const LEVELS = [
  { max: 50, name: '良好', key: 'good' },
  { max: 100, name: '普通', key: 'moderate' },
  { max: 150, name: '對敏感族群不健康', key: 'usg' },
  { max: 200, name: '對所有族群不健康', key: 'unhealthy' },
  { max: 300, name: '非常不健康', key: 'very' },
  { max: Infinity, name: '危害', key: 'hazard' },
];

/** AQI 等級；預測值可能有小數，先四捨五入（50.4 算良好、50.5 算普通，與 notebook 的 level() 相同） */
export function aqiLevel(aqi) {
  if (aqi === null || aqi === undefined) return null;
  const v = Math.round(aqi);
  return LEVELS.findIndex((l) => v <= l.max);
}

/** 官方日 AQI（aqx_p_434）的一筆 → 我們的欄位 */
export function parseDailyOfficial(rec) {
  const date = normTime(pick(rec, 'monitordate', 'MonitorDate'))?.slice(0, 10);
  if (!date) return null;
  const sub = (k) => parseAqiValue(pick(rec, k));
  return {
    site: String(pick(rec, 'sitename', 'SiteName') ?? '').trim(),
    date,
    aqi: parseAqiValue(pick(rec, 'aqi', 'AQI')),
    o38: sub('o38subindex'),
    pm25: sub('pm25subindex'),
    pm10: sub('pm10subindex'),
    no2: sub('no2subindex'),
  };
}

/** 實測值的三種定義：官方日 AQI、測站每小時 AQI 的日最大值、日平均 */
export const BASES = {
  daily: '官方日 AQI',
  max: '每小時 AQI 日最大值',
  mean: '每小時 AQI 日平均',
};

/**
 * 把每小時觀測、官方日 AQI、預報、模型預測整理成「每天一列」。
 * obsRows:   [{ time, aqi }]
 * dailyRows: [{ date, aqi }]
 * fcRows:    [{ forecast_date, publish_time, aqi }]
 * predRows:  [{ forecast_date, model, aqi }]
 * 官方預報只採用「目標日前一天 issue 時刻（含）以前」發布的最後一版。
 * issue 預設 '16:30'：跟 16 時版模型（只用當天 16:00 前的資料）比較才公平。
 */
export function buildDaily({ obsRows, dailyRows = [], fcRows, predRows, from, to, minHours = 18, issue = '16:30' }) {
  const obs = new Map();
  for (const r of obsRows) {
    if (r.aqi === null || r.aqi === undefined) continue;
    const d = r.time.slice(0, 10);
    const o = obs.get(d) ?? { max: -Infinity, sum: 0, n: 0 };
    o.max = Math.max(o.max, r.aqi);
    o.sum += r.aqi;
    o.n += 1;
    obs.set(d, o);
  }

  const daily = new Map();
  for (const r of dailyRows) if (r.aqi !== null && r.aqi !== undefined) daily.set(r.date, r.aqi);

  const forecast = new Map(); // date → { aqi, publish_time }
  for (const f of fcRows) {
    if (f.aqi === null || f.aqi === undefined) continue;
    const cutoff = `${addDays(f.forecast_date, -1)} ${issue}`;
    if (f.publish_time > cutoff) continue; // 比截止時刻晚發布的版本不算
    const cur = forecast.get(f.forecast_date);
    if (!cur || f.publish_time > cur.publish_time) forecast.set(f.forecast_date, f);
  }

  const models = new Map(); // date → { model: aqi }
  const modelNames = new Set();
  for (const p of predRows) {
    modelNames.add(p.model);
    const m = models.get(p.forecast_date) ?? {};
    m[p.model] = p.aqi;
    models.set(p.forecast_date, m);
  }

  const round1 = (x) => Math.round(x * 10) / 10;
  const rows = [];
  for (let d = from; d <= to; d = addDays(d, 1)) {
    const prevDate = addDays(d, -1);
    const o = obs.get(d);
    const prev = obs.get(prevDate);
    const complete = !!o && o.n >= minHours;
    const prevComplete = !!prev && prev.n >= minHours;
    rows.push({
      date: d,
      hours: o?.n ?? 0,
      complete,
      daily: daily.get(d) ?? null,
      prev_daily: daily.get(prevDate) ?? null,
      max: o ? o.max : null,
      mean: o ? round1(o.sum / o.n) : null,
      prev_max: prevComplete ? prev.max : null,
      prev_mean: prevComplete ? round1(prev.sum / prev.n) : null,
      forecast: forecast.get(d)?.aqi ?? null,
      forecast_published: forecast.get(d)?.publish_time ?? null,
      models: models.get(d) ?? {},
    });
  }
  return { rows, modelNames: [...modelNames].sort() };
}

/** 這一列在指定實測定義下的「實測值」與「前一天實測值」；資料不足回傳 null */
export function actualOf(row, basis) {
  if (basis === 'daily') return { actual: row.daily, prev: row.prev_daily };
  if (!row.complete) return { actual: null, prev: null };
  return basis === 'mean'
    ? { actual: row.mean, prev: row.prev_mean }
    : { actual: row.max, prev: row.prev_max };
}

/**
 * 計算每個預測來源的誤差。
 * basis: 'daily' 官方日 AQI、'max' 每小時日最大值、'mean' 每小時日平均。
 * 大幅變動日：|今天實測 − 昨天實測| ≥ bigChange。
 * 方向命中：預測的漲跌方向（預測值 − 昨天實測）和實際漲跌一致。
 * 只比較「實測和每個來源都有值」的日子，所有來源的天數相同，誤差才能直接比。
 */
export function computeMetrics(rows, modelNames, { basis = 'daily', bigChange = 30 } = {}) {
  const sources = [
    { key: 'forecast', label: '環境部預報', get: (r) => r.forecast },
    { key: 'persistence', label: '明天＝今天（基準線）', get: (r) => actualOf(r, basis).prev },
    ...modelNames.map((m) => ({ key: `model:${m}`, label: m, get: (r) => r.models[m] ?? null })),
  ];

  const common = rows.filter((r) => actualOf(r, basis).actual !== null
    && sources.every((s) => s.get(r) !== null && s.get(r) !== undefined));

  return sources.map((s) => {
    let n = 0, absSum = 0, sqSum = 0, levelHit = 0;
    let bn = 0, bAbs = 0, bDir = 0;
    for (const r of common) {
      const { actual, prev } = actualOf(r, basis);
      const pred = s.get(r);
      if (actual === null || pred === null || pred === undefined) continue;
      const err = pred - actual;
      n += 1;
      absSum += Math.abs(err);
      sqSum += err * err;
      if (aqiLevel(pred) === aqiLevel(actual)) levelHit += 1;
      if (prev !== null && Math.abs(actual - prev) >= bigChange) {
        bn += 1;
        bAbs += Math.abs(err);
        if (Math.sign(pred - prev) === Math.sign(actual - prev)) bDir += 1;
      }
    }
    const r1 = (x) => Math.round(x * 10) / 10;
    return {
      key: s.key,
      label: s.label,
      n,
      mae: n ? r1(absSum / n) : null,
      rmse: n ? r1(Math.sqrt(sqSum / n)) : null,
      level_acc: n ? r1((levelHit / n) * 100) : null,
      big_n: bn,
      big_mae: bn ? r1(bAbs / bn) : null,
      big_dir_acc: bn ? r1((bDir / bn) * 100) : null,
    };
  });
}

/** 檢查上傳的模型預測，回傳 { ok, value } 或 { ok:false, error } */
export function validatePrediction(p) {
  if (!p || typeof p !== 'object') return { ok: false, error: '每一筆都要是物件' };
  const date = String(p.date ?? '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(`${date}T00:00:00Z`))) {
    return { ok: false, error: `date 要是 YYYY-MM-DD：${date}` };
  }
  const aqi = Number(p.aqi);
  if (!Number.isFinite(aqi) || aqi < 0 || aqi > 500) {
    return { ok: false, error: `aqi 要是 0～500 的數字：${p.aqi}` };
  }
  const model = String(p.model ?? '我的模型').trim();
  if (!model || model.length > 40) return { ok: false, error: 'model 名稱要 1～40 字' };
  return { ok: true, value: { forecast_date: date, model, aqi: Math.round(aqi * 10) / 10 } };
}
