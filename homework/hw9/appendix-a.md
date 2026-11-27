# 附錄 A　名詞小辭典

本附錄收錄全書出現的專有名詞，**依照第一次出現的章節排列**。每個名詞附上英文原文、一句白話解釋，以及第一次出現的位置，方便你回頭複習。

讀到一半忘記某個名詞的意思時，可以用瀏覽器的「搜尋」功能（Ctrl + F）在這一頁找。

最後另外整理了一份「**Python 語法小辭典**」，收錄書中順便介紹到的 Python 寫法。

---

## 第 0 章　寫在開始之前

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| Agent（代理人） | Agent | 能自己決定「下一步要做什麼」，並使用工具把事情做完的 AI 程式（第 7 章正式定義） | 0.1 |
| 工具 | Tool | 你寫好、讓 AI 可以「指定使用」的 Python 函式 | 0.1 |
| Google Colab | Google Colaboratory | Google 提供的免費線上 Python 環境，打開瀏覽器就能寫程式 | 0.4 |
| 筆記本 | Notebook | Colab 裡的一份 `.ipynb` 檔案，由很多儲存格組成 | 0.4 |
| 儲存格 | Cell | 筆記本裡一小格可以單獨執行的程式 | 0.4 |
| 執行階段 | Runtime | Colab 背後真正在跑你程式的雲端電腦；閒置太久會被回收，變數會消失 | 0.4 |
| 套件 | Package | 別人寫好、可以安裝來用的 Python 工具包 | 0.4 |
| pip | pip | Python 用來安裝套件的指令；在 Colab 裡要寫成 `!pip install` | 0.4 |
| API | Application Programming Interface（應用程式介面） | 一個系統對外開放的「窗口」，規定別的程式要用什麼格式來找它 | 0.5 |
| API key（API 金鑰） | API key | 證明「這個請求是誰送的」的一串密碼，像學生證；外洩會被盜用 | 0.5 |
| 免費額度 | Free tier | API 提供的免費使用量，有每分鐘、每天的次數限制 | 0.5 |
| 密鑰 | Secrets | Colab 提供的「私人保險箱」，用來存放 API key，分享筆記本時不會被一起分享 | 0.6 |
| Mock（模擬物） | Mock | 假裝成真東西的替身，輸入輸出格式和真的一樣，用來測試流程 | 0.7 |
| 停用 | Deprecated | 被標記為「即將淘汰」，之後可能無法使用 | 0.8 |
| SDK | Software Development Kit（軟體開發套件） | 官方寫好的工具包，把呼叫 API 的繁瑣步驟包成簡單的函式（第 2 章詳細說明） | 0.8 |

## 第 1 章　LLM 是什麼

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| LLM（大型語言模型） | Large Language Model | 用海量文字訓練出來、能根據前文預測下一個字的程式；本質是「超強的文字接龍」 | 1.1 |
| 參數 | Parameter | 模型裡面數十億個可以調整的數字，決定模型的行為 | 1.1 |
| 語言模型 | Language Model | 能算出「一段文字接下來最可能出現什麼」的模型 | 1.1 |
| 自迴歸生成 | Autoregressive generation | 每次只產生一個 token，接上去之後再產生下一個的生成方式 | 1.1 |
| 預訓練 | Pre-training | 讓模型讀海量文字、學會「接龍」的第一階段訓練 | 1.1 |
| 微調 | Fine-tuning | 用問答範例再調整模型，讓它的回答更像「助理」的第二階段訓練 | 1.1 |
| Token（詞元） | Token | 模型處理文字的最小單位，可能是一個字、半個單字或一個標點；費用和長度上限都用它計算 | 1.2 |
| 輸入 token / 輸出 token | Input / Output tokens | 送進模型的 token 和模型產生的 token，分開計費，輸出通常比較貴 | 1.2 |
| 貪婪解碼 | Greedy decoding | 每次都挑機率最高的 token，結果穩定但死板 | 1.3 |
| 取樣 | Sampling | 照機率抽 token，結果有變化、比較自然 | 1.3 |
| Temperature（溫度） | Temperature | 控制「抽籤」隨機程度的參數：越低越穩定，越高越多變 | 1.3 |
| 幻覺 | Hallucination | 模型產生聽起來合理、語氣肯定，但其實是錯的或不存在的內容 | 1.4 |
| 訓練資料截止日期 | Knowledge cutoff | 模型訓練資料的最後日期，之後發生的事它不知道 | 1.5 |

