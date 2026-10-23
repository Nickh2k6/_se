# 測試方式

本專案分成兩種測試層級：

1. **各模組獨立測試** — 每個模組都有 `__main__` 區塊，可直接執行，不需外網。
2. **整合測試** — 透過 `python main.py` 對外連線，使用 httpbin.org 驗證完整流程。

## 1. 模組單元測試

不需要網路即可執行：

```bash
# URL 解析測試
python url_parser.py

# 函式庫層級測試（字面執行）
python http_request.py

# HTTP 回應解析測試（含 chunked、204 等）
python http_response.py
```

一次跑完所有模組測試：

```bash
python url_parser.py && python http_request.py && python http_response.py
```

> 注意：`socket_client.py` 的 `__main__` 區塊會實際連到 httpbin.org，需要網路。

## 2. 整合測試（直接跑 mycurl）

所有測試都以 httpbin.org 為目標，需要網路連線。

### 2.1 基本 GET

```bash
python main.py http://httpbin.org/get
```

預期：印出包含 `args`、`headers`、`url` 的 JSON body，status 200。

### 2.2 verbose 模式

```bash
python main.py -v http://httpbin.org/get
```

預期：stderr 印出請求與回應的詳細內容（request line、headers、HTTP 狀態行）。

### 2.3 HTTPS

```bash
python main.py https://httpbin.org/get
```

預期：與 2.1 相同結果，透過 TLS 傳輸。

### 2.4 自訂 header

```bash
python main.py -H "X-Custom-Header: myvalue" http://httpbin.org/headers
```

預期：回應 JSON 的 `headers.X-Custom-Header` 為 `myvalue`。

### 2.5 POST 表單資料

```bash
python main.py -d "name=alice&age=20" http://httpbin.org/post
```

預期：`method` 為 `POST`，`form` 含 `name` 與 `age`。

### 2.6 GET 帶資料自動轉 POST

```bash
python main.py -X GET -d "a=1" http://httpbin.org/post
```

預期：因 body 存在，實際送出為 `POST`，回應 `method` 顯示 `POST`。

### 2.7 Basic Auth（成功）

```bash
python main.py --user admin:secret http://httpbin.org/basic-auth/admin/secret
```

預期：`"authenticated": true`。

### 2.8 Basic Auth（失敗）

```bash
python main.py --user wrong:wrong http://httpbin.org/basic-auth/admin/secret
```

預期：status 401。

### 2.9 追蹤 redirect

```bash
python main.py -L http://httpbin.org/redirect/5
```

預期：最終 status 200，並傳回 `/get` 的內容。

### 2.10 不追蹤 redirect

```bash
python main.py http://httpbin.org/redirect/1
```

預期：status 302，直接輸出 redirect 回應（不會跟隨）。

### 2.11 輸出到檔案

```bash
python main.py -o /tmp/result.html http://httpbin.org/html
```

預期：檔案內容為 HTML，且 stderr 出現進度條。

### 2.12 timeout

```bash
python main.py -m 2 http://httpbin.org/delay/5
```

預期：約 2 秒後報 `TimeoutError`，exit code 28。

### 2.13 無效 URL

```bash
python main.py ftp://example.com
```

預期：報「Unsupported scheme」，exit code 3。

### 2.14 連線被拒

```bash
python main.py http://localhost:1
```

預期：連線失敗，exit code 7。

### 2.15 chunked 回應

httpbin.org 預設回應大多為 `Content-Length`，可改用 `https://httpbin.org/stream/20`：

```bash
python main.py "https://httpbin.org/stream/20"
```

預期：印出多行 JSON（chunked transfer-encoding 解碼成功）。

## 3. 快速回歸腳本

可用一行指令跑完整迴歸（Linux / macOS）：

```bash
cd /path/to/homework

python main.py http://httpbin.org/get && \
python main.py https://httpbin.org/get && \
python main.py -H "X-Test: 1" http://httpbin.org/headers && \
python main.py -d "name=alice" http://httpbin.org/post && \
python main.py --user admin:secret http://httpbin.org/basic-auth/admin/secret && \
python main.py -L http://httpbin.org/redirect/2 && \
python main.py -o /tmp/result.html http://httpbin.org/html && \
echo "ALL PASSED"
```

最後印出 `ALL PASSED` 代表所有 case 通過。

## 4. Exit code 檢查

```bash
python main.py -m 2 http://httpbin.org/delay/5; echo "exit=$?"
```

預期：`exit=28`。各 code 的意義見 `README.md` 的「錯誤處理」。