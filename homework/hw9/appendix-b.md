# 附錄 B　常見錯誤與排除

程式出錯時，**先看錯誤訊息的最後一行**，再到這個附錄找對應的狀況。每一項都寫了原因、解決方法，以及書中相關的章節，可以回去複習。

本附錄的分類：

- B.1 除錯的基本步驟
- B.2 API 錯誤（狀態碼）
- B.3 Colab 與套件
- B.4 回答的內容不對勁
- B.5 JSON 解析
- B.6 工具呼叫
- B.7 Agent 迴圈
- B.8 安全與記憶
- B.9 兩個實用的除錯小工具

---

## B.1 除錯的基本步驟

遇到問題時，照這個順序檢查，大部分的問題都能找到原因：

```text
  ① 看錯誤訊息的「最後一行」
       └─ 例外的名稱（KeyError、TypeError……）和訊息，通常已經說明了原因
  ② 確認是哪一層出錯（對照第 11 章的層級圖）
       ├─ 連不上 API？         → B.2、B.3
       ├─ 模型回答怪怪的？      → B.4
       ├─ 程式讀不懂回答？      → B.5
       ├─ 工具執行出錯？        → B.6
       └─ Agent 停不下來？      → B.7
  ③ 把送出去的 messages 印出來看（B.9 的 show_messages()）
       └─ 模型只看得到 messages，它的行為幾乎都能從 messages 找到原因
  ④ 把 USE_MOCK 改成 True 再跑一次
       ├─ mock 也錯 → 問題在「你的程式」
       └─ mock 正常 → 問題在「模型的回應」或「API 設定」
  ⑤ 對照官方文件：https://ai.google.dev/gemini-api/docs
       └─ 模型名稱、SDK 寫法可能已經改了
```

---

## B.2 API 錯誤（狀態碼）

### 400 Bad Request（請求格式錯誤）

| 錯誤訊息裡有 | 原因 | 解決方法 | 相關章節 |
|------------|------|---------|---------|
| `API_KEY_INVALID`、`API key not valid` | 金鑰錯誤、複製時少了字或多了空白 | 回 Google AI Studio 重新複製金鑰，更新 Colab 密鑰 | 第 0、2 章 |
| `Invalid JSON payload`、`Unknown name` | REST 請求的欄位名稱拼錯（例如把 `maxOutputTokens` 寫成 `max_output_tokens`） | REST 用駝峰式，Python SDK 用蛇形 | 第 2 章 |
| `properties: should be non-empty for OBJECT type` | 沒有參數的工具寫了空的 `properties` | 沒有參數就整個省略 `parameters` | 第 6 章 |
| 提到 `function call` / `function response` 數量不對 | 工具請求和工具結果沒有一一對應，或順序錯了 | 先加 assistant（含 `tool_calls`、`raw`），再為**每一張**紙條加一個 `tool` 結果 | 第 6、7 章 |
| 提到 `thought signature` / `signature` | 自己重建了模型的工具請求，弄丟思考簽章 | 把 `response["raw"]` 存進 assistant 訊息，原封不動送回 | 第 6 章 |
| 提到 context / token 數超過上限 | 對話太長，超過上下文長度 | 用 `trim_history()` 只送最近的對話 | 第 3 章 |

### 401 Unauthorized ／ 403 Forbidden（沒有權限）

| 原因 | 解決方法 |
|------|---------|
| 請求**沒有帶**金鑰 | 確認 `headers` 有 `x-goog-api-key`，或 `genai.Client(api_key=api_key)` 有傳入金鑰 |
| 金鑰沒有使用這個 API 的權限（例如在 Google Cloud 設定了限制） | 到 Google AI Studio 檢查金鑰設定，或建立一把新的 |
| 所在地區不支援這個服務 | 查看官方文件的「可用地區」說明 |

> 金鑰**錯誤**時，Gemini 通常回傳 **400**（`API_KEY_INVALID`）；其他家的 API（例如 OpenAI、Anthropic）通常回傳 **401**。看到這兩個狀態碼，第一件事都是檢查金鑰。（第 2 章 2.1 節）

