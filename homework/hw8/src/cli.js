#!/usr/bin/env node
// 指令列入口：解析參數、呼叫 client、印出結果。邏輯都在 index.js 和 format.js。

import { readFileSync } from 'node:fs';
import net from 'node:net';
import { parseArgs } from 'node:util';
import { KinmenAqi, DEFAULT_BASE_URL } from './index.js';
import { formatNow, formatTomorrow, formatHourly, formatAccuracy, formatStatus } from './format.js';

const HELP = `用法：kinmen-aqi [指令] [選項]

指令：
  now        現在的空氣品質（預設）
  tomorrow   明天的環境部預報與模型預測
  hourly     每小時 AQI（--hours，預設 24，最多 1440）
  accuracy   預報準確度統計（--days，預設 30；--basis daily|max|mean）
  status     看板的資料筆數與最近一次抓取

選項：
  --json            印出 JSON
  --base-url <url>  看板網址（預設 ${DEFAULT_BASE_URL}）
  -h, --help        顯示說明
  -v, --version     顯示版本`;

// Node 預設每個位址只等 250 毫秒就換下一個；IPv6 不通的網路上，IPv4 稍慢一點就會整個 ETIMEDOUT
net.setDefaultAutoSelectFamilyAttemptTimeout?.(1000);

async function main() {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      json: { type: 'boolean' },
      'base-url': { type: 'string' },
      hours: { type: 'string' },
      days: { type: 'string' },
      basis: { type: 'string' },
      help: { type: 'boolean', short: 'h' },
      version: { type: 'boolean', short: 'v' },
    },
  });

  if (values.help) return console.log(HELP);
  if (values.version) {
    const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    return console.log(pkg.version);
  }

  const client = new KinmenAqi({ baseUrl: values['base-url'] });
  const commands = {
    now: async () => [await client.now(), formatNow],
    tomorrow: async () => [await client.tomorrow(), formatTomorrow],
    hourly: async () => [await client.hourly({ hours: int(values.hours, 24) }), formatHourly],
    accuracy: async () => [await client.daily({ days: int(values.days, 30), basis: values.basis }), formatAccuracy],
    status: async () => [await client.status(), formatStatus],
  };

  const name = positionals[0] ?? 'now';
  if (positionals.length > 1 || !Object.hasOwn(commands, name)) {
    throw new Error(`沒有這個指令：${positionals.join(' ')}\n\n${HELP}`);
  }
  const [data, format] = await commands[name]();
  console.log(values.json ? JSON.stringify(data, null, 2) : format(data));
}

// 沒給就用預設值；給了但不是整數時原樣交給 client，由它丟出範圍錯誤
function int(v, dflt) {
  if (v === undefined) return dflt;
  return /^\d+$/.test(v) ? Number(v) : v;
}

main().catch((err) => {
  console.error(err.message);
  process.exitCode = 1;
});
