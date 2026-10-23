# hw6：網站應用程式的三種測試

做一個「待辦清單（Todo）」網站，後端用 **Rust（axum）**，前端用純 HTML/JS，然後幫它寫三層測試：

| 層級 | 測什麼 | 工具 | 檔案 | 數量 |
|---|---|---|---|---|
| 1. 單元測試 | 後端商業邏輯（一個函式、一個方法） | Rust 內建 `#[test]` | [server/src/todo.rs](server/src/todo.rs) | 15 |
| 1. 單元測試（選做） | 前端純函式 | Node 內建 `node:test` | [client/test/logic.test.js](client/test/logic.test.js) | 6 |
| 2. 系統測試 | Web API（真的開伺服器、真的送 HTTP） | `cargo test` + `reqwest` | [server/tests/api_test.rs](server/tests/api_test.rs) | 15 |
| 3. E2E 測試 | 從使用者角度操作整個網站 | Playwright（無頭 Chromium） | [e2e/tests/todo.spec.js](e2e/tests/todo.spec.js) | 10 |

![網站畫面](screenshot.png)

## 專案結構

```
hw6/
├── server/                 Rust 後端
│   ├── src/todo.rs         商業邏輯：TodoStore、標題驗證 ← 單元測試寫在檔案最下面
│   ├── src/lib.rs          HTTP 路由（REST API）+ 提供 client/ 靜態檔
│   ├── src/main.rs         程式進入點（PORT 環境變數，預設 3000）
│   └── tests/api_test.rs   系統測試（Web API）
├── client/                 前端（由 Rust 伺服器直接提供）
│   ├── index.html / style.css / app.js
│   ├── logic.js            不碰 DOM 的純函式，方便單元測試
│   └── test/logic.test.js  前端單元測試
└── e2e/                    Playwright E2E 測試
    ├── playwright.config.js
    └── tests/todo.spec.js
```

## 網站功能與 API

功能：新增、勾選完成、雙擊編輯、刪除、篩選（全部 / 未完成 / 已完成）、清除已完成、底部統計。資料存在伺服器記憶體中（重開伺服器會清空）。

| 方法 | 路徑 | 說明 | 成功 | 失敗 |
|---|---|---|---|---|
| GET | `/api/health` | 健康檢查 | 200 `{"status":"ok"}` | |
| GET | `/api/todos?filter=all\|active\|completed` | 列表 | 200 | 400（filter 值不對） |
| POST | `/api/todos` `{"title"}` | 新增 | 201 | 400（空白 / 超過 100 字）、422（缺欄位）、415（不是 JSON） |
| GET | `/api/todos/{id}` | 取得一筆 | 200 | 404、400（id 不是數字） |
| PATCH | `/api/todos/{id}` `{"title"?, "completed"?}` | 部分更新 | 200 | 400、404 |
| DELETE | `/api/todos/{id}` | 刪除 | 204 | 404 |
| DELETE | `/api/todos/completed` | 清除已完成 | 200 `{"removed":n}` | |
| GET | `/api/stats` | 統計 | 200 `{"total","active","completed"}` | |

錯誤一律回 `{"error": "訊息"}`，前端會直接把這個訊息顯示給使用者。

## 環境需求

- Rust（`cargo`）
- Node.js 18 以上（我用 v24.11.1）

### 啟動網站

```bash
cd server
cargo run
```

打開 http://127.0.0.1:3000 。

---

## 1. 單元測試（Unit Test）

### 概念

單元測試只測「一小塊程式」，不開網路、不碰瀏覽器，所以非常快（15 個測試 0.00 秒）。
為了讓邏輯好測，我把程式拆成兩層：

- `todo.rs`：純資料結構 `TodoStore` 和 `validate_title()`，完全不知道 HTTP 的存在 → **單元測試測這層**
- `lib.rs`：只負責把 HTTP 請求轉成對 `TodoStore` 的呼叫 → 交給系統測試

Rust 的慣例是把單元測試寫在同一個檔案的 `#[cfg(test)] mod tests` 裡，這樣可以測到私有的東西，正式編譯時也不會被包進去。

### 測了什麼（server/src/todo.rs）