## 第 2 章　第一次呼叫 API

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| HTTP | HyperText Transfer Protocol（超文字傳輸協定） | 網路上程式互相傳資料的共同規則 | 2.1 |
| URL（網址） | Uniform Resource Locator | 要把請求送到哪裡的地址 | 2.1 |
| HTTP 方法 | HTTP method | 請求的動作類型；送資料通常用 `POST` | 2.1 |
| 標頭 | Header | 請求附帶的額外資訊，例如 API key、資料格式 | 2.1 |
| 請求主體 | Request body | 請求真正的內容，本書用 JSON 格式寫 | 2.1 |
| 回應 | Response | 伺服器回傳的結果 | 2.1 |
| 狀態碼 | Status code | 回應的結果代號：200 成功、400 格式錯誤、404 找不到、429 請求太多 | 2.1 |
| JSON | JavaScript Object Notation | 用文字表示資料的格式，長得很像 Python 的 dict 和 list | 2.1 |
| 端點 | Endpoint | API 裡某個具體功能的網址，例如 `generateContent` | 2.2 |
| Interactions API | Interactions API | Google 推薦新專案使用的新版 Gemini API，伺服器可以幫你保存對話（第 11 章） | 2.2 |
| 多模態 | Multimodal | 能同時處理文字、圖片、聲音等多種資料 | 2.3 |
| Role（角色） | Role | 標明訊息是誰說的：`system`（開發者）、`user`（使用者）、`assistant`（模型，Gemini 叫 `model`） | 2.4 |
| Messages | Messages | 一個 list，裡面是依序排列的對話訊息；本書的通用格式是 `{"role": ..., "content": ...}` | 2.4 |
| max_tokens / max_output_tokens | Max output tokens | 回答最多能用幾個 token，超過就硬切斷 | 2.5 |
| 思考 | Thinking | 模型在回答前先在內部進行的推理 | 2.6 |
| 思考 token | Thinking tokens | 思考時產生的 token，也要算錢，也算在長度上限裡 | 2.6 |
| 停止原因 | Finish reason | 模型為什麼停下來：`STOP`（講完了）、`MAX_TOKENS`（被長度上限切斷） | 程式 2-2 |
| Client（客戶端） | Client | SDK 裡記住金鑰和連線設定的物件，全書叫 `client` | 程式 2-5 |
| 列舉 | Enum | 程式中表示「固定幾個選項」的寫法，例如 `FinishReason.STOP` | 程式 2-5 |
| 駝峰式 / 蛇形 | camelCase / snake_case | 兩種命名方式：`maxOutputTokens`（REST）與 `max_output_tokens`（Python SDK） | 程式 2-3 |

## 第 3 章　讓它記得你

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 無狀態 | Stateless | 系統不保留「之前發生過什麼」，每次請求都是獨立的；像每次都換人接的客服專線 | 3.2 |
| 對話紀錄 | Chat history | 用 list 保存的整段對話，全書叫 `chat_history`（第 10 章的 Agent 版叫 `history`） | 3.3 |
| 上下文長度（上下文視窗） | Context window | 模型一次能讀進去的 token 數量上限，包含輸入和輸出 | 3.5 |
| 截斷 | Truncation | 只保留最近的對話、丟掉太舊的，用來控制長度和費用 | 3.6 |

