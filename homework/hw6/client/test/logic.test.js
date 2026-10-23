// 前端單元測試（選做）：用 Node 內建的 node:test，不需要安裝任何套件。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { todosUrl, summaryText, errorMessage } from '../logic.js';

test('todosUrl：all 不加參數，其他篩選加 ?filter=', () => {
  assert.equal(todosUrl('all'), '/api/todos');
  assert.equal(todosUrl('active'), '/api/todos?filter=active');
  assert.equal(todosUrl('completed'), '/api/todos?filter=completed');
});

test('todosUrl：不認得的值當成 all', () => {
  assert.equal(todosUrl('done'), '/api/todos');
  assert.equal(todosUrl(undefined), '/api/todos');
});

test('summaryText：沒有資料時是空字串', () => {
  assert.equal(summaryText({ total: 0, active: 0, completed: 0 }), '');
});

test('summaryText：顯示未完成與總數', () => {
  assert.equal(summaryText({ total: 5, active: 2, completed: 3 }), '2 項未完成，共 5 項');
});

test('errorMessage：讀出伺服器回傳的 error 欄位', async () => {
  const res = new Response(JSON.stringify({ error: '標題不可為空白' }), { status: 400 });
  assert.equal(await errorMessage(res), '標題不可為空白');
});

test('errorMessage：回應不是 JSON 時用預設訊息', async () => {
  const res = new Response('oops', { status: 500 });
  assert.equal(await errorMessage(res), '發生錯誤（HTTP 500）');
});