| 測試 | 驗證的行為 |
|---|---|
| `validate_title_trims_whitespace` | 標題前後空白會被去掉 |
| `validate_title_rejects_empty_and_blank` | 空字串、只有空白/tab/換行 → `EmptyTitle` |
| `validate_title_length_boundary_counts_chars_not_bytes` | **邊界值**：剛好 100 字可以、101 字不行；而且中文 1 字算 1 個（不是 3 bytes） |
| `add_assigns_incrementing_ids_and_starts_incomplete` | id 從 1 開始遞增，新項目預設未完成 |
| `add_invalid_title_does_not_consume_id` | 新增失敗不會吃掉 id |
| `ids_are_not_reused_after_remove` | 刪除後 id 不會被重複使用 |
| `list_filters_by_status` | 三種篩選結果正確且保持順序 |
| `filter_deserializes_from_lowercase_string` | `"completed"` 能轉成 `Filter::Completed`，不認得的值會失敗 |
| `update_changes_only_given_fields` | PATCH 只改有給的欄位 |
| `update_with_invalid_title_leaves_todo_unchanged` | 標題不合法時**整筆都不改**（completed 也不會被改到） |
| `update_missing_id_returns_not_found` | 改不存在的 id → `NotFound` |
| `remove_deletes_only_that_todo` | 只刪那一筆；重複刪 → `NotFound` |
| `clear_completed_removes_completed_and_returns_count` | 回傳刪掉幾筆；沒東西可刪回 0 |
| `stats_counts_each_status` | 空的與有資料時的統計 |
| `error_messages_are_human_readable` | 錯誤訊息內容 |

測試資料用 `sample_store()` 這個小工具函式準備（三筆資料、第 2 筆已完成），每個測試各自建一份，互不影響。

### 怎麼跑

```bash
cd server
cargo test --lib
```

### 結果