## 第 4 章　控制輸出

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 結構化輸出 | Structured output | 讓模型照固定格式（例如 JSON）回答，讓程式能準確讀取 | 4.1 |
| Prompt（提示詞） | Prompt | 送給模型的文字指令 | 4.2 |
| System prompt（系統提示詞） | System prompt | 放在 `system` 角色裡、設定模型身分、規則和格式的文字；是「強烈的建議」，不是強制規則 | 4.2 |
| 提示工程 | Prompt engineering | 撰寫、調整 prompt 的技巧 | 4.2 |
| 意圖 | Intent | 使用者「想做什麼」，例如查課表、查天氣 | 4.3 |
| null | null | JSON 的「空值」，轉成 Python 後變成 `None` | 4.3 |
| 解析 | Parse | 把文字轉換成程式能使用的資料，例如 `json.loads()` | 4.4 |
| MIME type（媒體類型） | MIME type | 標示資料格式的標籤，例如 `application/json` | 4.6 |
| JSON 模式 | JSON mode | API 的設定，限制模型只能輸出合法的 JSON（保證語法，不保證內容） | 4.6 |

## 第 5 章　讓 LLM 使用工具（上）手刻版

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 工具呼叫（函式呼叫） | Tool calling / Function calling | 模型指定「要用哪個工具、參數是什麼」，由程式執行，再把結果交還給模型的過程 | 5.2 |
| 工具清單 | Tools registry | 把工具名稱（字串）對應到函式的 dict，全書叫 `TOOLS` | 5.4 |
| 工具結果 | Tool result | 程式執行工具後得到的結果，要送回給模型 | 5.6 |
| 世界標準時間 | UTC（Coordinated Universal Time） | 全世界共用的標準時間，比台灣慢 8 小時；Colab 預設使用它 | 程式 5-1 |
| 時區 | Time zone | 不同地區的時間設定，台灣是 `Asia/Taipei` | 程式 5-1 |
| 正規表示式 | Regular expression | 描述文字樣式的語法，用來搜尋、比對字串；Python 用 `re` 模組 | 程式 5-6 |

## 第 6 章　讓 LLM 使用工具（下）原生版

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 原生工具呼叫 | Native function calling | API 內建的工具呼叫功能，紙條格式由 API 標準化 | 6.1 |
| JSON Schema（JSON 結構描述） | JSON Schema | 用 JSON 描述「JSON 應該長什麼樣子」的標準寫法：型別、選項、必填欄位 | 6.2 |
| 工具宣告 | Function declaration | 用 JSON Schema 寫成的工具說明書：`name`、`description`、`parameters`，全書叫 `TOOL_DECLARATIONS` | 6.2 |
| enum | Enum | JSON Schema 裡「只能從這幾個值裡面選」的限制 | 6.2 |
| required | Required | JSON Schema 裡「一定要給」的參數 | 6.2 |
| function_call | Function call | 原生版中，模型回應裡的工具請求（紙條） | 6.4 |
| 思考簽章 | Thought signature | 新一代 Gemini 呼叫工具時附上的加密推理紀錄，下一次呼叫要原封不動送回 | 6.4 |
| function_response | Function response | 原生版中，送回給模型的工具結果 | 6.5 |
| Part（部分） | Part | Gemini 訊息裡的一個內容片段，可以是文字、工具請求或工具結果 | 6.5 |
| tool 角色 | Tool role | 本書通用格式中代表「工具執行結果」的角色 | 6.6 |
| 平行函式呼叫 | Parallel function calling | 模型在一次回應中同時要求好幾個互不相關的工具 | 6.8 |

## 第 7 章　Agent 誕生

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| Agent（代理人、智慧代理） | Agent | 能自己決定下一步、使用工具完成目標的程式；Agent ＝ LLM ＋ 工具 ＋ 迴圈 | 7.2 |
| Workflow（工作流程） | Workflow | 步驟由程式設計師事先寫死的流程，可預測但沒彈性 | 7.2 |
| Agent 迴圈 | Agent loop | 思考 → 行動 → 觀察 → 再思考，重複到模型不再要求工具為止 | 7.3 |
| 思考 / 行動 / 觀察 | Thought / Action / Observation | Agent 迴圈的三個動作：決定下一步、執行工具、讀取結果 | 7.3 |
| ReAct | Reasoning + Acting（推理＋行動） | 讓模型交替寫出推理、採取行動的方法，2022 年提出 | 7.4 |