### 404 Not Found（找不到）

| 原因 | 解決方法 |
|------|---------|
| `MODEL_NAME` 拼錯 | 檢查大小寫、連字號，例如 `gemini-3.5-flash-lite` |
| 模型已經停用 | 到官方 Models 頁面查目前的模型名稱，改掉 `MODEL_NAME` 那一行 |
| REST 網址拼錯（例如少了 `:generateContent`） | 對照第 2 章程式 2-1 的 `url` |

### 429 Too Many Requests（請求太多）

| 原因 | 解決方法 |
|------|---------|
| 超過免費額度的「每分鐘請求數」 | 等一分鐘再試；用 B.9 的 `call_with_retry()` 自動等待重試 |
| 超過「每天請求數」 | 隔天再試，或改用 `USE_MOCK = True` 繼續練習 |
| Agent 迴圈或測試迴圈跑太多次 | 減少測試次數；Agent 一題就會呼叫好幾次 API（第 7、8 章） |

### 500 Internal Server Error ／ 503 Service Unavailable（伺服器錯誤）

Google 的伺服器暫時出問題或太忙，**不是你的程式錯了**。等幾秒到幾分鐘再試，或用 B.9 的 `call_with_retry()` 自動重試。

---

## B.3 Colab 與套件

| 錯誤訊息 / 狀況 | 原因 | 解決方法 | 相關章節 |
|---------------|------|---------|---------|
| `SecretNotFoundError` | 密鑰名稱打錯或沒有建立 | 左側 🔑 面板確認名稱是 `GEMINI_API_KEY`（大小寫一樣、沒有空白） | 第 0 章 |
| `NotebookAccessError` | 沒打開密鑰的「筆記本存取權」 | 在 🔑 面板打開那一列的開關 | 第 0 章 |
| `ModuleNotFoundError: No module named 'google.colab'` | 不是在 Colab 執行 | 本書程式請在 Colab 執行 | 第 0 章 |
| `ModuleNotFoundError: No module named 'google.genai'` | 沒安裝 SDK，或執行階段重啟後套件不見了 | 重跑 `!pip install -q -U google-genai` | 第 2 章 |
| `ImportError` / `AttributeError`，提到 `google.genai` 或 `types` | SDK 版本太舊，或剛升級還沒重新啟動 | 重跑 `!pip install -q -U google-genai`，再到選單「執行階段 → 重新啟動工作階段」 | 第 2 章 |
| 程式用了 `import google.generativeai` | 照著舊教學寫，用到**舊版** SDK | 本書一律用 `from google import genai` | 第 0、2 章 |
| `NameError: name 'xxx' is not defined` | 執行階段重啟過，前面的儲存格沒重跑；或跳著執行 | 從最上面開始依序執行，或執行該章的「準備環境」程式（程式 X-0） | 第 0 章 |
| 其他儲存格都不能執行，一直在轉圈 | 有儲存格在等 `input()`（聊天迴圈、人工確認） | 在輸入框輸入 `exit` 或 `n`，或按該儲存格的 ■ 停止 | 第 3、9 章 |
| 時間差了 8 小時 | Colab 使用世界標準時間（UTC） | `datetime.now(ZoneInfo("Asia/Taipei"))` | 第 5 章 |

---

## B.4 回答的內容不對勁

