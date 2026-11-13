// CLI 的文字輸出。純函式，不碰網路，方便單獨測試。

import { aqiLevel } from './index.js';

const dash = (v, unit = '') => (v === null || v === undefined ? '—' : `${v}${unit}`);
const levelName = (aqi) => aqiLevel(aqi)?.name ?? '沒有資料';

/** KinmenAqi#now() 的結果 */
export function formatNow(now) {
  if (!now) return '看板目前沒有觀測資料';
  const lines = [
    `${now.site}　${now.time}`,
    `AQI ${dash(now.aqi)}　${levelName(now.aqi)}`,
    `主要污染物：${now.pollutant || '—'}`,
    `PM2.5 ${dash(now.pm25)}　PM10 ${dash(now.pm10)}　臭氧 ${dash(now.o3)}　二氧化氮 ${dash(now.no2)}`,
    `風速 ${dash(now.wind_speed, ' m/s')}　風向 ${dash(now.wind_dir, '°')}`,
  ];
  if (now.today?.hours) {
    lines.push(`今天到目前：最高 ${dash(now.today.max)}、平均 ${dash(now.today.mean)}（${now.today.hours} 小時）`);
  }
  return lines.join('\n');
}

/** KinmenAqi#tomorrow() 的結果 */
export function formatTomorrow(t) {
  const lines = [`${t.area}　明天 ${t.date}`];
  lines.push(t.forecast
    ? `環境部預報：AQI ${t.forecast.aqi}　${levelName(t.forecast.aqi)}（${t.forecast.published} 發布）`
    : '環境部預報：還沒發布');
  for (const p of t.predictions) lines.push(`${p.model}：AQI ${p.aqi}　${levelName(p.aqi)}`);
  if (t.predictions.length === 0) lines.push('模型預測：還沒上傳');
  return lines.join('\n');
}

/** KinmenAqi#hourly() 的結果，一小時一行，缺值的小時照樣列出 */
export function formatHourly(rows) {
  if (rows.length === 0) return '這段時間沒有觀測資料';
  return rows
    .map((r) => `${r.time}  ${String(dash(r.aqi)).padStart(3)}  ${r.aqi === null ? '缺資料' : levelName(r.aqi)}`)
    .join('\n');
}

/** KinmenAqi#daily() 的結果，只列誤差統計 */
export function formatAccuracy(d) {
  const lines = [`${d.site}　${d.from} ～ ${d.to}　實測值：${d.basis_label}`];
  for (const m of d.metrics) {
    lines.push(m.n === 0
      ? `${m.label}：沒有可比較的天數`
      : `${m.label}：${m.n} 天　MAE ${dash(m.mae)}　RMSE ${dash(m.rmse)}　等級猜對 ${dash(m.level_acc, '%')}`);
  }
  return lines.join('\n');
}

/** KinmenAqi#status() 的結果 */
export function formatStatus(s) {
  const c = s.counts;
  const last = s.recent[0];
  const lines = [
    `觀測 ${c.observations} 筆（從 ${dash(c.first_observation)} 起）、預報 ${c.forecasts} 筆、模型預測 ${c.predictions} 筆、官方日 AQI ${c.daily_official} 筆`,
  ];
  if (last) lines.push(`最近一次抓取：${last.time}　${last.ok ? '成功' : `失敗（${last.message ?? '沒有訊息'}）`}`);
  return lines.join('\n');
}