## 第 8 章　讓 Agent 更可靠

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 例外 | Exception | 程式執行時發生的錯誤；沒有被 `try/except` 接住就會讓程式停止 | 8.1 |
| 自我修正 | Self-correction | 模型看到錯誤訊息後，自己換一種做法再試 | 8.2 |
| 停止條件 | Stopping condition | Agent 什麼時候該停：正常回答、超過步數、連續失敗、超過預算 | 8.4 |
| Token 預算 | Token budget | 一次任務最多能用多少 token，超過就停止，用來控制費用 | 8.5 |
| 紀錄（日誌） | Log | 把「什麼時間、做了什麼、結果如何」記下來，像飛機的黑盒子 | 8.6 |
| 連線錯誤 | ConnectionError | 程式連不上伺服器時的例外，本章用來模擬工具壞掉 | 程式 8-6 |

## 第 9 章　讓 Agent 更安全

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 工具分級 | Tool risk levels | 依照「出錯的後果」把工具分成只讀、可復原、不可逆三級 | 9.2 |
| 集合 | Set | Python 的資料型別，元素不重複，用 `in` 檢查很快；`DANGEROUS_TOOLS` 就是集合 | 9.2 |
| 人工確認（人在迴圈中） | Human-in-the-loop | 關鍵步驟停下來讓人決定，人同意了才繼續 | 9.3 |
| 預設拒絕 | Deny by default | 沒有明確同意就當作拒絕 | 9.3 |
| 提示注入 | Prompt injection | 把假指令藏在模型會讀到的文字裡，企圖讓模型拋棄原本的規則 | 9.4 |
| SQL 注入 | SQL injection | 把惡意程式碼注入正常資料的傳統資安攻擊，提示注入的名稱來源 | 9.4 |
| 直接注入 | Direct prompt injection | 假指令由使用者自己輸入 | 9.4 |
| 間接注入 | Indirect prompt injection | 假指令藏在工具讀回來的資料（網頁、公告、Email）裡，對 Agent 特別危險 | 9.4 |
| 多層防禦 | Defense in depth | 設好幾道防線，一層失守還有下一層 | 9.6 |
| 最小權限原則 | Principle of least privilege | 只給完成任務剛好需要的權限，多一點都不給 | 9.6 |
| 深複製 | Deep copy | 連同裡面所有的 list、dict 都完整複製一份，`copy.deepcopy()` | 程式 9-1 |
| 權限錯誤 | PermissionError | 沒有權限執行某個動作時的例外，本章用在 `send_email` 的網域限制 | 程式 9-6 |

## 第 10 章　記憶與知識

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 短期記憶 | Short-term memory | 這次對話的內容，存在程式的 list 裡（`history`），關掉就消失 | 10.2 |
| 長期記憶 | Long-term memory | 跨對話保存的重要資訊，存在檔案或資料庫裡 | 10.2 |
| 資料庫 | Database | 專門用來保存、查詢大量資料的系統 | 10.3 |
| RAG（檢索增強生成） | Retrieval-Augmented Generation | 先檢索相關資料、放進 prompt、再讓模型生成回答，像開書考 | 10.4 |
| 檢索 | Retrieval | 從資料中找出和問題相關的段落 | 10.4 |
| Bigram（二元組） | Bigram | 把文字切成「每兩個相鄰的字一組」的片段，本書用來做中文關鍵字搜尋 | 10.5 |
| 停用詞 | Stop words | 到處都會出現、對搜尋沒有幫助的字，例如「的、是、什麼」 | 10.5 |
| 向量 | Vector | 一串數字，用來表示一段文字的意思 | 10.7 |
| 嵌入 | Embedding | 用專門的模型把文字轉成向量；意思相近的文字，向量也會很接近 | 10.7 |
| 向量搜尋 | Vector search | 用向量找出「意思最接近」的資料，同義詞也找得到 | 10.7 |

## 第 11 章　回頭看框架