```
running 15 tests
test todo::tests::add_assigns_incrementing_ids_and_starts_incomplete ... ok
test todo::tests::update_changes_only_given_fields ... ok
test todo::tests::remove_deletes_only_that_todo ... ok
test todo::tests::add_invalid_title_does_not_consume_id ... ok
test todo::tests::stats_counts_each_status ... ok
test todo::tests::clear_completed_removes_completed_and_returns_count ... ok
test todo::tests::error_messages_are_human_readable ... ok
test todo::tests::list_filters_by_status ... ok
test todo::tests::ids_are_not_reused_after_remove ... ok
test todo::tests::validate_title_trims_whitespace ... ok
test todo::tests::validate_title_rejects_empty_and_blank ... ok
test todo::tests::filter_deserializes_from_lowercase_string ... ok
test todo::tests::update_missing_id_returns_not_found ... ok
test todo::tests::update_with_invalid_title_leaves_todo_unchanged ... ok
test todo::tests::validate_title_length_boundary_counts_chars_not_bytes ... ok

test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

### 前端單元測試（選做）

前端把「不碰畫面」的邏輯抽到 [client/logic.js](client/logic.js)（組 API 網址、統計文字、解析錯誤訊息），用 Node 內建的測試框架測，不用安裝任何套件：

```bash
cd client
npm test
```

```
✔ todosUrl：all 不加參數，其他篩選加 ?filter= (0.5415ms)
✔ todosUrl：不認得的值當成 all (0.086ms)
✔ summaryText：沒有資料時是空字串 (0.7333ms)
✔ summaryText：顯示未完成與總數 (0.0868ms)
✔ errorMessage：讀出伺服器回傳的 error 欄位 (21.5045ms)
✔ errorMessage：回應不是 JSON 時用預設訊息 (0.5813ms)
ℹ tests 6
ℹ pass 6
ℹ fail 0
```

---

## 2. 系統測試（Web API 測試）

### 概念

系統測試把後端當成一個**黑盒子**：不呼叫內部函式，而是像真的客戶端一樣送 HTTP 請求，只看「狀態碼、標頭、JSON 內容」對不對。這樣能抓到單元測試抓不到的問題，例如路由寫錯、狀態碼錯、JSON 欄位名稱錯、請求格式錯誤時怎麼回應。

做法（[server/tests/api_test.rs](server/tests/api_test.rs)）：

1. 每個測試呼叫 `TestServer::start()`，在 `127.0.0.1:0`（讓作業系統挑一個空的 port）啟動**真正的 HTTP 伺服器**
2. 用 `reqwest`（Rust 的 HTTP 客戶端）送請求
3. 檢查回應

因為每個測試都有自己的一台伺服器、自己的資料，所以 15 個測試可以**平行**執行而不互相干擾。

Rust 的慣例是：放在 `tests/` 資料夾的檔案是「整合測試」，只能用 crate 的公開 API（這裡只有 `todo_server::app()`），剛好符合黑盒子測試的精神。

### 測了什麼

| 測試 | 請求 | 預期 |
|---|---|---|
| `health_check_returns_ok` | `GET /api/health` | 200 `{"status":"ok"}` |
| `list_is_empty_on_fresh_server` | `GET /api/todos` | 200 `[]` |
| `create_returns_201_with_new_todo_and_json_content_type` | `POST` 標題前後有空白 | 201、`content-type: application/json`、標題被 trim |
| `create_with_blank_title_returns_400_and_error_message` | `POST {"title":"   "}` | 400、`error` 是「標題不可為空白」 |
| `create_with_too_long_title_returns_400` | 101 字標題 | 400 |
| `create_with_malformed_body_is_rejected` | 缺欄位 / 壞 JSON / 沒 content-type | 422 / 400 / 415 |
| `get_single_todo_and_404_for_missing` | `GET /api/todos/1`、`/999` | 200、404 |
| `non_numeric_id_returns_400` | `GET /api/todos/abc` | 400 |
| `patch_updates_fields_and_persists` | `PATCH` 後再 `GET` | 改動真的存進去了 |
| `patch_errors` | 空標題 / 不存在的 id | 400 / 404 |
| `delete_returns_204_then_404` | 刪兩次 | 第一次 204（無 body），第二次 404 |
| `filter_query_and_stats` | `?filter=active`、`?filter=completed`、`/api/stats`、`?filter=done` | 篩選正確、統計正確、不合法的 filter 回 400 |
| `clear_completed_endpoint` | `DELETE /api/todos/completed` | `{"removed":2}`，只剩未完成的 |
| `wrong_method_returns_405` | `PUT /api/todos` | 405 |
| `serves_frontend_static_files` | `GET /`、`/app.js`、不存在的檔案 | 前端檔案有正確提供、`text/html`、404 |

### 怎麼跑

```bash
cd server
cargo test --test api_test
```

（直接 `cargo test` 會把單元測試和系統測試一起跑。）

### 結果

```
running 15 tests
test wrong_method_returns_405 ... ok
test list_is_empty_on_fresh_server ... ok
test health_check_returns_ok ... ok
test non_numeric_id_returns_400 ... ok
test create_with_too_long_title_returns_400 ... ok
test create_returns_201_with_new_todo_and_json_content_type ... ok
test create_with_blank_title_returns_400_and_error_message ... ok
test serves_frontend_static_files ... ok
test create_with_malformed_body_is_rejected ... ok
test patch_errors ... ok
test get_single_todo_and_404_for_missing ... ok
test delete_returns_204_then_404 ... ok
test patch_updates_fields_and_persists ... ok
test clear_completed_endpoint ... ok
test filter_query_and_stats ... ok

