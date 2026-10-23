// 前端的純函式（不碰 DOM、不碰網路），方便用 node --test 做單元測試。

const FILTERS = ['all', 'active', 'completed'];

/** 把篩選條件轉成 API 網址；不認得的值一律當成 all */
export function todosUrl(filter) {
  return FILTERS.includes(filter) && filter !== 'all'
    ? `/api/todos?filter=${filter}`
    : '/api/todos';
}

/** 底部的統計文字，例如「2 項未完成，共 5 項」 */
export function summaryText(stats) {
  if (stats.total === 0) return '';
  return `${stats.active} 項未完成，共 ${stats.total} 項`;
}

/** 從錯誤回應取出要顯示的訊息 */
export async function errorMessage(response) {
  try {
    const body = await response.json();
    if (body && typeof body.error === 'string') return body.error;
  } catch {
    // 回應不是 JSON，用下面的預設訊息
  }
  return `發生錯誤（HTTP ${response.status}）`;
}
