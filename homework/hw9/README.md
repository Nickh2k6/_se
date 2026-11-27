# hw9：從 LLM API 到 AI Agent —— 一步一步親手打造你的第一個 Agent

> 軟體工程 hw9：用 AI 寫一本給初學者的技術入門書。
> 範例程式使用 **Google Gemini API**，全部在 **Google Colab** 執行。

## 檔案說明

| 檔案 | 內容 |
|------|------|
| `README.md` | 題目要求、全書目錄、全書共用命名表 |
| `ch00.md` ～ `ch11.md` | 第 0 章到第 11 章，一章一個檔案 |
| `appendix-a.md` ～ `appendix-d.md` | 附錄 A～D |

---

## 全書目錄

### 第 0 章　寫在開始之前（`ch00.md`）
這本書會帶你做出什麼、該怎麼讀，以及動手前要先準備好的環境。

- 0.1 這本書要帶你做出什麼：「校園小助理 Agent」完成後的樣子 —— 先看終點，再出發。
- 0.2 一張圖看懂全書：五層能力（API → 記憶 → 結構化輸出 → 工具 → Agent 迴圈）怎麼一層一層疊起來。
- 0.3 怎麼讀這本書：每章的固定格式、哪些章一定要跑程式、哪些可以先跳過。
- 0.4 準備 Google Colab：開新筆記本、執行儲存格、`!pip install` 是什麼。
- 0.5 申請 Gemini API key：到 Google AI Studio 取得金鑰、免費額度的限制。
- 0.6 把 API key 放進 Colab 密鑰（Secrets）：為什麼絕對不能寫死在程式裡，以及 `userdata.get()` 怎麼用。
- 0.7 沒有 API key 也沒關係：介紹貫穿全書的「假的 LLM」（mock LLM）。
- 0.8 模型會更新：遇到錯誤時，如何對照官方文件確認最新寫法。

### 第 1 章　LLM 是什麼（`ch01.md`）
用「超強的文字接龍」理解大型語言模型，知道它擅長什麼、為什麼會一本正經地亂講。

- 1.1 超強的文字接龍：LLM（Large Language Model，大型語言模型）其實只做一件事 —— 猜下一個字。
- 1.2 Token 是什麼：模型眼中的「字」不是我們的字，以及它跟計費的關係。
- 1.3 機率與取樣：同一個問題為什麼每次回答不一樣。
- 1.4 幻覺（hallucination）：模型為什麼會編造不存在的課程或日期。
- 1.5 LLM 不會的事：不知道現在幾點、不會真的算數、不能上網 —— 這正是後面要加「工具」的原因。

### 第 2 章　第一次呼叫 API（`ch02.md`）
先用 `requests` 直接發 HTTP 請求看懂原始 JSON，再換成官方 SDK，做出第一個 `call_llm()` 函式。

- 2.1 API 與 HTTP 請求：用「點餐單」比喻 request（請求）與 response（回應），以及常見狀態碼。
- 2.2 本書使用的端點與模型：`generateContent` ＋ `gemini-3.5-flash-lite`，以及版本變動的提醒。
- 2.3 請求長什麼樣子：一層一層拆開 `contents` / `role` / `parts` / `text`。
- 2.4 messages 與 role：system / user / assistant（Gemini 裡叫 `model`）三種角色各代表誰。
- 2.5 兩個常用參數：`temperature`（隨機程度）與 `max_tokens`（Gemini 叫 `max_output_tokens`，回答長度上限）。
- 2.6 什麼是「思考」（thinking）：思考 token 也算錢、也算在長度上限裡。
- 2.7 SDK 是什麼：「紙本點餐單」與「點餐 App」。
- 動手做：先用 `requests` 看懂原始 JSON，再換成 `google-genai` SDK，最後包成全書共用的 `call_llm()`。

### 第 3 章　讓它記得你（`ch03.md`）
API 本身不會記得上一句話，所以要自己用 list 把對話存起來，做出能連續聊天的迴圈。

- 3.1 實驗：連問兩句，模型忘記你叫什麼名字了。
- 3.2 無狀態（stateless）是什麼：每次呼叫都是「第一次見面」。
- 3.3 用 list 保存對話：`chat_history` 的結構與更新方式。
- 3.4 做出聊天迴圈：`while True` ＋ `input()`，輸入 `exit` 離開。
- 3.5 上下文長度（context window）：對話越長，送出去的 token 越多。
- 3.6 成本問題：每一輪都把整段歷史重送一次，費用怎麼算、怎麼截斷舊訊息。

