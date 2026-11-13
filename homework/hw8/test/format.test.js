import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatNow, formatTomorrow, formatHourly, formatAccuracy, formatStatus } from '../src/format.js';

test('now：有資料與沒有資料', () => {
  const out = formatNow({
    site: '金門', time: '2026-11-13 09:00', aqi: 71, pollutant: '細懸浮微粒',
    pm25: 17, pm10: 31, o3: 29, no2: null, wind_speed: 1.6, wind_dir: 311,
    today: { max: 76, mean: 70.8, hours: 10 },
  });
  assert.match(out, /AQI 71　普通/);
  assert.match(out, /二氧化氮 —/);
  assert.match(out, /最高 76、平均 70.8（10 小時）/);
  assert.equal(formatNow(null), '看板目前沒有觀測資料');
});

test('tomorrow：預報和預測都還沒有', () => {
  const out = formatTomorrow({ area: '金門', date: '2026-11-14', forecast: null, predictions: [] });
  assert.match(out, /環境部預報：還沒發布/);
  assert.match(out, /模型預測：還沒上傳/);
});

test('tomorrow：預報和預測並列', () => {
  const out = formatTomorrow({
    area: '金門', date: '2026-11-14',
    forecast: { aqi: 105, published: '2026-11-13 10:30' },
    predictions: [{ model: '16時版', aqi: 50.4 }],
  });
  assert.match(out, /環境部預報：AQI 105　對敏感族群不健康/);
  assert.match(out, /16時版：AQI 50.4　良好/);
});

test('hourly：缺值的小時照樣列出', () => {
  const out = formatHourly([{ time: '2026-11-13 08:00', aqi: 72 }, { time: '2026-11-13 09:00', aqi: null }]);
  assert.deepEqual(out.split('\n'), ['2026-11-13 08:00   72  普通', '2026-11-13 09:00    —  缺資料']);
  assert.equal(formatHourly([]), '這段時間沒有觀測資料');
});

test('accuracy：沒有可比較天數的來源另外說明', () => {
  const out = formatAccuracy({
    site: '金門', from: '2026-11-11', to: '2026-11-13', basis_label: '官方日 AQI',
    metrics: [
      { label: '環境部預報', n: 2, mae: 14, rmse: 14.3, level_acc: 50 },
      { label: '我的模型', n: 0, mae: null, rmse: null, level_acc: null },
    ],
  });
  assert.match(out, /環境部預報：2 天　MAE 14　RMSE 14.3　等級猜對 50%/);
  assert.match(out, /我的模型：沒有可比較的天數/);
});

test('status：最近一次抓取失敗時顯示訊息', () => {
  const counts = { observations: 5, forecasts: 3, predictions: 1, daily_official: 2, first_observation: '2024-12-31 00:00' };
  assert.match(formatStatus({ counts, recent: [{ time: 't', ok: 0, message: 'api_key 不存在' }] }), /失敗（api_key 不存在）/);
  assert.match(formatStatus({ counts, recent: [{ time: 't', ok: 1, message: null }] }), /成功/);
  assert.doesNotMatch(formatStatus({ counts, recent: [] }), /最近一次抓取/);
});
