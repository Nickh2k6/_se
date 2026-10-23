# mycurl

一個用 Python 純標準函式庫實作的 curl 風格 HTTP 客戶端，不含任何第三方套件。支援 HTTP/HTTPS、自訂 header、表單資料、Basic Auth、redirect 追蹤、進度條與 timeout。

## 功能

- HTTP / HTTPS（透過 Python `ssl` 模組）
- 常見 HTTP 方法：GET、POST、PUT 等（用 `-X` 指定）
- 自訂 header（`-H`，可重複使用）
- 請求 body（`-d`，`GET` 帶 body 時自動轉為 `POST`）
- 回應 body 輸出到 stdout 或檔案（`-o`）
- Basic Authentication（`--user user:password` 或 URL 內嵌 `user:pass@host`）
- 追蹤 redirect（`-L`），同 curl 行為：301/302/303 改為 GET
- 回應解析：Content-Length、chunked transfer-encoding、無 body 狀態碼（204/304）
- 進度條顯示（寫入檔案時）
- timeout 控制與 DNS／連線／接收階段錯誤分類

## 檔案結構

| 檔案 | 說明 |
|------|------|
| `main.py` | 程式進入點：命令列參數解析與主流程 |
| `url_parser.py` | URL 解析，輸出 `URLParts` |
| `http_request.py` | 建構 HTTP 請求 |
| `http_response.py` | 解析 HTTP 回應 |
| `socket_client.py` | socket 連線、SSL、傳送與接收封包 |
| `utils.py` | 共用工具（verbose 除錯輸出等） |
| `README.md` | 專案說明 |
| `README-testing.md` | 測試方式說明 |

## 使用方式

```bash
# 基本 GET
python main.py http://httpbin.org/get

# verbose 模式（顯示請求／回應細節）
python main.py -v http://httpbin.org/get

# 自訂方法與 header
python main.py -X POST -H "Accept: application/json" http://httpbin.org/post

# 表單資料（GET 帶 -d 會自動改用 POST）
python main.py -d "name=alice&age=20" http://httpbin.org/post

# 從檔案讀取 body
python main.py -d @payload.json http://httpbin.org/post

# 追蹤 redirect
python main.py -L http://httpbin.org/redirect/5

# 寫入檔案（同時顯示進度條）
python main.py -o result.html http://httpbin.org/html

# Basic Auth
python main.py --user admin:secret http://httpbin.org/basic-auth/admin/secret

# 嵌入 URL 的認證資訊
python main.py http://admin:secret@httpbin.org/basic-auth/admin/secret

# 設定 timeout（秒）
python main.py -m 5 http://httpbin.org/delay/3
```

## 命令列參數

| 參數 | 說明 |
|------|------|
| `urls` | 要抓取的 URL（可多個） |
| `-X, --request` | HTTP 方法，預設 `GET` |
| `-H, --header` | 自訂 header（`NAME:VALUE`，可重複） |
| `-d, --data` | 請求 body（字串或 `@filename`） |
| `-o, --output` | body 寫入檔案 |
| `-v, --verbose` | 詳細輸出 |
| `-L, --location` | 追蹤 redirect |
| `-m, --max-time` | timeout（秒） |
| `--user` | `user:password` Basic Auth |
| `--no-progress` | 停用進度條 |

## 錯誤處理

程式以 exit code 回報錯誤：

| Exit code | 意義 |
|-----------|------|
| `0` | 成功 |
| `3` | URL 或 redirect 相關錯誤 |
| `6` | header / body 檔案格式錯誤 |
| `7` | 連線失敗 |
| `28` | timeout |