### 第 4 章　控制輸出（`ch04.md`）
用 system prompt 規定角色與規則，要求模型輸出 JSON，讓程式能讀懂它的回答；並寫出 mock LLM。

- 4.1 問題：模型的回答是給人看的，程式很難從中挑出資料。
- 4.2 System prompt：設定「校園小助理」的身分、語氣與規則。
- 4.3 要求輸出 JSON：在 prompt 裡給格式範例。
- 4.4 用 `json.loads()` 解析：把文字變成 Python dict。
- 4.5 格式錯誤怎麼辦：多了 \`\`\`json 標記、少了括號 —— 清理、`try/except`、重試。
- 4.6 用 API 的 JSON 模式：`response_mime_type` 讓 Gemini 保證輸出 JSON。
- 4.7 寫出 `mock_llm()`：沒有 API key 也能跑第 4 章以後的程式。

### 第 5 章　讓 LLM 使用工具（上）手刻版（`ch05.md`）
關鍵觀念：LLM 自己不會執行任何東西，它只會說「要用哪個工具、參數是什麼」，真正執行的是你的程式。

- 5.1 問題：模型不知道今天星期幾、算錯大數字、不知道你的課表。
- 5.2 核心觀念：模型是「下指令的人」，你的程式才是「動手的人」。
- 5.3 準備工具：`calculator()`、`get_current_time()`、`get_schedule()`、`get_weather()`（課表與天氣用 dict 模擬）。
- 5.4 工具清單 `TOOLS`：用 dict 把名稱對應到函式。
- 5.5 用 prompt 教模型輸出 `{"tool": ..., "args": ...}`。
- 5.6 解析 → 執行 → 把結果送回去：寫出 `run_tool()`，完成一次完整的工具呼叫。
- 5.7 手刻版的限制：格式常出錯、prompt 越寫越長、一次只能叫一個工具。

### 第 6 章　讓 LLM 使用工具（下）原生版（`ch06.md`）
改用 Gemini 內建的工具呼叫（function calling），並和手刻版逐項對照。

- 6.1 為什麼 API 要內建工具呼叫：把第 5 章的痛點交給模型廠商處理。
- 6.2 用 JSON Schema 描述工具：名稱、說明、參數型別。
- 6.3 送出工具定義：`tools` 參數怎麼寫。
- 6.4 讀懂回傳的 `function_call`：模型想叫哪個工具、帶什麼參數。
- 6.5 送回 `function_response`：把執行結果交還給模型。
- 6.6 在通用格式裡記錄工具呼叫：`tool_calls`、`tool` 角色，以及保留思考簽章的 `raw`。
- 6.7 手刻版 vs 原生版對照表：一項一項比較。
- 6.8 一次叫多個工具（parallel function calling）。

### 第 7 章　Agent 誕生（`ch07.md`）
Agent = LLM ＋ 工具 ＋ 迴圈。把「呼叫一次工具」變成「自己決定要做幾步」，寫出第一版 `run_agent()`。

- 7.1 問題：「明天第一堂課前，天氣適合騎車嗎？」需要好幾個步驟，一次工具呼叫不夠。
- 7.2 Agent 是什麼：用「會自己查資料的實習生」比喻。
- 7.3 思考 → 行動 → 觀察 → 再思考：Agent 迴圈的四個動作。
- 7.4 ReAct（Reasoning + Acting，推理加行動）：這個想法從哪裡來。
- 7.5 用 `while` 迴圈寫出 `run_agent()`：什麼時候繼續、什麼時候停。
- 7.6 把每一步印出來：看見 Agent 的「腦內過程」。
- 7.7 用 mock LLM 跑一次：不花錢也能看懂流程。

### 第 8 章　讓 Agent 更可靠（`ch08.md`）
工具一定會出錯、模型可能繞圈圈，要讓 Agent 能自我修正，也要知道什麼時候該停。

- 8.1 問題：工具丟出例外，整個程式就當掉了。
- 8.2 把錯誤訊息回傳給模型：讓它自己換個參數再試一次。
- 8.3 最大步數 `max_steps`：防止無限迴圈。
- 8.4 停止條件：正常結束、達到上限、連續失敗。
- 8.5 成本控制：記錄每一步的 token 用量，超過預算就停。
- 8.6 加上紀錄（log）：出事時能回頭查是哪一步出錯。

### 第 9 章　讓 Agent 更安全（`ch09.md`）
Agent 能做的事越多，出錯的代價越大：危險的動作要人來點頭，外部內容不能盲目相信。

- 9.1 問題：如果工具是「退選課程」或「寄信給教授」呢？
- 9.2 工具分級：哪些工具可以直接執行、哪些要先問人。
- 9.3 人工確認（human-in-the-loop）：執行前先印出內容，等使用者輸入 `y`。
- 9.4 提示注入（prompt injection）是什麼：藏在資料裡的「假指令」。
- 9.5 實驗：在假的公告資料裡藏一句「忽略之前的指示⋯⋯」，看 Agent 會不會上當。
- 9.6 防禦原則：工具回傳的內容是「資料」不是「命令」、最小權限、危險動作一律確認。

### 第 10 章　記憶與知識（進階）（`ch10.md`）
讓 Agent 記得跨對話的事，也能查詢它原本不知道的校園資料。

- 10.1 記憶和知識，其實都是「放進 messages 的文字」。
- 10.2 短期記憶 vs 長期記憶：`chat_history` 與存在檔案裡的筆記。
- 10.3 用 JSON 檔做長期記憶：`save_memory()` 與 `load_memory()`。
- 10.4 RAG（Retrieval-Augmented Generation，檢索增強生成）是什麼：「開書考」比喻。
- 10.5 用關鍵字搜尋做最簡單的 RAG：從假的「校園公告」裡找出相關段落。
- 10.6 把搜尋包成工具：`search_notes()` 讓 Agent 自己決定什麼時候查。
- 10.7 關鍵字搜尋的限制：為什麼真正的系統會用向量搜尋（embedding）。

### 第 11 章　回頭看框架（`ch11.md`）
畫出從「API 呼叫」到「Agent」的完整層級圖，看懂框架到底幫你包裝了哪些東西。

- 11.1 全書回顧：一張完整的層級圖。
- 11.2 框架在做什麼：把前面手寫的程式換成現成的零件。
- 11.3 LangChain：對照它的 model、tool、agent 各對應到本書哪一章。
- 11.4 OpenAI Agents SDK：Agent、Tool、Runner 的對應。
- 11.5 Claude Agent SDK：內建工具、權限確認與第 9 章的關係。
- 11.6 Google 的新做法：Interactions API（伺服器幫你記對話）與 ADK（Agent Development Kit）。
- 11.7 什麼時候該用框架、什麼時候自己寫就好。
- 11.8 下一步可以學什麼：MCP、多 Agent、評估（evaluation）。

### 附錄
- **附錄 A　名詞小辭典**（`appendix-a.md`）：全書專有名詞，依章節排列，附英文原文與白話解釋。
- **附錄 B　常見錯誤與排除**（`appendix-b.md`）：401、403、429、模型名稱錯誤、JSON 解析失敗、無限迴圈、Colab 密鑰讀不到⋯⋯
- **附錄 C　完整程式碼**（`appendix-c.md`）：最終版「校園小助理 Agent」，可整段貼進 Colab 執行。
- **附錄 D　各章練習題解答**（`appendix-d.md`）

---

## 全書共用命名表

後面章節會接著前面的程式繼續改，所以名稱從頭到尾都用這一套：

| 名稱 | 種類 | 第一次出現 | 用途 |
|------|------|-----------|------|
| `GEMINI_API_KEY` | Colab 密鑰名稱 | 第 0 章 | 存在 Colab Secrets 的 API key |
| `api_key` | 變數 | 第 2 章 | 從 Colab 密鑰讀出來的 API key |
| `MODEL_NAME` | 變數 | 第 2 章 | 模型名稱，目前是 `gemini-3.5-flash-lite` |
| `messages` | list | 第 2 章 | 通用格式訊息：`[{"role": "system"/"user"/"assistant", "content": "..."}]` |
| `client` | 變數 | 第 2 章 | `google-genai` SDK 的連線物件 |
| `call_llm(messages, temperature, max_output_tokens, json_mode)` | 函式 | 第 2 章（第 4 章加 `json_mode`） | 送出訊息、回傳模型的文字回答 |
| `chat_history` | list | 第 3 章 | 保存整段對話 |
| `trim_history(chat_history, max_messages)` | 函式 | 第 3 章 | 保留 system ＋ 最近幾則訊息 |
| `SYSTEM_PROMPT` | 字串 | 第 4 章 | 校園小助理的角色與規則（只放角色規則，不放格式） |
| `JSON_FORMAT_PROMPT` | 字串 | 第 4 章 | 第 4 章的 JSON 意圖格式規定 |
| `parse_json_reply(text)` | 函式 | 第 4 章 | 清理並解析模型回答的 JSON，失敗回傳 `None` |
| `ask_json(messages, max_retries)` | 函式 | 第 4 章 | 解析失敗時把錯誤告訴模型並重試 |
| `WEEKDAYS` | list | 第 4 章 | 星期一～星期日 |
| `mock_llm(messages, ...)` | 函式 | 第 4 章 | 假的 LLM，參數和 `call_llm()` 完全一樣 |
| `USE_MOCK` / `llm` | 開關 / 函式變數 | 第 4 章 | `llm = mock_llm if USE_MOCK else call_llm`；第 5 章起一律呼叫 `llm()` |
| `calculator(expression)` | 工具 | 第 5 章 | 計算算式 |
| `get_current_time()` | 工具 | 第 5 章 | 取得現在時間 |
| `get_schedule(day)` | 工具 | 第 5 章 | 查詢假的課表 |
| `get_weather(city)` | 工具 | 第 5 章 | 查詢假的天氣 |
| `FAKE_SCHEDULE` / `FAKE_WEATHER` | dict | 第 5 章 | 假的課表與天氣資料 |
| `TOOLS` | dict | 第 5 章 | 工具名稱 → 函式 |
| `run_tool(name, args)` | 函式 | 第 5 章 | 依名稱執行工具，結果轉成字串回傳 |
| `tool_result_message(name, args, result)` | 函式 | 第 5 章 | 把工具結果包成 `[工具結果] ...` 的 user 訊息 |
| `TOOL_PROMPT` | 字串 | 第 5 章 | 手刻版工具說明：輸出 `{"tool", "args"}` 或 `{"answer"}` |
| `ask_with_tool(user_input)` | 函式 | 第 5 章 | 手刻版工具呼叫，最多用一次工具 |
| `mock_next_action(question, used)` | 函式 | 第 5 章 | mock_llm 的關鍵字規則，決定下一個工具 |
| `TOOL_DECLARATIONS` | list | 第 6 章 | 給 Gemini 看的工具說明（JSON Schema） |
| `call_llm_tools(messages, ...)` | 函式 | 第 6 章 | 原生工具呼叫版，回傳 `{"text", "tool_calls", "raw"}` |
| `mock_llm_tools(messages, ...)` | 函式 | 第 6 章 | 假的原生工具呼叫，格式同上（`raw` 為 `None`） |
| `llm_tools` | 函式變數 | 第 6 章 | `llm_tools = mock_llm_tools if USE_MOCK else call_llm_tools` |
| `ask_with_native_tools(user_input)` | 函式 | 第 6 章 | 原生版，最多一輪（可平行）工具呼叫 |
| 工具紙條訊息 | messages 元素 | 第 6 章 | `{"role": "assistant", "content", "tool_calls", "raw"}` |
| 工具結果訊息 | messages 元素 | 第 6 章 | `{"role": "tool", "name", "content"}` |
| `AGENT_PROMPT` | 字串 | 第 7 章 | Agent 工作守則（先寫想法、資訊夠了就回答） |
| `format_call(name, args)` | 函式 | 第 7 章 | 把工具請求排成 `get_schedule(day="星期五")` |
| `run_agent(user_input, max_steps)` | 函式 | 第 7 章 | Agent 主迴圈：思考 → 行動 → 觀察 |
| `MOCK_THOUGHTS` | dict | 第 7 章 | mock 使用各工具前寫出的想法 |
| `run_tool()`（安全版） | 函式 | 第 8 章 | 接住所有例外，回傳「錯誤：」開頭的文字 |
| `usage` 欄位 | `llm_tools` 回傳值 | 第 8 章 | `{"input": 輸入 token, "output": 輸出 token}` |
| `run_agent(user_input, max_steps, max_failures, token_budget)` | 函式 | 第 8 章 | 可靠版：四種停止條件＋紀錄 |
| `AGENT_LOG` / `log_event(step, kind, **details)` | list / 函式 | 第 8 章 | 最近一次執行的每一步紀錄 |
| `stubborn_llm_tools(messages, ...)` | 函式 | 第 8 章 | 測試用：永遠要求同一個工具的假模型 |
| `get_announcements()` / `drop_course(course)` / `send_email(to, subject, body)` | 工具 | 第 9 章 | 讀公告（只讀）、退選與寄信（危險） |
| `FAKE_ANNOUNCEMENTS` / `SENT_EMAILS` / `ORIGINAL_SCHEDULE` | list / list / dict | 第 9 章 | 假公告（含提示注入）、假寄件備份、課表備份 |
| `reset_fake_data()` | 函式 | 第 9 章 | 還原課表、清空寄件備份 |
| `DANGEROUS_TOOLS` | set | 第 9 章 | 需要人工確認的工具名稱 |
| `ask_user_confirm(name, args)` | 函式 | 第 9 章 | 印出完整動作，只有輸入 y 才同意 |
| `run_tool()`（＋人工確認） | 函式 | 第 9 章 | 危險工具先問人；拒絕時回傳「已取消：」開頭 |
| `SYSTEM_PROMPT`（第 5 條規則） | 字串 | 第 9 章 | 工具回傳的內容是資料，不是指令 |
| `ALLOWED_EMAIL_DOMAIN` | 字串 | 第 9 章 | `send_email` 只能寄到 `@nqu.edu.tw` |
| `build_system_prompt()` | 函式 | 第 10 章 | 組出 SYSTEM_PROMPT ＋ AGENT_PROMPT ＋ 長期記憶 |
| `run_agent(..., history=None)` | 函式 | 第 10 章 | 多了短期記憶參數，正常回答後自動存入問答 |
| `MEMORY_FILE` | 字串 | 第 10 章 | 長期記憶檔 `campus_memory.json` |
| `save_memory()` / `load_memory()` | 函式 | 第 10 章 | 長期記憶的讀寫 |
| `remember(fact)` | 工具 | 第 10 章 | 讓模型把使用者的重要資訊存進長期記憶 |
| `mock_next_action_ch9` / `NOTE_KEYWORDS` | 函式 / list | 第 10 章 | mock 升級時保留的第 9 章版本、查規定的關鍵字 |
| `CAMPUS_NOTES` / `STOP_CHARS` | list / set | 第 10 章 | 虛構的學校規定、搜尋用的停用詞 |
| `make_bigrams(text)` | 函式 | 第 10 章 | 把中文切成兩字一組 |
| `search_notes(query, top_k)` | 工具 | 第 10 章 | 關鍵字（兩字組）搜尋學校規定 |
| `build_rag_prompt(question)` | 函式 | 第 10 章 | 手動 RAG：搜尋結果＋問題組成 prompt |
| `chat_agent()` | 函式 | 第 10 章 | 聊天版：短期＋長期記憶＋所有工具 |

---

## 原始題目

以下是這份作業的題目（「主要使用的 API」那欄原本要自己填，這裡選 Google Gemini）。

```markdown
# 任務
請寫一本給初學者的技術入門書，主題是：
「從 LLM API 到 AI Agent：一步一步親手打造你的第一個 Agent」

