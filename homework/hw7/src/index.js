// 金門空品看板 — Cloudflare Worker
// 排程：每小時抓環境部即時 AQI 與空品預報，存進 D1。
// HTTP：/api/* 回傳 JSON；其他路徑由 public/ 靜態檔案提供。

import {
  taipeiNow, addDays, extractRecords, parseObservation, parseForecast, parseDailyOfficial,
  buildDaily, computeMetrics, validatePrediction, BASES,
} from './lib.js';

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(collect(env));
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname.startsWith('/api/')) return await route(request, env, url);
      return env.ASSETS.fetch(request);
    } catch (err) {
      console.error(err);
      return json({ error: '伺服器錯誤', detail: String(err?.message ?? err) }, 500);
    }
  },
};

// ---------- 抓資料 ----------

// filters 是環境部 API 的篩選語法，例如 'sitename,EQ,金門'，多個條件用 | 連接。
// 環境部 API 預設不保證排序、分頁之間會重複也會漏，所以一定要指定 sort。
async function fetchDataset(env, id, { filters, sort, offset = 0, limit = 1000 } = {}) {
  if (!env.MOENV_API_KEY) throw new Error('沒有設定 MOENV_API_KEY');
  const base = env.MOENV_BASE || 'https://data.moenv.gov.tw/api/v2';
  const params = new URLSearchParams({ format: 'JSON', limit: String(limit), offset: String(offset), api_key: env.MOENV_API_KEY });
  if (filters) params.set('filters', filters);
  if (sort) params.set('sort', sort);
  const res = await fetch(`${base}/${id}?${params}`, { headers: { 'User-Agent': 'kinmen-aqi-dashboard' } });
  const text = await res.text();
  if (!res.ok) throw new Error(`${id} HTTP ${res.status}：${text.slice(0, 80)}`);
  try {
    return extractRecords(JSON.parse(text));
  } catch {
    // 金鑰錯誤時環境部回傳的是一行中文純文字，不是 JSON
    throw new Error(`${id} 回傳不是 JSON：${text.slice(0, 80)}`);
  }
}

export async function collect(env) {
  const site = env.SITE_NAME || '金門';
  const area = env.FORECAST_AREA || '金門';
  const result = { observations: 0, forecasts: 0, daily: 0, errors: [] };

  const [obsRes, fcRes, dailyRes] = await Promise.allSettled([
    fetchDataset(env, 'aqx_p_432', { filters: `sitename,EQ,${site}` }),
    // 預報資料集保留過去各版；最新 30 筆約是最近 3 天、每天 3 版
    fetchDataset(env, 'aqf_p_01', { filters: `area,EQ,${area}`, sort: 'publishtime desc', limit: 30 }),
    // 官方日 AQI 隔天早上才公布，抓最近幾天就夠
    fetchDataset(env, 'aqx_p_434', { filters: `sitename,EQ,${site}`, sort: 'monitordate desc', limit: 10 }),
  ]);

  if (obsRes.status === 'fulfilled') {
    const rows = obsRes.value.map(parseObservation).filter((r) => r && r.site === site);
    if (rows.length === 0) result.errors.push(`即時資料裡找不到「${site}」測站`);
    result.observations = await saveObservations(env, rows);
  } else {
    result.errors.push(obsRes.reason.message);
  }

  if (fcRes.status === 'fulfilled') {
    const rows = fcRes.value.map(parseForecast).filter((r) => r && r.area === area);
    if (rows.length === 0) result.errors.push(`預報資料裡找不到「${area}」空品區`);
    result.forecasts = await saveForecasts(env, rows);
  } else {
    result.errors.push(fcRes.reason.message);
  }

  if (dailyRes.status === 'fulfilled') {
    const rows = dailyRes.value.map(parseDailyOfficial).filter((r) => r && r.site === site);
    result.daily = await saveDaily(env, rows);
  } else {
    result.errors.push(dailyRes.reason.message);
  }

  const ok = result.errors.length === 0;
  await env.DB.batch([
    env.DB.prepare('INSERT INTO fetch_log (time, ok, observations, forecasts, message) VALUES (?,?,?,?,?)')
      .bind(new Date().toISOString(), ok ? 1 : 0, result.observations, result.forecasts,
        result.errors.join('；') || null),
    // 紀錄只留最近 500 筆
    env.DB.prepare('DELETE FROM fetch_log WHERE id NOT IN (SELECT id FROM fetch_log ORDER BY id DESC LIMIT 500)'),
  ]);
  if (!ok) console.warn('collect errors:', result.errors);
  return result;
}