| 狀況 | 原因 | 解決方法 | 相關章節 |
|------|------|---------|---------|
| 同一個問題，每次答案不一樣 | 模型照機率抽字，這是正常的 | 需要穩定時設 `temperature=0` | 第 1、2 章 |
| 調 `temperature` 好像沒有效果 | Gemini 3.6 以後、Gemini 4 系列會忽略 temperature | 本書使用 `gemini-3.5-flash-lite` | 第 2 章 |
| 回答講到一半就斷掉 | 被 `max_output_tokens` 切斷，停止原因是 `MAX_TOKENS` | 調大 `max_output_tokens` | 第 2 章 |
| 回答是空的（`""` 或 `None`） | ① 思考用光了長度上限 ② 被安全機制擋下 ③ 只回傳了工具請求 | ① 調大 `max_output_tokens` ② 檢查停止原因 ③ 檢查 `tool_calls` | 第 2、6 章 |
| 講得頭頭是道，但內容是錯的 | 幻覺：模型只保證「接得順」，不保證「是真的」 | 用工具查真的資料（第 5～7 章）、用 RAG 提供資料（第 10 章）、在 prompt 寫「不知道就說不確定」 | 第 1、4 章 |
| 不知道今天幾號、算錯數學 | 模型沒有時鐘、不會真的計算 | 用 `get_current_time`、`calculator` 工具 | 第 1、5 章 |
| 不記得上一句話 | API 是無狀態的 | 用 `chat_history` / `history` 保存對話 | 第 3、10 章 |
| 沒照 system prompt 的規則回答 | system prompt 只是「強烈的建議」 | 把規則寫得更具體、加上範例；重要的規則要用程式檢查 | 第 4、9 章 |

---

## B.5 JSON 解析