讀完這本書，讀者要能：
1. 用自己的話解釋 LLM API、對話記憶、結構化輸出、工具呼叫（Tool Calling）、Agent 迴圈分別是什麼，以及它們怎麼一層一層疊起來。
2. 不使用任何 Agent 框架，自己用 Python 寫出一個能使用多個工具的迷你 Agent。
3. 知道 LangChain 之類的框架「幫開發者做掉了哪些事」。

# 目標讀者
- 資工系大學生，會基本 Python（變數、函式、list / dict、迴圈、try/except）。
- 完全沒碰過 LLM API 或 Agent。
- 用 Google Colab 執行程式。

# 寫作風格
1. 由淺入深：每一章只引入一個新概念，而且要建立在前一章之上。
2. 先講結論，再講細節。
3. 專有名詞第一次出現時，先用白話解釋意思並附上英文原文。不要預設讀者已經懂。
4. 多用生活比喻，但比喻完一定要回到真正的技術說明。
5. 每一章都要說清楚「上一章的做法遇到什麼限制，所以才需要這一章」，讓讀者感覺每一層都是自然長出來的，不是憑空出現。
6. 用繁體中文、台灣慣用的技術用語。
7. 適當使用 ASCII 圖或流程圖，說明資料怎麼在「使用者 → 程式 → LLM → 工具」之間流動。