| 名詞 | 英文 | 白話解釋 | 出現位置 |
|------|------|---------|---------|
| 框架 | Framework | 別人寫好的一整套程式架構，你只要把自己的部分填進去 | 11.2 |
| 型別提示 | Type hint | `day: str`、`-> dict` 這種標記，說明參數或回傳值的型別；框架用它自動產生工具宣告 | 11.2 |
| 追蹤 | Tracing | 框架版的「紀錄」，記下 Agent 每一步的動作 | 11.2 |
| Session | Session | 框架用來保存對話（短期記憶）的機制 | 11.2 |
| Retriever | Retriever | 框架中負責 RAG「檢索」步驟的元件 | 11.2 |
| LangChain | LangChain | 廣為人知的 LLM 應用框架，用 `create_agent()` 建立 Agent | 11.3 |
| LangGraph | LangGraph | LangChain 用來執行 Agent 迴圈的底層框架 | 11.3 |
| 中介軟體 | Middleware | 在 Agent 迴圈的某個時間點插入自己程式的機制，例如人工確認 | 11.3 |
| OpenAI Agents SDK | OpenAI Agents SDK | OpenAI 官方的 Agent 框架，核心是 `Agent` 和 `Runner` | 11.4 |
| Guardrails（護欄） | Guardrails | 檢查輸入或輸出是否合規的機制 | 11.4 |
| Handoffs | Handoffs | 一個 Agent 把工作轉交給另一個 Agent | 11.4 |
| Tool Runner | Tool Runner | Claude API SDK 裡幫你跑工具呼叫迴圈的輔助功能 | 11.5 |
| Claude Agent SDK | Claude Agent SDK | 把 Claude Code 包成函式庫的 Agent 框架，有內建工具、權限、session、hooks | 11.5 |
| Hooks | Hooks | 在 Agent 執行過程的特定時間點自動執行你的程式 | 11.5 |
| Managed Agents | Managed Agents | 由 Anthropic 代管 Agent 迴圈和執行環境的服務 | 11.5 |
| ADK | Agent Development Kit | Google 官方的 Agent 框架，和 Gemini 整合最好 | 11.6 |
| MCP（模型上下文協定） | Model Context Protocol | 規定 AI 應用程式和外部工具、資料怎麼溝通的開放標準，像 USB 接頭 | 11.8 |
| 多 Agent 系統 | Multi-agent system | 好幾個 Agent 分工合作完成任務 | 11.8 |
| 評估 | Evaluation | 用一批測試問題，系統性地檢查 Agent 答得對不對 | 11.8 |
| 串流 | Streaming | 回答一個字一個字送回來，使用者不用乾等 | 11.8 |
| 部署 | Deployment | 把程式放到伺服器上，讓別人可以使用 | 11.8 |
| 環境變數 | Environment variable | 作業系統層級的設定值，`os.environ`；LangChain 從這裡讀 API key | 程式 11-1 |

---

## Python 語法小辭典

書中順便介紹的 Python 寫法，依第一次出現的位置排列。