| 錯誤訊息 / 狀況 | 原因 | 解決方法 | 相關章節 |
|---------------|------|---------|---------|
| `json.decoder.JSONDecodeError` | 回答有 `` ```json `` 標記、前後多了文字、被切斷、用了單引號 | 用 `parse_json_reply()` 清理；失敗時用 `ask_json()` 重試；或開啟 JSON 模式 | 第 4 章 |
| `TypeError: string indices must be integers` | 對字串用 `reply["intent"]`，忘了先解析 | 先 `json.loads()` 或 `parse_json_reply()` 變成 dict | 第 4 章 |
| `KeyError: 'day'` 之類 | 模型漏了某個欄位 | 用 `.get("day")` 取值，或先檢查欄位是否齊全 | 第 4 章 |
| `KeyError: 'candidates'` | 請求失敗了，回應是錯誤訊息，不是答案 | 先印出 `response.status_code` 和 `response.json()` 看錯誤內容 | 第 2 章 |
| `KeyError: 'parts'` | 回答被切斷或是空的 | 檢查停止原因；用 `.get()` 一層一層安全取值 | 第 2 章 |
| 中文印出來變成 `金門` | `json.dumps()` 沒加 `ensure_ascii=False` | 加上 `ensure_ascii=False` | 第 2 章 |

---

## B.6 工具呼叫

| 錯誤訊息 / 狀況 | 原因 | 解決方法 | 相關章節 |
|---------------|------|---------|---------|
| 以為模型「執行」了工具 | 誤解工具呼叫的本質 | 模型只會寫紙條，真正執行的永遠是你的 `run_tool()` | 第 5 章 |
| `KeyError: 'get_scheduel'` | 模型拼錯工具名稱，`TOOLS` 找不到 | 使用安全版 `run_tool()`，把「可用的工具清單」告訴模型 | 第 5、8 章 |
| `TypeError: ... got an unexpected keyword argument` | 模型寫錯參數名稱（例如 `date` 而不是 `day`） | 原生版用 JSON Schema 描述參數；安全版 `run_tool()` 把錯誤交還給模型 | 第 6、8 章 |
| `ValueError: day 必須是星期一到星期日` | 模型傳了 `"明天"` | JSON Schema 用 `enum` 限制；工具說明寫「不知道星期幾要先查時間」 | 第 6 章 |
| `ZeroDivisionError` | 算式除以零 | 安全版 `run_tool()` 會把它變成「錯誤：」開頭的文字 | 第 8 章 |
| 模型要求的工具 `run_tool()` 找不到 | `TOOL_DECLARATIONS` 的 `name` 和 `TOOLS` 的 key 不一樣 | 用第 6 章程式 6-1 最後的檢查確認名稱一致 | 第 6 章 |
| 改了工具函式，Agent 還在用舊的 | `TOOLS` 裡存的是舊函式 | 重新定義後要 `TOOLS["名稱"] = 新函式` | 第 8、9 章 |
| 新增的工具，模型都不會用 | 忘了加進 `TOOL_DECLARATIONS`，或 `description` 寫得不清楚 | 加進宣告；說明寫「做什麼、什麼時候一定要用」 | 第 6、10 章 |
| `TypeError: 'NoneType' object is not iterable` | 沒有工具請求時，`response.function_calls` 是 `None` | 寫成 `response.function_calls or []` | 第 6 章 |
| SDK 警告：`there are non-text parts in the response` | 回應有 `function_call` 時還用 `response.text` | 逐一檢查 part（參考 `call_llm_tools()`） | 第 6 章 |
| 平行呼叫只處理了一個工具 | 只處理了 `tool_calls[0]` | 用 for 迴圈處理**每一個**工具請求 | 第 6、7 章 |
| 直接 `eval()` 模型給的字串 | 參數可能有惡意程式碼 | 先檢查內容，並限制 `eval` 能用的功能（參考 `calculator`） | 第 5、9 章 |

---

## B.7 Agent 迴圈

| 狀況 | 原因 | 解決方法 | 相關章節 |
|------|------|---------|---------|
| **無限迴圈**：程式一直跑、停不下來 | 用了 `while True` 卻沒有步數上限 | 一定要有 `max_steps`；按 ■ 停止儲存格 | 第 7、8 章 |
| 一直重複呼叫同一個工具 | 工具結果沒有加進 messages，模型每圈看到的都一樣 | 確認每個結果都 `append` 成 `tool` 訊息 | 第 7 章 |
| 工具一直失敗，Agent 一直重試 | 工具壞了，或錯誤訊息太模糊 | 設 `max_failures`；錯誤訊息寫明「怎麼改」 | 第 8 章 |
| 工具出錯，整個 Agent 當掉 | `run_tool()` 沒有 `try/except` | 使用安全版 `run_tool()` | 第 8 章 |
| 一題花了很多 token | 每一圈都重送整段 messages ＋ 工具宣告 | 設 `token_budget`；用 `AGENT_LOG` 找出花最多的一步 | 第 8 章 |
| 偶爾失敗一次就停止 | 用了「總失敗次數」而不是「連續失敗次數」 | 成功時把計數歸零 | 第 8 章 |
| 問題之間互相干擾 | `messages` 寫在 `run_agent()` 外面，沒有重設 | 在 `run_agent()` 裡面建立 `messages` | 第 7 章 |
| 改了 `call_llm_tools()`，沒有效果 | `llm_tools` 還指向舊的函式 | 重新執行 `llm_tools = mock_llm_tools if USE_MOCK else call_llm_tools` | 第 8 章 |
| 測試完，真的模型變成假的 | 暫時換成 mock 或 `stubborn_llm_tools` 後忘了換回來 | 用 `real_llm_tools` 存起來，測完一定換回去 | 第 7、8 章 |
| `KeyError: 'usage'` | 自己寫的假模型少了 `usage` 欄位 | 所有 `llm_tools` 的回傳格式都要有 `text`、`tool_calls`、`raw`、`usage` | 第 8 章 |
| Agent 沒有印出「思考」 | 模型這一步直接寫了紙條 | 正常現象；`AGENT_PROMPT` 只能鼓勵，不能強迫 | 第 7 章 |

---

## B.8 安全與記憶

| 狀況 | 原因 | 解決方法 | 相關章節 |
|------|------|---------|---------|
| Agent 照著公告、網頁裡的指令做事 | 提示注入 | 危險工具要人工確認；`SYSTEM_PROMPT` 寫明工具結果是資料；用程式限制工具權限 | 第 9 章 |
| 只在 prompt 寫「不要寄給外部信箱」，還是寄出去了 | prompt 不是強制規則 | 限制寫在**工具的程式碼**裡（最小權限） | 第 9 章 |
| 直接按 Enter 就執行了危險動作 | 預設值是「同意」 | 預設拒絕：只有輸入 `y` 才執行 | 第 9 章 |
| 使用者拒絕後，模型一直重試 | 拒絕訊息沒有說「不要再試」 | 回傳「已取消：……不要再嘗試這個動作」 | 第 9 章 |
| 還原課表沒有效果 | `ORIGINAL = FAKE_SCHEDULE` 兩個名字指向同一個 dict | 用 `copy.deepcopy()` | 第 9 章 |
| 傳了 `history=[]`，對話卻沒被記住 | 用 `if history:` 判斷，空 list 被當成「假」 | 改成 `if history is not None` | 第 10 章 |
| 關掉 Colab 再打開，長期記憶不見了 | Colab 的本機檔案會被清除 | 把 `MEMORY_FILE` 改存到 Google 雲端硬碟 | 第 10 章 |
| 讀記憶檔時 `JSONDecodeError` | 檔案內容壞了 | 修正或刪除 `campus_memory.json` | 第 10 章 |
| 搜尋不到明明存在的資料 | 關鍵字搜尋只比對字，不懂意思 | 調整資料寫法、加同義詞，或改用向量搜尋 | 第 10 章 |

---

## B.9 兩個實用的除錯小工具

### 程式 B-1：遇到 429 / 503 時自動等待重試

免費額度很容易遇到 429（請求太多）。這個函式在遇到「等一下就會好」的錯誤時，會**自動等待、重試**，而且每次等待的時間越來越長，這種做法叫**指數退避（exponential backoff）**：第一次等 5 秒、第二次 10 秒、第三次 20 秒⋯⋯避免一直猛敲伺服器。

```python
import time
from google.genai import errors