# 程式碼規則
程式碼只用在「需要實際執行，才能看懂系統怎麼實作」的地方，不要為了寫程式而寫程式。
- 每段程式都必須能直接貼到 Google Colab 執行；需要安裝的套件，在該章開頭用 !pip install 列出。
- 一段程式只示範一個新概念，保持簡短。
- 註解用繁體中文。
- 每段程式後面都要有：①逐段解說 ②執行後預期會看到的輸出範例。
- API key 一律用 Colab 的「密鑰（Secrets）」讀取（from google.colab import userdata），絕對不可以寫死在程式裡。
- 主要使用的 API：Google Gemini。模型名稱與 SDK 寫法請用你所知最新的版本，並在書中提醒讀者：如果執行出錯，要對照官方文件確認。
- 另外提供一個「假的 LLM 函式」（mock LLM），讓沒有 API key 的讀者也能跑通第 4 章以後的流程、理解機制。
- 盡量讓讀者看見底層：先用 requests 直接發 HTTP 請求、看懂原始 JSON，再改用官方 SDK；每一層都先手寫，最後才介紹框架。

# 貫穿全書的實作專案
整本書都圍繞同一個專案：「校園小助理 Agent」。每一章為它加上一層新能力，最後一章組合成完整版本。
工具範例：計算機、取得現在時間、查詢一份假的課表或天氣資料（用 Python dict 模擬即可，不需要真的串外部服務）。