async function saveObservations(env, rows) {
  const stmt = env.DB.prepare(
    `INSERT OR REPLACE INTO observations
     (site, time, aqi, pm25, pm10, o3, o3_8hr, no2, co, so2, wind_speed, wind_dir, pollutant, status)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`);
  for (let i = 0; i < rows.length; i += 100) {
    await env.DB.batch(rows.slice(i, i + 100).map((r) => stmt.bind(
      r.site, r.time, r.aqi, r.pm25, r.pm10, r.o3, r.o3_8hr, r.no2, r.co, r.so2,
      r.wind_speed, r.wind_dir, r.pollutant, r.status)));
  }
  return rows.length;
}

async function saveDaily(env, rows) {
  const stmt = env.DB.prepare(
    'INSERT OR REPLACE INTO daily_official (site, date, aqi, o38, pm25, pm10, no2) VALUES (?,?,?,?,?,?,?)');
  for (let i = 0; i < rows.length; i += 100) {
    await env.DB.batch(rows.slice(i, i + 100).map((r) => stmt.bind(r.site, r.date, r.aqi, r.o38, r.pm25, r.pm10, r.no2)));
  }
  return rows.length;
}

async function saveForecasts(env, rows) {
  const stmt = env.DB.prepare(
    `INSERT OR REPLACE INTO forecasts (area, forecast_date, publish_time, aqi, major_pollutant, content)
     VALUES (?,?,?,?,?,?)`);
  for (let i = 0; i < rows.length; i += 100) {
    await env.DB.batch(rows.slice(i, i + 100).map((r) => stmt.bind(
      r.area, r.forecast_date, r.publish_time, r.aqi, r.major_pollutant, r.content)));
  }
  return rows.length;
}

/** 抓某個日期之後的全部資料：用日期篩選＋排序，一路翻到最後一頁 */
async function fetchSince(env, id, filters, sort, maxPages = 40) {
  const all = [];
  for (let page = 0; page < maxPages; page++) {
    const recs = await fetchDataset(env, id, { filters, sort, offset: page * 1000 });
    all.push(...recs);
    if (recs.length < 1000) return all;
  }
  throw new Error(`${id} 超過 ${maxPages} 頁，請縮短補抓天數`);
}

/**
 * 補抓過去 days 天的資料：
 * - 觀測：歷史 AQI 資料集 aqx_p_488（每小時，含今天）
 * - 官方日 AQI：aqx_p_434（一天一筆，原始資料有重複列，存檔時依日期去重）
 * - 預報：aqf_p_01 本身就保留過去各版
 */
export async function backfill(env, days) {
  const site = env.SITE_NAME || '金門';
  const area = env.FORECAST_AREA || '金門';
  const start = addDays(taipeiNow().date, -days); // 從 days 天前的 00:00 開始
  const fcStart = addDays(start, -2);             // 預報最早要涵蓋到「目標日前兩天」發布的版本
  const dailyStart = addDays(start, -1);          // 多一天給「明天＝今天」基準線

  const [obsRecs, fcRecs, dailyRecs] = await Promise.all([
    fetchSince(env, 'aqx_p_488', `sitename,EQ,${site}|datacreationdate,GR,${addDays(start, -1)} 23:00`, 'datacreationdate desc'),
    fetchSince(env, 'aqf_p_01', `area,EQ,${area}|publishtime,GR,${addDays(fcStart, -1)} 23:59`, 'publishtime desc'),
    fetchSince(env, 'aqx_p_434', `sitename,EQ,${site}|monitordate,GR,${addDays(dailyStart, -1)}`, 'monitordate desc'),
  ]);

  // API 的範圍篩選是字串比較，這裡再確認一次範圍，並依主鍵去重
  const dedupe = (rows, key) => [...new Map(rows.map((r) => [key(r), r])).values()];
  const obs = dedupe(obsRecs.map(parseObservation).filter((r) => r && r.site === site && r.time >= `${start} 00:00`), (r) => r.time);
  const fc = dedupe(fcRecs.map(parseForecast).filter((r) => r && r.area === area && r.publish_time >= `${fcStart} 00:00`),
    (r) => `${r.forecast_date}|${r.publish_time}`);
  const daily = dedupe(dailyRecs.map(parseDailyOfficial).filter((r) => r && r.site === site && r.date >= dailyStart), (r) => r.date);

  await saveObservations(env, obs);
  await saveForecasts(env, fc);
  await saveDaily(env, daily);
  const times = obs.map((r) => r.time).sort();
  return {
    from: start,
    observations: obs.length,
    first_observation: times[0] ?? null,
    last_observation: times.at(-1) ?? null,
    forecasts: fc.length,
    daily: daily.length,
  };
}

