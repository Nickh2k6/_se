import { todosUrl, summaryText, errorMessage } from './logic.js';

const form = document.querySelector('#new-todo-form');
const input = document.querySelector('#new-todo');
const errorBox = document.querySelector('#error');
const list = document.querySelector('#todo-list');
const empty = document.querySelector('#empty');
const summary = document.querySelector('#summary');
const filterButtons = document.querySelectorAll('.filters button');
const clearButton = document.querySelector('#clear-completed');

let currentFilter = 'all';

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

/** 呼叫 API；失敗時顯示錯誤並回傳 null */
async function api(method, url, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers['content-type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  if (!res.ok) {
    showError(await errorMessage(res));
    return null;
  }
  showError('');
  return res.status === 204 ? true : res.json();
}

function renderTodo(todo) {
  const li = document.createElement('li');
  li.dataset.testid = 'todo-item';
  li.dataset.id = todo.id;
  li.classList.toggle('completed', todo.completed);

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.checked = todo.completed;
  checkbox.dataset.testid = 'toggle';
  checkbox.addEventListener('change', async () => {
    await api('PATCH', `/api/todos/${todo.id}`, { completed: checkbox.checked });
    refresh();
  });

  const title = document.createElement('span');
  title.className = 'title';
  title.textContent = todo.title;
  title.dataset.testid = 'todo-title';
  title.title = '雙擊可編輯';
  title.addEventListener('dblclick', () => startEdit(li, title, todo));

  const del = document.createElement('button');
  del.type = 'button';
  del.className = 'delete';
  del.textContent = '刪除';
  del.dataset.testid = 'delete';
  del.addEventListener('click', async () => {
    await api('DELETE', `/api/todos/${todo.id}`);
    refresh();
  });

  li.append(checkbox, title, del);
  return li;
}

function startEdit(li, title, todo) {
  const edit = document.createElement('input');
  edit.className = 'edit';
  edit.value = todo.title;
  edit.dataset.testid = 'edit';
  title.replaceWith(edit);
  edit.focus();

  let done = false;
  const finish = async (save) => {
    if (done) return;
    done = true;
    if (save && edit.value !== todo.title) {
      await api('PATCH', `/api/todos/${todo.id}`, { title: edit.value });
    }
    refresh();
  };
  edit.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') finish(true);
    if (e.key === 'Escape') finish(false);
  });
  edit.addEventListener('blur', () => finish(true));
}

async function refresh() {
  const [todos, stats] = await Promise.all([
    fetch(todosUrl(currentFilter)).then((r) => r.json()),
    fetch('/api/stats').then((r) => r.json()),
  ]);
  list.replaceChildren(...todos.map(renderTodo));
  empty.hidden = todos.length > 0;
  summary.textContent = summaryText(stats);
  clearButton.hidden = stats.completed === 0;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const created = await api('POST', '/api/todos', { title: input.value });
  if (created) input.value = '';
  refresh();
});

filterButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    currentFilter = btn.dataset.filter;
    filterButtons.forEach((b) => b.classList.toggle('active', b === btn));
    refresh();
  });
});

clearButton.addEventListener('click', async () => {
  await api('DELETE', '/api/todos/completed');
  refresh();
});

refresh();