test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s
```

---

## 3. E2E 測試（Playwright 無頭瀏覽器）

### 概念

E2E（End-to-End，端對端）測試站在**使用者**的角度：打開真的瀏覽器、在輸入框打字、按按鈕、看畫面上出現什麼。它會走過整條路徑：

```
Playwright ──控制──► 無頭 Chromium ──► app.js ──HTTP──► Rust 伺服器 ──► 回應 ──► 畫面更新
```

「無頭（headless）」的意思是瀏覽器在背景執行、不開視窗，所以可以在沒有螢幕的 CI 機器上跑。

### 設定重點（[e2e/playwright.config.js](e2e/playwright.config.js)）

- **`webServer`**：跑測試前，Playwright 會自動執行 `cargo run` 啟動 Rust 伺服器（port 3100），並等 `/api/health` 回 200 才開始測，測完自動關掉。不需要手動開伺服器。
- **`workers: 1`**：所有測試共用同一台伺服器，所以一次只跑一個，避免互相影響。
- **`beforeEach`**：每個測試開始前，先用 Playwright 的 `request` 呼叫 API 把資料全部刪掉，再打開首頁 → 每個測試都從空清單開始。
- 前端元素都加了 `data-testid`，測試用 `page.getByTestId()` 找元素，就算之後改了 CSS 或文字，測試也不容易壞。
- 失敗時自動留下**截圖**和 **trace**（可以一步一步回放），方便除錯。

### 測了什麼

| # | 測試 | 使用者操作 → 預期畫面 |
|---|---|---|
| 1 | 首頁載入 | 標題「待辦清單」、顯示「目前沒有待辦事項」 |
| 2 | 新增待辦 | 按 Enter 和按「新增」都能新增；輸入框清空；統計顯示「2 項未完成，共 2 項」 |
| 3 | 空白標題 | 顯示**伺服器回傳**的「標題不可為空白」；之後正常新增，錯誤訊息消失 |
| 4 | 勾選完成 | 出現刪除線（`completed` class）；取消勾選後恢復；統計跟著變 |
| 5 | 篩選 | 「未完成」只剩 A、C；「已完成」只剩 B；「全部」三個都在 |
| 6 | 編輯 | 雙擊標題 → 改字 → Enter 儲存；再雙擊 → 改字 → Esc 取消不存 |
| 7 | 刪除 | 一個一個刪，最後顯示空清單提示 |
| 8 | 清除已完成 | 沒有已完成時按鈕隱藏；勾選後出現；按下後只剩未完成的 |
| 9 | 重新整理 | `page.reload()` 後資料和勾選狀態都還在（證明真的存在伺服器） |
| 10 | 前端與 API 一致 | 從畫面新增後，用 API 查也查得到同一筆資料 |

### 怎麼跑

```bash
cd e2e
npm install
npx playwright install chromium
npx playwright test
```

其他用法：

```bash
npx playwright test --headed
```

（開出瀏覽器視窗，看得到它自己在點）

```bash
npx playwright show-report
```

（打開 HTML 測試報告）

### 結果

```
[WebServer]    Finished `dev` profile [unoptimized + debuginfo] target(s) in 16.27s
[WebServer]     Running `...\debug\todo_server.exe`
[WebServer] Todo server listening on http://127.0.0.1:3100

Running 10 tests using 1 worker

  ok  1 [chromium] › tests\todo.spec.js:23:1 › 首頁載入：顯示標題與空清單提示 (2.0s)
  ok  2 [chromium] › tests\todo.spec.js:30:1 › 新增待辦：按 Enter 或按鈕都可以，輸入框會清空 (459ms)
  ok  3 [chromium] › tests\todo.spec.js:42:1 › 空白標題：顯示伺服器回傳的錯誤訊息，清單不變 (439ms)
  ok  4 [chromium] › tests\todo.spec.js:54:1 › 勾選完成：畫面加上刪除線，統計更新 (610ms)
  ok  5 [chromium] › tests\todo.spec.js:69:1 › 篩選：全部 / 未完成 / 已完成 (863ms)
  ok  6 [chromium] › tests\todo.spec.js:85:1 › 編輯：雙擊標題修改，按 Enter 儲存、按 Esc 取消 (471ms)
  ok  7 [chromium] › tests\todo.spec.js:100:1 › 刪除：項目從畫面消失，最後顯示空清單 (599ms)
  ok  8 [chromium] › tests\todo.spec.js:112:1 › 清除已完成：只有在有已完成項目時才出現按鈕 (578ms)
  ok  9 [chromium] › tests\todo.spec.js:125:1 › 資料存在伺服器：重新整理頁面後資料還在 (450ms)
  ok 10 [chromium] › tests\todo.spec.js:137:1 › 前端與 API 一致：從 UI 新增的資料，API 也查得到 (259ms)

  10 passed (25.5s)