// ---------- API ----------

async function route(request, env, url) {
  const { pathname } = url;
  const method = request.method;

  if (method === 'OPTIONS') return new Response(null, { status: 204, headers: corsHeaders() });

  if (method === 'GET' && pathname === '/api/latest') return latest(env);
  if (method === 'GET' && pathname === '/api/hourly') return hourly(env, url);
  if (method === 'GET' && pathname === '/api/daily') return daily(env, url);
  if (method === 'GET' && pathname === '/api/status') return status(env);

  if (method === 'POST' && pathname === '/api/predictions') {
    if (!authorized(request, env)) return json({ error: '需要正確的 API_TOKEN' }, 401);
    return postPredictions(request, env);
  }
  if (method === 'POST' && pathname === '/api/collect') {
    if (!authorized(request, env)) return json({ error: '需要正確的 API_TOKEN' }, 401);
    return json(await collect(env));
  }
  if (method === 'POST' && pathname === '/api/backfill') {
    if (!authorized(request, env)) return json({ error: '需要正確的 API_TOKEN' }, 401);
    const max = clampInt(env.MAX_BACKFILL_DAYS, 1, 3650, 90);
    const days = clampInt(url.searchParams.get('days'), 1, max, 14);
    return json(await backfill(env, days));
  }

  return json({ error: `沒有這個 API：${method} ${pathname}` }, 404);
}

function authorized(request, env) {
  const token = env.API_TOKEN;
  if (!token) return false; // 沒設定就一律拒絕寫入
  const h = request.headers.get('Authorization') || '';
  const given = h.startsWith('Bearer ') ? h.slice(7) : '';
  if (given.length !== token.length) return false;
  let diff = 0;
  for (let i = 0; i < token.length; i++) diff |= token.charCodeAt(i) ^ given.charCodeAt(i);
  return diff === 0;
}

async function latest(env) {
  const site = env.SITE_NAME || '金門';
  const area = env.FORECAST_AREA || '金門';
  const today = taipeiNow().date;

  const obs = await env.DB.prepare(
    'SELECT * FROM observations WHERE site = ? AND aqi IS NOT NULL ORDER BY time DESC LIMIT 1').bind(site).first();

  // 每個預報日取最新發布的一版
  const { results: forecasts } = await env.DB.prepare(
    `SELECT f.forecast_date, f.publish_time, f.aqi, f.major_pollutant, f.content
       FROM forecasts f
       JOIN (SELECT forecast_date, MAX(publish_time) AS p FROM forecasts
              WHERE area = ? AND forecast_date >= ? GROUP BY forecast_date) last
         ON f.forecast_date = last.forecast_date AND f.publish_time = last.p
      WHERE f.area = ?
      ORDER BY f.forecast_date LIMIT 3`).bind(area, today, area).all();

  const { results: predictions } = await env.DB.prepare(
    'SELECT forecast_date, model, aqi FROM predictions WHERE forecast_date >= ? ORDER BY forecast_date, model')
    .bind(today).all();

  const todayStats = await env.DB.prepare(
    'SELECT MAX(aqi) AS max, ROUND(AVG(aqi),1) AS mean, COUNT(aqi) AS hours FROM observations WHERE site = ? AND time LIKE ?')
    .bind(site, `${today}%`).first();

  return json({ site, area, today, observation: obs, today_stats: todayStats, forecasts, predictions }, 200, 300);
}