def call_with_retry(func, *args, max_retries=3, **kwargs):
    """
    呼叫 func(*args, **kwargs)；遇到 429、500、503 時，等一下再重試。
    其他錯誤（例如 400 金鑰錯誤）重試也沒用，直接丟出。
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except errors.APIError as e:
            retryable = e.code in (429, 500, 503)
            if retryable and attempt < max_retries:
                wait = 5 * (2 ** attempt)      # 5、10、20 秒……越等越久
                print(f"[重試] 收到錯誤 {e.code}，{wait} 秒後再試（第 {attempt + 1} 次）")
                time.sleep(wait)
            else:
                raise


# 用法：把原本的呼叫包起來
# 原本：response = llm_tools(messages, temperature=0)
# 改成：response = call_with_retry(llm_tools, messages, temperature=0)
```

**逐段解說：**

- **`from google.genai import errors`**：SDK 的錯誤類別。`errors.APIError` 是所有 API 錯誤的共同類別，它的 `.code` 屬性就是 HTTP 狀態碼。
- **`func, *args, **kwargs`**：
  - `func` 是要呼叫的函式（例如 `llm_tools`），傳的是**函式本身**，不是呼叫結果（第 4 章：函式也是值）。
  - `*args` 收集所有「沒有名字」的參數成一個 tuple，`**kwargs` 收集所有「有名字」的參數成一個 dict（第 8 章的 `**details` 是同樣的道理）。呼叫時再用 `func(*args, **kwargs)` 原封不動地展開傳進去。
- **`retryable`**：只有 429（太多請求）、500、503（伺服器問題）值得重試。400（格式錯誤）、404（模型不存在）重試一百次也不會好，直接 `raise` 丟出。
- **`5 * (2 ** attempt)`**：`2 ** attempt` 是 2 的次方（1、2、4⋯⋯），乘以 5 就是 5、10、20 秒。
- **`time.sleep(wait)`**：讓程式暫停 `wait` 秒。
- **最後一次也失敗**：`attempt < max_retries` 不成立，`raise` 把錯誤丟出去，讓你知道真的不行了。

**預期輸出（遇到 429 時）：**

```text
[重試] 收到錯誤 429，5 秒後再試（第 1 次）
[重試] 收到錯誤 429，10 秒後再試（第 2 次）
```

之後成功的話就會正常回傳結果；如果 3 次重試都失敗，會顯示原本的錯誤訊息。

> 想讓整個 Agent 都自動重試，可以把第 8 章 `run_agent()` 裡的 `response = llm_tools(messages, temperature=0)` 改成 `response = call_with_retry(llm_tools, messages, temperature=0)`。

### 程式 B-2：把 messages 印出來看 —— `show_messages()`

**模型只看得到 messages。** 當 Agent 的行為很奇怪時，把它實際看到的 messages 印出來，通常馬上就知道問題在哪：少了某則訊息、順序錯了、工具結果是空的、system prompt 沒有放進去⋯⋯

這段**不需要 API key**。

```python
def show_messages(messages, max_len=80):
    """把 messages 一則一則印出來；太長的內容只顯示前 max_len 個字"""
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = str(msg.get("content", ""))
        if len(content) > max_len:
            content = content[:max_len] + "……"

        if role == "assistant" and msg.get("tool_calls"):
            calls = ", ".join(c["name"] for c in msg["tool_calls"])
            print(f"{i:>2}. [assistant] 要求工具：{calls}　{content}")
        elif role == "tool":
            print(f"{i:>2}. [tool:{msg['name']}] {content}")
        else:
            print(f"{i:>2}. [{role}] {content}")


# 測試：一段典型的 Agent 對話
test_messages = [
    {"role": "system", "content": "你是「金門大學校園小助理」，服務對象是金門大學的學生。規則：1. 一律使用繁體中文回答。2. 回答簡短，最多三句話。"},
    {"role": "user", "content": "明天有什麼課？"},
    {"role": "assistant", "content": "我需要先知道今天是星期幾。", "tool_calls": [{"name": "get_current_time", "args": {}}], "raw": None},
    {"role": "tool", "name": "get_current_time", "content": "2026-11-27 星期五 21:30"},
    {"role": "assistant", "content": "", "tool_calls": [{"name": "get_schedule", "args": {"day": "星期六"}}], "raw": None},
    {"role": "tool", "name": "get_schedule", "content": '{"day": "星期六", "courses": []}'},
]
show_messages(test_messages)
```

**逐段解說：**

- **`enumerate(messages)`**：一邊跑迴圈，一邊拿到索引 `i`（第幾則）。
- **太長就截斷**：system prompt 和工具結果常常很長，只顯示前 `max_len` 個字，看起來比較清楚。
- **三種格式**：
  - assistant 有 `tool_calls` 時，印出它要求了哪些工具。
  - `tool` 訊息印出是哪個工具的結果。
  - 其他（system、user、一般的 assistant 回答）照原樣印出。
- **`f"{i:>2}"`**：索引靠右對齊、佔 2 格（第 3 章程式 3-4 介紹過）。

**預期輸出：**

```text
 0. [system] 你是「金門大學校園小助理」，服務對象是金門大學的學生。規則：1. 一律使用繁體中文回答。2. 回答簡短，最多三句話。
 1. [user] 明天有什麼課？
 2. [assistant] 要求工具：get_current_time　我需要先知道今天是星期幾。
 3. [tool:get_current_time] 2026-11-27 星期五 21:30
 4. [assistant] 要求工具：get_schedule　
 5. [tool:get_schedule] {"day": "星期六", "courses": []}
```

**怎麼用在 Agent 裡？** 在第 8 章 `run_agent()` 的 `response = llm_tools(...)` 這一行**前面**，暫時加上一行 `show_messages(messages)`，就能看到每一圈模型實際讀到了什麼。除錯完記得刪掉。

**用這個輸出可以檢查：**

- 第 0 則是不是 system？內容對不對（有沒有長期記憶、安全規則）？
- 每一個「要求工具」的 assistant 後面，是不是都接著對應數量的 tool 結果？
- tool 結果是不是空的、是不是「錯誤：」開頭？
- 有沒有同樣的工具請求重複出現（Agent 在繞圈圈）？
