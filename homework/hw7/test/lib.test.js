import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  taipeiNow, addDays, extractRecords, normTime, num, parseAqiValue,
  parseObservation, parseForecast, parseDailyOfficial, aqiLevel, buildDaily, computeMetrics, validatePrediction,
} from '../src/lib.js';

test('台灣時間換算', () => {
  // UTC 11/05 17:30 = 台灣 11/06 01:30
  const t = taipeiNow(new Date('2026-11-05T17:30:00Z'));
  assert.equal(t.date, '2026-11-06');
  assert.equal(t.hour, 1);
  assert.equal(t.stamp, '2026-11-06 01:30');
});

test('日期加減跨月', () => {
  assert.equal(addDays('2026-11-01', -1), '2026-10-31');
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
});

test('records 包裝與純陣列都能讀', () => {
  assert.deepEqual(extractRecords({ records: [1, 2] }), [1, 2]);
  assert.deepEqual(extractRecords([3]), [3]);
  assert.deepEqual(extractRecords('api_key 不存在。'), []);
});

test('時間格式正規化', () => {
  assert.equal(normTime('2026/11/06 09:00:00'), '2026-11-06 09:00');
  assert.equal(normTime('2026-11-6 9:30'), '2026-11-06 09:30');
  assert.equal(normTime('2026-11-07'), '2026-11-07 00:00');
  assert.equal(normTime(''), null);
  assert.equal(normTime('昨天'), null);
});

test('缺值與區間', () => {
  assert.equal(num(''), null);
  assert.equal(num('-'), null);
  assert.equal(num('ND'), null);
  assert.equal(num('12.5'), 12.5);
  assert.equal(parseAqiValue('51-70'), 61);
  assert.equal(parseAqiValue('65'), 65);
  assert.equal(parseAqiValue(''), null);
});

test('解析即時 AQI 一筆', () => {
  const r = parseObservation({
    sitename: '金門', county: '金門縣', aqi: '78', pollutant: '細懸浮微粒', status: '普通',
    'pm2.5': '25', pm10: '48', o3: '30.1', o3_8hr: '35', no2: '6.2', co: '0.3', so2: '1.1',
    wind_speed: '4.2', wind_direc: '30', publishtime: '2026/11/06 09:00:00',
  });
  assert.equal(r.site, '金門');
  assert.equal(r.time, '2026-11-06 09:00');
  assert.equal(r.aqi, 78);
  assert.equal(r.pm25, 25);
  assert.equal(r.wind_dir, 30);
});

test('解析歷史 AQI（aqx_p_488）一筆', () => {
  // 2026-11-06 實際抓到的格式
  const r = parseObservation({
    sitename: '金門', county: '金門縣', aqi: '65', pollutant: '細懸浮微粒', status: '普通',
    'pm2.5': '13', pm10: '33', o3: '47', windspeed: '2.8', winddirec: '91.0',
    datacreationdate: '2026-11-06 08:00', siteid: '77', unit: '',
  });
  assert.equal(r.time, '2026-11-06 08:00');
  assert.equal(r.aqi, 65);
  assert.equal(r.wind_speed, 2.8);
  assert.equal(r.wind_dir, 91);
});

test('大寫欄位名稱也讀得到', () => {
  const r = parseObservation({ SiteName: '金門', AQI: '40', PublishTime: '2026-11-06 10:00' });
  assert.equal(r.aqi, 40);
  assert.equal(r.site, '金門');
});

test('解析預報一筆', () => {
  const f = parseForecast({
    content: '...', publishtime: '2026-11-06 10:30', area: '金門', majorpollutant: '細懸浮微粒',
    forecastdate: '2026-11-07', aqi: '85', minorpollutant: '', minorpollutantaqi: '',
  });
  assert.deepEqual(
    { area: f.area, d: f.forecast_date, p: f.publish_time, aqi: f.aqi },
    { area: '金門', d: '2026-11-07', p: '2026-11-06 10:30', aqi: 85 });
});

test('AQI 等級邊界', () => {
  assert.equal(aqiLevel(50), 0);
  assert.equal(aqiLevel(51), 1);
  assert.equal(aqiLevel(101), 2);
  assert.equal(aqiLevel(301), 5);
  assert.equal(aqiLevel(null), null);
  assert.equal(aqiLevel(50.4), 0);   // 預測值四捨五入後分級
  assert.equal(aqiLevel(50.5), 1);
});

function hours(date, values) {
  return values.map((aqi, h) => ({ time: `${date} ${String(h).padStart(2, '0')}:00`, aqi }));
}

test('解析官方日 AQI（aqx_p_434）一筆', () => {
  // 2026-11-06 實際抓到的格式
  const r = parseDailyOfficial({
    siteid: '77', sitename: '金門', monitordate: '2026-11-05', aqi: '122', o38subindex: '122', o3subindex: '',
    pm25subindex: '91', pm10subindex: '73', cosubindex: '3', so2subindex: '52', no2subindex: '64',
  });
  assert.deepEqual(r, { site: '金門', date: '2026-11-05', aqi: 122, o38: 122, pm25: 91, pm10: 73, no2: 64 });
});