| 寫法 | 名稱 | 意思 | 範例 | 出現位置 |
|------|------|------|------|---------|
| `!指令` | Colab 系統指令 | 開頭加 `!`，交給系統執行，不是 Python | `!pip install requests` | 0.4 |
| `random.choices(list, weights=...)` | 加權隨機抽樣 | 照指定的比例抽元素，回傳 list | `random.choices(["a", "b"], weights=[0.7, 0.3])` | 程式 1-1 |
| `max(d, key=d.get)` | 找最大值的 key | 找出 dict 中值最大的那個 key | `max(probs, key=probs.get)` | 程式 1-1 |
| `f"{x:>4}"` | f-string 格式設定 | 靠右對齊、佔 4 格；`:.6f` 是小數點後 6 位 | `f"{3.14159:.2f}"` → `3.14` | 程式 3-4 |
| `.get(key, 預設值)` | 安全取值 | dict 找不到 key 時回傳預設值，不會出錯 | `usage.get("thoughtsTokenCount", 0)` | 程式 2-2 |
| `[x for x in list if 條件]` | 串列生成式（list comprehension） | 一行寫完的 for 迴圈，產生新的 list | `[m for m in msgs if m["role"] == "system"]` | 程式 3-5 |
| `list[-n:]` | 負數切片 | 取最後 n 個元素 | `history[-4:]` | 程式 3-5 |
| `x if 條件 else y` | 條件運算式 | 一行的 if-else | `"model" if role == "assistant" else "user"` | 程式 2-6 |
| `llm = call_llm` | 函式也是值 | 函式可以存進變數（注意沒有括號） | `llm = mock_llm if USE_MOCK else call_llm` | 程式 4-7 |
| `func.__name__` | 函式名稱 | 取得函式的名字 | `llm.__name__` → `"call_llm"` | 程式 4-7 |
| `func(**d)` | 展開 dict 成參數 | 呼叫函式時把 dict 展開成具名參數 | `get_schedule(**{"day": "星期五"})` | 程式 5-2 |
| `{**d1, "k": v}` | 展開 dict | 把 dict 的內容放進新的 dict | `{"city": city, **FAKE_WEATHER[city]}` | 程式 5-1 |
| `set(a) <= set(b)` | 子集合 | 檢查 a 的元素是不是都在 b 裡 | `set(expression) <= allowed` | 程式 5-1 |
| `isinstance(x, 型別)` | 型別檢查 | 檢查 x 是不是某個型別 | `isinstance(result, str)` | 程式 5-2 |
| `range(n - 1, -1, -1)` | 倒數迴圈 | 從 n-1 倒數到 0 | `for i in range(len(msgs) - 1, -1, -1)` | 程式 5-6 |
| `except 例外類別 as e` | 接住特定例外 | 具體的例外寫前面，`Exception` 放最後 | `except TypeError as e:` | 程式 8-2 |
| `def f(**details)` | 收集具名參數 | 定義函式時，把其他具名參數收集成 dict | `log_event(1, "tool", name="calculator")` | 程式 8-5 |
| `with open(...) as f` | 開檔 | 區塊結束時自動關閉檔案 | `with open("log.json", "w", encoding="utf-8") as f:` | 程式 8-7 |
| `json.dump` / `json.load` | 寫入 / 讀取 JSON 檔 | 沒有 `s` 的版本直接對檔案操作 | `json.dump(data, f, ensure_ascii=False)` | 程式 8-7 |
| `1_000_000` | 數字分隔 | 底線只是為了好讀，等於 `1000000` | `total / 1_000_000` | 程式 8-7 |
| `{"a", "b"}` | 集合 | 元素不重複的資料型別 | `DANGEROUS_TOOLS = {"drop_course", "send_email"}` | 9.2 |
| `copy.deepcopy(x)` | 深複製 | 完整複製一份，改其中一份不會影響另一份 | `copy.deepcopy(FAKE_SCHEDULE)` | 程式 9-1 |
| `d.clear()` / `d.update(x)` | 清空 / 合併 dict | 修改同一個 dict，而不是建立新的 | `FAKE_SCHEDULE.clear()` | 程式 9-1 |
| `globals()` | 全域變數表 | 回傳目前所有全域變數組成的 dict | `"mock_next_action_ch9" not in globals()` | 程式 10-3 |
| `list.extend(other)` | 接上另一個 list | 把另一個 list 的元素一個一個加進來 | `messages.extend(history)` | 程式 10-2 |
| `is not None` | 判斷有沒有值 | 和 `if x:` 不同，空 list 也算「有傳」 | `if history is not None:` | 程式 10-2 |
| `set(a) & set(b)` | 交集 | 兩個集合都有的元素 | `set(pair) & STOP_CHARS` | 程式 10-4 |
| `lambda 參數: 運算式` | 匿名函式 | 一行的小函式，常用在排序 | `sort(key=lambda item: item[0])` | 程式 10-4 |
| `list[:] = 新內容` | 切片賦值 | 換掉 list 裡的內容，而不是指向新的 list | `history[:] = trim_history(history)` | 程式 10-6 |
| `os.environ["KEY"]` | 環境變數 | 讀寫作業系統層級的設定值 | `os.environ["GOOGLE_API_KEY"] = ...` | 程式 11-1 |
