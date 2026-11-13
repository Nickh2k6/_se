import { test } from 'node:test';
import assert from 'node:assert/strict';
import { KinmenAqi, KinmenAqiError, aqiLevel, addDays, DEFAULT_BASE_URL } from '../src/index.js';

// 假的 fetch：記下每次請求，回傳指定的內容
function fakeFetch(body, { status = 200, raw = false } = {}) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url: String(url), init });
    return new Response(raw ? body : JSON.stringify(body), { status });
  };
  return { fn, calls };
}

const LATEST = {
  site: '金門',
  area: '金門',
  today: '2026-11-13',
  observation: { site: '金門', time: '2026-11-13 09:00', aqi: 71, pm25: 17, pollutant: '細懸浮微粒', status: '普通' },
  today_stats: { max: 76, mean: 70.8, hours: 10 },
  forecasts: [
    { forecast_date: '2026-11-13', publish_time: '2026-11-12 22:00', aqi: 70, major_pollutant: '細懸浮微粒', content: '' },
    { forecast_date: '2026-11-14', publish_time: '2026-11-13 10:30', aqi: 105, major_pollutant: '臭氧八小時', content: '' },
  ],
  predictions: [
    { forecast_date: '2026-11-13', model: '16時版', aqi: 66.4 },
    { forecast_date: '2026-11-14', model: '16時版', aqi: 50.4 },
  ],
};

test('AQI 等級邊界與小數', () => {
  assert.equal(aqiLevel(50).key, 'good');
  assert.equal(aqiLevel(50.4).key, 'good');
  assert.equal(aqiLevel(50.5).key, 'moderate');
  assert.equal(aqiLevel(151).key, 'unhealthy');
  assert.equal(aqiLevel(500).key, 'hazard');
  assert.equal(aqiLevel(null), null);
  assert.equal(aqiLevel('abc'), null);
});

test('日期加減跨年', () => {
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
});

test('now 把觀測、等級和今天統計合在一起', async () => {
  const { fn, calls } = fakeFetch(LATEST);
  const now = await new KinmenAqi({ fetch: fn }).now();
  assert.equal(calls[0].url, `${DEFAULT_BASE_URL}/api/latest`);
  assert.equal(now.aqi, 71);
  assert.equal(now.level.name, '普通');
  assert.deepEqual(now.today, { max: 76, mean: 70.8, hours: 10 });
});

test('看板沒有觀測時 now 回傳 null', async () => {
  const { fn } = fakeFetch({ ...LATEST, observation: null });
  assert.equal(await new KinmenAqi({ fetch: fn }).now(), null);
});

test('tomorrow 只取明天的預報和預測', async () => {
  const { fn } = fakeFetch(LATEST);
  const t = await new KinmenAqi({ fetch: fn }).tomorrow();
  assert.equal(t.date, '2026-11-14');
  assert.equal(t.forecast.aqi, 105);
  assert.equal(t.forecast.level.key, 'usg');
  assert.deepEqual(t.predictions.map((p) => [p.model, p.aqi, p.level.key]), [['16時版', 50.4, 'good']]);
});

test('明天的預報還沒發布時 forecast 是 null', async () => {
  const { fn } = fakeFetch({ ...LATEST, forecasts: LATEST.forecasts.slice(0, 1), predictions: [] });
  const t = await new KinmenAqi({ fetch: fn }).tomorrow();
  assert.equal(t.forecast, null);
  assert.deepEqual(t.predictions, []);
});

test('hourly 帶上 hours 並回傳 rows', async () => {
  const rows = [{ time: '2026-11-13 08:00', aqi: 72 }];
  const { fn, calls } = fakeFetch({ site: '金門', hours: 1, rows });
  assert.deepEqual(await new KinmenAqi({ fetch: fn }).hourly({ hours: 1 }), rows);
  assert.equal(calls[0].url, `${DEFAULT_BASE_URL}/api/hourly?hours=1`);
});

test('daily 的參數對應到 API 的查詢字串', async () => {
  const { fn, calls } = fakeFetch({ rows: [], metrics: [] });
  await new KinmenAqi({ fetch: fn, baseUrl: 'https://example.test/' }).daily({ days: 90, basis: 'max', bigChange: 40 });
  assert.equal(calls[0].url, 'https://example.test/api/daily?days=90&basis=max&big=40');
});

test('超出範圍的參數不送出請求', async () => {
  const { fn, calls } = fakeFetch({});
  const c = new KinmenAqi({ fetch: fn });
  await assert.rejects(c.hourly({ hours: 0 }), RangeError);
  await assert.rejects(c.hourly({ hours: 1441 }), RangeError);
  await assert.rejects(c.hourly({ hours: '24' }), RangeError);
  assert.throws(() => c.daily({ days: 1 }), RangeError);
  assert.throws(() => c.daily({ basis: 'median' }), RangeError);
  assert.equal(calls.length, 0);
});

test('API 的錯誤訊息和狀態碼會帶出來', async () => {
  const { fn } = fakeFetch({ error: '需要正確的 API_TOKEN' }, { status: 401 });
  await assert.rejects(new KinmenAqi({ fetch: fn, token: 'x' }).uploadPredictions({ date: '2026-11-14', aqi: 60 }), (err) => {
    assert.ok(err instanceof KinmenAqiError);
    assert.equal(err.status, 401);
    assert.equal(err.message, '需要正確的 API_TOKEN');
    return true;
  });
});

test('回傳不是 JSON 時丟出錯誤', async () => {
  const { fn } = fakeFetch('<html>壞掉了</html>', { status: 502, raw: true });
  await assert.rejects(new KinmenAqi({ fetch: fn }).status(), (err) => err instanceof KinmenAqiError && err.status === 502);
});

test('連不上時包成 KinmenAqiError 並保留原因', async () => {
  const cause = new TypeError('fetch failed');
  const c = new KinmenAqi({ fetch: async () => { throw cause; } });
  await assert.rejects(c.latest(), (err) => err instanceof KinmenAqiError && err.status === null && err.cause === cause);
});

test('上傳預測：單筆包成陣列並帶 token', async () => {
  const { fn, calls } = fakeFetch({ saved: 1 });
  const res = await new KinmenAqi({ fetch: fn, token: 'secret' }).uploadPredictions({ date: '2026-11-14', aqi: 60, model: 'm' });
  assert.deepEqual(res, { saved: 1 });
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer secret');
  assert.deepEqual(JSON.parse(calls[0].init.body), [{ date: '2026-11-14', aqi: 60, model: 'm' }]);
});

test('讀取的請求不帶 token', async () => {
  const { fn, calls } = fakeFetch(LATEST);
  await new KinmenAqi({ fetch: fn, token: 'secret' }).latest();
  assert.equal(calls[0].init.headers.Authorization, undefined);
});

test('沒有 token 或筆數不對時不送出上傳', async () => {
  const { fn, calls } = fakeFetch({ saved: 0 });
  assert.throws(() => new KinmenAqi({ fetch: fn }).uploadPredictions({ date: '2026-11-14', aqi: 60 }), KinmenAqiError);
  assert.throws(() => new KinmenAqi({ fetch: fn, token: 'x' }).uploadPredictions([]), RangeError);
  assert.equal(calls.length, 0);
});