test('每日彙整：官方預報只採前一天 16:30（含）以前發布的最後一版', () => {
  const obsRows = [
    ...hours('2026-11-01', Array(24).fill(40)),
    ...hours('2026-11-02', Array(24).fill(90)),
    ...hours('2026-11-03', Array(10).fill(50)), // 不完整的一天
  ];
  const dailyRows = [{ date: '2026-11-01', aqi: 45 }, { date: '2026-11-02', aqi: 85 }];
  const fcRows = [
    { forecast_date: '2026-11-02', publish_time: '2026-10-31 16:30', aqi: 60 },
    { forecast_date: '2026-11-02', publish_time: '2026-11-01 16:30', aqi: 80 }, // 採用
    { forecast_date: '2026-11-02', publish_time: '2026-11-01 22:00', aqi: 88 }, // 比 16:30 晚，不算
    { forecast_date: '2026-11-02', publish_time: '2026-11-02 10:30', aqi: 95 }, // 當天發布，不算
  ];
  const predRows = [{ forecast_date: '2026-11-02', model: 'rf', aqi: 85 }];
  const { rows, modelNames } = buildDaily({ obsRows, dailyRows, fcRows, predRows, from: '2026-11-02', to: '2026-11-03' });

  assert.deepEqual(modelNames, ['rf']);
  const d2 = rows[0];
  assert.equal(d2.max, 90);
  assert.equal(d2.prev_max, 40);
  assert.equal(d2.daily, 85);
  assert.equal(d2.prev_daily, 45);
  assert.equal(d2.forecast, 80);
  assert.equal(d2.models.rf, 85);
  assert.equal(d2.complete, true);
  assert.equal(rows[1].complete, false);

  const late = buildDaily({ obsRows, fcRows, predRows, from: '2026-11-02', to: '2026-11-02', issue: '22:00' });
  assert.equal(late.rows[0].forecast, 88);
});

test('誤差與大幅變動日（每小時日最大值）', () => {
  const rows = [
    // 實測從 40 跳到 90（變動 50）：官方 80（方向對）、基準線 40（方向不對：沒變）、模型 30（方向錯）
    { date: 'a', complete: true, max: 90, prev_max: 40, forecast: 80, models: { m: 30 } },
    // 小變動日
    { date: 'b', complete: true, max: 50, prev_max: 45, forecast: 50, models: { m: 50 } },
    // 不完整的日子不計
    { date: 'c', complete: false, max: 10, prev_max: 50, forecast: 99, models: {} },
  ];
  const m = computeMetrics(rows, ['m'], { basis: 'max', bigChange: 20 });
  const by = Object.fromEntries(m.map((x) => [x.key, x]));

  assert.equal(by.forecast.n, 2);
  assert.equal(by.forecast.mae, 5);         // (10 + 0) / 2
  assert.equal(by.forecast.big_n, 1);
  assert.equal(by.forecast.big_dir_acc, 100);
  assert.equal(by.persistence.mae, 27.5);   // (50 + 5) / 2
  assert.equal(by.persistence.big_dir_acc, 0);
  assert.equal(by['model:m'].big_dir_acc, 0);
  assert.equal(by.forecast.level_acc, 100); // 80/90 都是普通，50/50 都是良好
});

test('只比較所有來源都有值的日子', () => {
  const rows = [
    { date: 'a', complete: true, daily: 100, prev_daily: 90, forecast: 110, models: { m: 95 } },
    { date: 'b', complete: true, daily: 50, prev_daily: 60, forecast: 70, models: {} }, // 模型沒有預測 → 整天不比
  ];
  const by = Object.fromEntries(computeMetrics(rows, ['m'], { basis: 'daily' }).map((x) => [x.key, x]));
  assert.equal(by.forecast.n, 1);
  assert.equal(by.forecast.mae, 10);
  assert.equal(by['model:m'].n, 1);
  assert.equal(by.persistence.n, 1);
});

test('官方日 AQI 當實測：不需要每小時資料完整', () => {
  const rows = [
    { date: 'a', complete: false, daily: 120, prev_daily: 80, forecast: 110, models: {} },
    { date: 'b', complete: true, daily: null, prev_daily: 120, forecast: 90, models: {} }, // 還沒公布
  ];
  const by = Object.fromEntries(computeMetrics(rows, [], { basis: 'daily', bigChange: 30 }).map((x) => [x.key, x]));
  assert.equal(by.forecast.n, 1);
  assert.equal(by.forecast.mae, 10);
  assert.equal(by.forecast.big_n, 1);          // 80 → 120 變動 40
  assert.equal(by.persistence.mae, 40);
});

test('上傳預測的檢查', () => {
  assert.equal(validatePrediction({ date: '2026-11-07', aqi: 72.34 }).value.aqi, 72.3);
  assert.equal(validatePrediction({ date: '2026-11-07', aqi: 72 }).value.model, '我的模型');
  assert.equal(validatePrediction({ date: '11/07', aqi: 72 }).ok, false);
  assert.equal(validatePrediction({ date: '2026-11-07', aqi: 900 }).ok, false);
  assert.equal(validatePrediction({ date: '2026-11-07', aqi: 'abc' }).ok, false);
});
