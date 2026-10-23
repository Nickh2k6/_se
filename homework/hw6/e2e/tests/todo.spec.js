// E2E 測試：用無頭 Chromium 打開真正的網頁，模擬使用者點擊、輸入，
// 驗證「瀏覽器 → 前端 JS → HTTP → Rust 伺服器 → 畫面」整條路徑。
import { test, expect } from '@playwright/test';

// 每個測試開始前，透過 API 把伺服器上的資料清空，讓測試彼此獨立
test.beforeEach(async ({ request, page }) => {
  const todos = await (await request.get('/api/todos')).json();
  for (const t of todos) {
    await request.delete(`/api/todos/${t.id}`);
  }
  await page.goto('/');
});

async function addTodo(page, title) {
  await page.getByTestId('new-todo').fill(title);
  await page.getByTestId('new-todo').press('Enter');
  await expect(page.getByTestId('todo-title').filter({ hasText: title })).toBeVisible();
}

const items = (page) => page.getByTestId('todo-item');
const titles = (page) => page.getByTestId('todo-title');

test('首頁載入：顯示標題與空清單提示', async ({ page }) => {
  await expect(page).toHaveTitle(/Todo/);
  await expect(page.getByRole('heading', { name: '待辦清單' })).toBeVisible();
  await expect(page.getByTestId('empty')).toBeVisible();
  await expect(items(page)).toHaveCount(0);
});

test('新增待辦：按 Enter 或按鈕都可以，輸入框會清空', async ({ page }) => {
  await addTodo(page, '買牛奶');

  await page.getByTestId('new-todo').fill('寫作業');
  await page.getByTestId('add-button').click();

  await expect(titles(page)).toHaveText(['買牛奶', '寫作業']);
  await expect(page.getByTestId('new-todo')).toHaveValue('');
  await expect(page.getByTestId('empty')).toBeHidden();
  await expect(page.getByTestId('summary')).toHaveText('2 項未完成，共 2 項');
});

test('空白標題：顯示伺服器回傳的錯誤訊息，清單不變', async ({ page }) => {
  await page.getByTestId('new-todo').fill('   ');
  await page.getByTestId('add-button').click();

  await expect(page.getByTestId('error')).toHaveText('標題不可為空白');
  await expect(items(page)).toHaveCount(0);

  // 接著正常新增，錯誤訊息應該消失
  await addTodo(page, '運動');
  await expect(page.getByTestId('error')).toBeHidden();
});

test('勾選完成：畫面加上刪除線，統計更新', async ({ page }) => {
  await addTodo(page, '買牛奶');
  await addTodo(page, '寫作業');

  const first = items(page).first();
  await first.getByTestId('toggle').check();

  await expect(first).toHaveClass(/completed/);
  await expect(page.getByTestId('summary')).toHaveText('1 項未完成，共 2 項');

  await first.getByTestId('toggle').uncheck();
  await expect(first).not.toHaveClass(/completed/);
  await expect(page.getByTestId('summary')).toHaveText('2 項未完成，共 2 項');
});

test('篩選：全部 / 未完成 / 已完成', async ({ page }) => {
  for (const t of ['A', 'B', 'C']) await addTodo(page, t);
  await items(page).nth(1).getByTestId('toggle').check();
  await expect(items(page).nth(1)).toHaveClass(/completed/);

  const filters = page.getByTestId('filters');
  await filters.getByRole('button', { name: '未完成' }).click();
  await expect(titles(page)).toHaveText(['A', 'C']);

  await filters.getByRole('button', { name: '已完成' }).click();
  await expect(titles(page)).toHaveText(['B']);

  await filters.getByRole('button', { name: '全部' }).click();
  await expect(titles(page)).toHaveText(['A', 'B', 'C']);
});

test('編輯：雙擊標題修改，按 Enter 儲存、按 Esc 取消', async ({ page }) => {
  await addTodo(page, '買牛奶');

  await titles(page).first().dblclick();
  const edit = page.getByTestId('edit');
  await edit.fill('買豆漿');
  await edit.press('Enter');
  await expect(titles(page)).toHaveText(['買豆漿']);

  await titles(page).first().dblclick();
  await page.getByTestId('edit').fill('不要存這個');
  await page.getByTestId('edit').press('Escape');
  await expect(titles(page)).toHaveText(['買豆漿']);
});

test('刪除：項目從畫面消失，最後顯示空清單', async ({ page }) => {
  await addTodo(page, '買牛奶');
  await addTodo(page, '寫作業');

  await items(page).first().getByTestId('delete').click();
  await expect(titles(page)).toHaveText(['寫作業']);

  await items(page).first().getByTestId('delete').click();
  await expect(items(page)).toHaveCount(0);
  await expect(page.getByTestId('empty')).toBeVisible();
});

test('清除已完成：只有在有已完成項目時才出現按鈕', async ({ page }) => {
  await addTodo(page, 'A');
  await addTodo(page, 'B');
  await expect(page.getByTestId('clear-completed')).toBeHidden();

  await items(page).first().getByTestId('toggle').check();
  await expect(page.getByTestId('clear-completed')).toBeVisible();

  await page.getByTestId('clear-completed').click();
  await expect(titles(page)).toHaveText(['B']);
  await expect(page.getByTestId('clear-completed')).toBeHidden();
});

test('資料存在伺服器：重新整理頁面後資料還在', async ({ page }) => {
  await addTodo(page, '重新整理也不會不見');
  await items(page).first().getByTestId('toggle').check();
  await expect(items(page).first()).toHaveClass(/completed/);

  await page.reload();

  await expect(titles(page)).toHaveText(['重新整理也不會不見']);
  await expect(items(page).first()).toHaveClass(/completed/);
  await expect(items(page).first().getByTestId('toggle')).toBeChecked();
});

test('前端與 API 一致：從 UI 新增的資料，API 也查得到', async ({ page, request }) => {
  await addTodo(page, '同步檢查');
  const todos = await (await request.get('/api/todos')).json();
  expect(todos).toEqual([expect.objectContaining({ title: '同步檢查', completed: false })]);
});