```

---

## 測試過程紀錄

### 1. 先寫後端邏輯與單元測試

先寫 `todo.rs` 和它的單元測試，`cargo test --lib` 15 個全過。

### 2. 系統測試抓到「前端還沒寫」

接著寫 API 和系統測試。第一次跑時 14 過 1 失敗：

```
---- serves_frontend_static_files stdout ----
thread 'serves_frontend_static_files' panicked at tests\api_test.rs:301:5:
assertion `left == right` failed
  left: 404
 right: 200

test result: FAILED. 14 passed; 1 failed
```

原因是當時 `client/` 資料夾還是空的，`GET /` 找不到 `index.html`。這也是一種「先寫測試，再寫實作」的流程：寫完前端後再跑，15 個全過。

### 3. 寫前端與 E2E 測試

寫完前端後跑 Playwright，10 個全過。

### 4. 驗證測試真的有用：故意把程式改壞

測試全綠不代表測試有效 — 也可能是測試什麼都沒檢查。所以我**故意弄一個 bug**：把 `validate_title` 裡的 `raw.trim()` 改成 `raw`（不去掉空白），再跑一次 `cargo test`：

```
test todo::tests::add_invalid_title_does_not_consume_id ... FAILED
test todo::tests::update_with_invalid_title_leaves_todo_unchanged ... FAILED
test todo::tests::validate_title_trims_whitespace ... FAILED
test todo::tests::validate_title_rejects_empty_and_blank ... FAILED
test result: FAILED. 11 passed; 4 failed            ← 單元測試

test create_with_blank_title_returns_400_and_error_message ... FAILED
test create_returns_201_with_new_todo_and_json_content_type ... FAILED
test result: FAILED. 13 passed; 2 failed            ← 系統測試
```

單元測試和系統測試都抓到了這個 bug（E2E 的「空白標題」測試也會抓到）。改回來之後又全部通過。

### 5. 環境問題（Windows）

在我的電腦上遇到兩個跟程式無關的問題，記錄下來：

1. **`link.exe not found`**：Rust 預設的 `msvc` 工具鏈需要 Visual Studio 的「使用 C++ 的桌面開發」元件，我的 VS 2022 沒有裝。因為電腦上已經有 MSYS2 的 gcc，所以改用 GNU 工具鏈：
   ```bash
   rustup toolchain install stable-x86_64-pc-windows-gnu
   ```
   之後在 PowerShell 設定好環境變數再跑（只影響這個視窗）：
   ```powershell
   $env:RUSTUP_TOOLCHAIN = "stable-x86_64-pc-windows-gnu"; $env:PATH = "C:\msys64\ucrt64\bin;$env:PATH"
   ```
   另外在 Git Bash 裡會被 `/usr/bin/link`（Unix 的 link 指令）搶走，要用 PowerShell 跑 `cargo`。
2. **路徑太長**：專案放在很深的資料夾時，編譯會出現「系統找不到指定的路徑」，把編譯輸出移到短路徑就好：
   ```powershell
   $env:CARGO_TARGET_DIR = "$env:TEMP\hw6t"
   ```

裝好 Visual Studio C++ 元件、或專案路徑不深的電腦不需要這些設定。

## 三種測試的比較

| | 單元測試 | 系統測試（API） | E2E 測試 |
|---|---|---|---|
| 測試對象 | 一個函式 / 一個 struct | 整個後端（透過 HTTP） | 整個網站（前端 + 後端） |
| 觀點 | 開發者（白箱） | API 使用者（黑箱） | 終端使用者（黑箱） |
| 速度 | 最快（< 0.01 秒） | 快（0.02 秒） | 最慢（約 6 秒，不含編譯） |
| 失敗時好不好找原因 | 最好找，直接指到哪個函式 | 知道是哪個 API | 只知道「畫面不對」，要看 trace |
| 能抓到的問題 | 邏輯錯誤、邊界值 | 路由、狀態碼、JSON 格式、輸入驗證 | 前後端串接、DOM 操作、使用者流程 |
| 數量 | 最多 | 中等 | 最少（只測重要流程） |

這就是「測試金字塔」：底層的單元測試又快又多，越往上越慢、越貴，所以數量越少，但覆蓋的範圍越完整。
