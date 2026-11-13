// 金門空品看板（hw7 的 Cloudflare Worker）的 client。
// 只用 Node 內建的 fetch，沒有其他依賴；fetch 可以從外面換掉，方便測試。

export const DEFAULT_BASE_URL = 'https://kinmen-aqi.nickh2k6.workers.dev';

export const LEVELS = [
  { max: 50, name: '良好', key: 'good' },
  { max: 100, name: '普通', key: 'moderate' },
  { max: 150, name: '對敏感族群不健康', key: 'usg' },
  { max: 200, name: '對所有族群不健康', key: 'unhealthy' },
  { max: 300, name: '非常不健康', key: 'very' },
  { max: Infinity, name: '危害', key: 'hazard' },
];

/** 每日統計可以選的「實測值」算法，與看板的 /api/daily 相同 */
export const BASES = ['daily', 'max', 'mean'];

/** AQI → LEVELS 的一筆；預測值可能有小數，先四捨五入（與看板相同）。不是數字時回傳 null */
export function aqiLevel(aqi) {
  if (aqi === null || aqi === undefined || !Number.isFinite(Number(aqi))) return null;
  const v = Math.round(Number(aqi));
  return LEVELS.find((l) => v <= l.max);
}

/** 'YYYY-MM-DD' 加減天數 */
export function addDays(date, n) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** API 回傳錯誤、不是 JSON 或連不上時丟出；status 是 HTTP 狀態碼（連不上時為 null） */
export class KinmenAqiError extends Error {
  constructor(message, { status = null, cause } = {}) {
    super(message, { cause });
    this.name = 'KinmenAqiError';
    this.status = status;
  }
}

export class KinmenAqi {
  /**
   * @param {object} [options]
   * @param {string} [options.baseUrl] 看板網址，自己部署的版本可以換掉
   * @param {string} [options.token] API_TOKEN，只有上傳預測才需要
   * @param {typeof fetch} [options.fetch] 自訂 fetch
   * @param {number} [options.timeoutMs] 每次請求的逾時毫秒數
   */
  constructor({ baseUrl = DEFAULT_BASE_URL, token, fetch: fetchImpl = globalThis.fetch, timeoutMs = 15000 } = {}) {
    if (typeof fetchImpl !== 'function') throw new TypeError('這個環境沒有 fetch，請用 Node 18 以上或傳入 options.fetch');
    this.baseUrl = String(baseUrl).replace(/\/+$/, '');
    this.token = token;
    this.fetch = fetchImpl;
    this.timeoutMs = timeoutMs;
  }

  /** 最新觀測、今天統計、今天起 3 天的預報、模型預測（/api/latest 原始內容） */
  latest() {
    return this.#request('GET', '/api/latest');
  }

  /** 每小時觀測，由舊到新；hours 為 1～1440 */
  async hourly({ hours = 72 } = {}) {
    checkInt('hours', hours, 1, 1440);
    return (await this.#request('GET', '/api/hourly', { hours })).rows;
  }

  /**
   * 每日彙整與各預測來源的誤差統計。
   * @param {object} [options]
   * @param {number} [options.days] 2～1000
   * @param {'daily'|'max'|'mean'} [options.basis] 實測值用官方日 AQI、每小時最大或每小時平均
   * @param {number} [options.bigChange] 「大幅變動日」的門檻，1～200
   */
  daily({ days = 30, basis = 'daily', bigChange = 30 } = {}) {
    checkInt('days', days, 2, 1000);
    checkInt('bigChange', bigChange, 1, 200);
    if (!BASES.includes(basis)) throw new RangeError(`basis 要是 ${BASES.join('、')} 其中之一：${basis}`);
    return this.#request('GET', '/api/daily', { days, basis, big: bigChange });
  }

  /** 最近的抓取紀錄與資料筆數 */
  status() {
    return this.#request('GET', '/api/status');
  }

  /** 現在的空氣品質：最新一筆觀測加上等級；看板還沒有資料時回傳 null */
  async now() {
    const { site, observation, today_stats: today } = await this.latest();
    if (!observation) return null;
    return { ...observation, site, level: aqiLevel(observation.aqi), today };
  }

  /** 明天的環境部預報與模型預測；預報還沒發布時 forecast 為 null */
  async tomorrow() {
    const { area, today, forecasts, predictions } = await this.latest();
    const date = addDays(today, 1);
    const f = forecasts.find((x) => x.forecast_date === date);
    return {
      area,
      date,
      forecast: f ? { aqi: f.aqi, level: aqiLevel(f.aqi), pollutant: f.major_pollutant, published: f.publish_time } : null,
      predictions: predictions
        .filter((p) => p.forecast_date === date)
        .map((p) => ({ model: p.model, aqi: p.aqi, level: aqiLevel(p.aqi) })),
    };
  }

  /**
   * 上傳模型預測，需要 token。
   * @param {{date: string, aqi: number, model?: string} | Array<{date: string, aqi: number, model?: string}>} predictions
   * @returns {Promise<{saved: number}>}
   */
  uploadPredictions(predictions) {
    if (!this.token) throw new KinmenAqiError('上傳預測需要 token（建立 KinmenAqi 時傳入 options.token）');
    const list = Array.isArray(predictions) ? predictions : [predictions];
    if (list.length === 0 || list.length > 400) throw new RangeError('一次 1～400 筆');
    return this.#request('POST', '/api/predictions', undefined, list);
  }

  async #request(method, path, query, body) {
    const url = new URL(this.baseUrl + path);
    for (const [k, v] of Object.entries(query ?? {})) url.searchParams.set(k, String(v));

    const headers = { Accept: 'application/json' };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      headers.Authorization = `Bearer ${this.token}`;
    }

    let res;
    try {
      res = await this.fetch(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch (cause) {
      // Node 的 fetch 只說「fetch failed」，真正的原因（ENOTFOUND、ECONNRESET…）在 cause 裡
      const why = cause?.name === 'TimeoutError'
        ? `超過 ${this.timeoutMs} 毫秒沒有回應`
        : [cause?.message, cause?.cause?.code ?? cause?.cause?.message].filter(Boolean).join('：');
      throw new KinmenAqiError(`連不上 ${url.origin}：${why}`, { cause });
    }

    let data;
    try {
      data = await res.json();
    } catch (cause) {
      throw new KinmenAqiError(`${method} ${path} 回傳的不是 JSON（HTTP ${res.status}）`, { status: res.status, cause });
    }
    if (!res.ok) throw new KinmenAqiError(data?.error ?? `HTTP ${res.status}`, { status: res.status });
    return data;
  }
}

function checkInt(name, v, min, max) {
  if (!Number.isInteger(v) || v < min || v > max) throw new RangeError(`${name} 要是 ${min}～${max} 的整數：${v}`);
}