# 章節架構（請依此擴寫，可微調章名，但不要改順序）
第 0 章 寫在開始之前：這本書會帶你做出什麼、怎麼讀、Colab 與 API key 的準備
第 1 章 LLM 是什麼：用「超強的文字接龍」理解；token、機率、為什麼會亂講（幻覺，hallucination）
第 2 章 第一次呼叫 API：HTTP 請求、request / response 的 JSON 結構、messages、role（system / user / assistant）、temperature、max_tokens；先用 requests，再用 SDK
第 3 章 讓它記得你：API 是無狀態（stateless）的；用 list 自己保存對話；做出聊天迴圈；context window（上下文長度）與成本問題
第 4 章 控制輸出：system prompt 設定角色與規則；要求輸出 JSON 並用 Python 解析；格式錯誤時怎麼處理
第 5 章 讓 LLM 使用工具（上）手刻版：關鍵觀念是「LLM 自己不會執行任何東西，它只會說要用哪個工具、參數是什麼，真正執行的是你的程式」；只靠 prompt 讓模型輸出 {"tool": ..., "args": ...}，程式解析、執行、把結果送回
第 6 章 讓 LLM 使用工具（下）原生版：改用 API 內建的 tool calling，和手刻版逐項對照
第 7 章 Agent 誕生：Agent = LLM ＋ 工具 ＋ 迴圈；思考 → 行動 → 觀察 → 再思考；ReAct（Reasoning + Acting）概念；用 while 迴圈寫出迷你 Agent，並把每一步印出來
第 8 章 讓 Agent 更可靠：工具出錯時把錯誤回傳給模型讓它自我修正；最大步數與停止條件；成本控制
第 9 章 讓 Agent 更安全：危險工具要人工確認；提示注入（prompt injection）是什麼、為什麼工具回傳的內容不能盲目相信
第 10 章 記憶與知識（進階）：短期 vs 長期記憶；RAG（檢索增強生成）的基本概念，用簡單的關鍵字搜尋示範
第 11 章 回頭看框架：畫出從「API 呼叫」到「Agent」的完整層級圖；對照 LangChain、OpenAI Agents SDK、Claude Agent SDK，說明它們把前面手寫的哪些部分包裝起來
附錄 A 名詞小辭典（全書專有名詞，依章節排列）
附錄 B 常見錯誤與排除（401、429、JSON 解析失敗、無限迴圈⋯⋯）
附錄 C 完整程式碼（最終版校園小助理 Agent）
附錄 D 各章練習題解答

# 每一章的固定格式
1. 【本章重點】兩三句話的結論
2. 【為什麼需要這一章】上一章的限制
3. 【觀念解說】白話解釋 ＋ 比喻 ＋ 圖示
4. 【動手做】程式碼 ＋ 逐段解說 ＋ 預期輸出（需要時才有）
5. 【常見錯誤】這章最容易踩的坑
6. 【本章小結】3–5 點
7. 【練習題】2–3 題，由簡單到稍難（解答放附錄 D）

# 輸出方式
這本書很長，請分段輸出：
1. 先輸出完整目錄（含每章的小節標題與一句話說明），然後停下來。
2. 之後每次輸出一章，寫完一章就停下來；我說「繼續」再寫下一章。
3. 每一章都要完整寫完，不要用「以下省略」或「同上」帶過。
4. 後面章節的程式碼必須和前面章節一致（同樣的變數名稱、函式名稱），讓讀者能接著上一章的程式繼續改。
```
