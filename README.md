# 投稿審查系統

依 1151 期中個人專題 PPT 製作，參考 DB-Basic Example 的 FastAPI、HTML 表單、Session、Jinja2 與直接 SQL 寫法。

## 功能

- 作者：查看自己的稿件、新增、修改及刪除編輯中的稿件、送出投稿。
- 編輯：查看待審清單與文章，通過或退回稿件。
- 狀態：編輯中 → 審查中 → 已通過，退回時回到編輯中。
- 補充規則：後端檢查角色、作者擁有權及狀態，不能透過修改網址操作他人稿件。

## 第一次安裝

需要 uv、Python 3.12 以上與 PostgreSQL。以下命令在專案資料夾的 PowerShell 執行。

```powershell
uv sync
Copy-Item .env.example .env
```

使用 pgAdmin 或 psql 建立專題資料庫（只執行一次）：

```sql
CREATE DATABASE a_review_web;
```

編輯 `.env`，將 DATABASE_URL 的 YOUR_PASSWORD 換成本機 PostgreSQL 密碼，並設定 SESSION_SECRET 為自己的隨機字串。可以用以下命令產生：

```powershell
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

再執行：

```powershell
uv run python init_db.py
uv run python run.py
```

瀏覽器開啟 http://127.0.0.1:8000 。按 Ctrl+C 停止伺服器，修改 Python 後重新執行啟動命令。

這次製作時已在原電腦完成獨立資料庫、`.env` 與資料表設定，原電腦直接執行 `uv run python run.py` 即可。從 GitHub 下載到其他電腦時，仍需完成上述第一次安裝。

**課堂範例之外的調整：** 本機 Python 3.14 在 Windows 預設的事件迴圈無法配合 psycopg 非同步連線，因此新增 run.py，明確使用 SelectorEventLoop。這裡的啟動命令是專案補充，並非 PPT 原文。

## 示範帳號

| 帳號 | 密碼 | 角色 |
| --- | --- | --- |
| author | 初始化時輸入的密碼 | 作者 |
| author2 | 初始化時輸入的密碼 | 第二位作者，測試資料隔離 |
| editor | 初始化時輸入的密碼 | 編輯 |

初始化時會要求輸入至少 8 字元的密碼。這是本機課堂示範版本，帳號由 init_db.py 建立，沒有註冊功能。重跑初始化不刪除既有資料，也不重設既有帳號密碼。密碼以雜湊存放；正式公開使用前需更換示範帳號、設定 HTTPS 與登入限制。

## 操作練習

1. 用 author 登入，新增文章並儲存。
2. 回清單編輯內容，確認後按「送出投稿」。
3. 登出，用 editor 登入，開啟稿件，按「退回修改」。
4. 用 author 登入，修改並再次送出。
5. 用 editor 登入，按「通過稿件」。
6. 用 author 登入，可看到「已通過」，不能再修改或刪除。

## 檔案與閱讀順序

| 檔案 | 用途 |
| --- | --- |
| schema.sql | users 與 articles 資料表 |
| db.py | 課堂風格的資料庫連線池及 getDB |
| main.py | 登入、清單、新增、修改、刪除、送審、審查 |
| templates/ | HTML 表單與清單，Jinja2 顯示資料 |
| static/style.css | 基本排版與小螢幕調整 |
| static/script.js | 刪除及送審確認視窗 |
| security.py | 密碼雜湊工具 |
| init_db.py | 建立資料表與示範帳號 |
| run.py | Windows 相容的啟動程式 |
| test_workflow.py | 完整流程與權限驗證 |

`Form(...)` 接收表單，`Depends(getDB)` 取得連線，SQL 使用參數而不是拼接文字，`TemplateResponse` 顯示網頁，`RedirectResponse(..., 303)` 在修改後回清單。CSRF 隱藏欄位用來確認表單來自目前登入的工作階段。

## 測試

```powershell
uv run pytest -q
```

需要可連線的 PostgreSQL 與 `.env`。測試建立隨機命名的獨立 schema，結束後移除自己的 schema，不清空正式的稿件資料。涵蓋完整送審、退回、通過、刪除流程，以及錯誤登入、角色權限、他人稿件隔離、CSRF、欄位驗證及 HTML 跳脫。

`.env`、虛擬環境與快取由 `.gitignore` 排除，不上傳 GitHub。

## 開發紀錄

- 分析 PPT 與課堂資料夾，確認 PostgreSQL 方案，建立需求紀錄。
- 完成表單、Session 登入、作者與編輯功能、基本 CSS 與確認視窗。
- 事件迴圈與終端機中文編碼問題。PostgreSQL 整合測試 2 項通過，瀏覽器確認登入及新增投稿表單。