async function hourly(env, url) {
  const site = env.SITE_NAME || '金門';
  const hours = clampInt(url.searchParams.get('hours'), 1, 24 * 60, 72);
  const { results } = await env.DB.prepare(
    `SELECT time, aqi, pm25, pm10, o3, wind_speed, pollutant, status
       FROM (SELECT * FROM observations WHERE site = ? ORDER BY time DESC LIMIT ?)
      ORDER BY time`).bind(site, hours).all();
  return json({ site, hours, rows: results }, 200, 300);
}

async function daily(env, url) {
  const site = env.SITE_NAME || '金門';
  const area = env.FORECAST_AREA || '金門';
  const days = clampInt(url.searchParams.get('days'), 2, 1000, 30);
  const b = url.searchParams.get('basis');
  const basis = Object.hasOwn(BASES, b) ? b : 'daily';
  const bigChange = clampInt(url.searchParams.get('big'), 1, 200, 30);
  const issue = /^\d{2}:\d{2}$/.test(env.FORECAST_ISSUE ?? '') ? env.FORECAST_ISSUE : '16:30';

  const to = taipeiNow().date;
  const from = addDays(to, -(days - 1));
  const before = addDays(from, -1); // 多抓一天算「明天＝今天」基準線

  const [obs, dly, fc, pred] = await env.DB.batch([
    env.DB.prepare('SELECT time, aqi FROM observations WHERE site = ? AND time >= ? ORDER BY time').bind(site, before),
    env.DB.prepare('SELECT date, aqi FROM daily_official WHERE site = ? AND date >= ?').bind(site, before),
    env.DB.prepare('SELECT forecast_date, publish_time, aqi FROM forecasts WHERE area = ? AND forecast_date >= ?').bind(area, from),
    env.DB.prepare('SELECT forecast_date, model, aqi FROM predictions WHERE forecast_date >= ?').bind(from),
  ]);

  const { rows, modelNames } = buildDaily({
    obsRows: obs.results, dailyRows: dly.results, fcRows: fc.results, predRows: pred.results, from, to, issue,
  });
  const metrics = computeMetrics(rows, modelNames, { basis, bigChange });
  return json({
    site, area, from, to, basis, basis_label: BASES[basis], big_change: bigChange, forecast_issue: issue,
    models: modelNames, rows, metrics,
  }, 200, 300);
}

async function status(env) {
  const { results } = await env.DB.prepare(
    'SELECT time, ok, observations, forecasts, message FROM fetch_log ORDER BY id DESC LIMIT 10').all();
  const counts = await env.DB.prepare(
    `SELECT (SELECT COUNT(*) FROM observations) AS observations,
            (SELECT COUNT(*) FROM forecasts) AS forecasts,
            (SELECT COUNT(*) FROM predictions) AS predictions,
            (SELECT COUNT(*) FROM daily_official) AS daily_official,
            (SELECT MIN(time) FROM observations) AS first_observation`).first();
  return json({ recent: results, counts }, 200, 60);
}

async function postPredictions(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: '內容要是 JSON' }, 400);
  }
  const list = Array.isArray(body) ? body : [body];
  if (list.length === 0 || list.length > 400) return json({ error: '一次 1～400 筆' }, 400);

  const values = [];
  for (const [i, p] of list.entries()) {
    const v = validatePrediction(p);
    if (!v.ok) return json({ error: `第 ${i + 1} 筆：${v.error}` }, 400);
    values.push(v.value);
  }
  const now = new Date().toISOString();
  const stmt = env.DB.prepare(
    'INSERT OR REPLACE INTO predictions (forecast_date, model, aqi, created_at) VALUES (?,?,?,?)');
  await env.DB.batch(values.map((v) => stmt.bind(v.forecast_date, v.model, v.aqi, now)));
  return json({ saved: values.length });
}

// ---------- 工具 ----------

function clampInt(v, min, max, dflt) {
  const n = Number.parseInt(v ?? '', 10);
  if (!Number.isFinite(n)) return dflt;
  return Math.min(max, Math.max(min, n));
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
  };
}

function json(data, status = 200, maxAge = 0) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': maxAge ? `public, max-age=${maxAge}` : 'no-store',
      ...corsHeaders(),
    },
  });
}
