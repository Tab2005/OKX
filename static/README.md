AI 輔助多交易所市場掃描器
這是一個使用 Python 開發的 Web 應用程式，旨在掃描多個加密貨幣交易所（OKX, Binance）的現貨與合約市場，利用技術分析形態（三角收斂、W底、上升三角形）篩選出潛在的交易機會，並整合 Gemini AI 提供即時的市場情境分析。

核心架構
本專案採用現代化的前後端分離架構：

後端 (Backend):

Web 框架: Flask (用於提供 API 服務)

背景任務: Celery (搭配 Eventlet，用於處理耗時的掃描任務)

訊息代理: Redis (Celery 的任務佇列與結果儲存)

核心邏輯: tasks.py 包含了所有與交易所 API 的互動、技術形態分析、以及與 Gemini AI 的串接。

前端 (Frontend):

一個單純的 static/index.html 檔案。

樣式: Tailwind CSS

互動: 原生 JavaScript (透過 fetch 與後端 API 溝通)

主要功能
多交易所支援: 可同時掃描 OKX 與 Binance。

多市場支援: 支援現貨 (Spot) 與永續合約 (Swap/Perpetual) 市場。

多形態分析:

三角收斂 (Symmetrical Triangle)

W底反彈 (Double Bottom)

上升三角形 (Ascending Triangle)

進場策略偵測: 可區分形態是「正在形成 (forming)」還是「剛剛突破 (breakout)」。

AI 輔助決策: 對於突破訊號，可一鍵呼叫 Gemini AI 進行即時的市場情緒與新聞分析。

雲端部署: 已適配 Render.com 的雲端部署環境，可 7x24 小時運行。

本地開發設定與執行指南
1. 必要條件
請確保您的電腦已安裝以下軟體：

Python 3.10+

Git

Docker Desktop

2. 首次設定流程
# 1. 從 GitHub 下載專案
git clone [您的專案 Git URL]
cd [您的專案資料夾]

# 2. 建立並啟用 Python 虛擬環境
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# 3. 複製並設定您的 API 金鑰
# 將 env.example 複製為 .env
# 然後用文字編輯器打開 .env，貼上您自己的 Gemini API 金鑰
# Windows:
copy .env.example .env
# macOS/Linux:
# cp .env.example .env

# 4. 安裝所有必要的 Python 函式庫
pip install -r requirements.txt

3. 每日執行流程
您需要啟動三個服務，建議分別在三個獨立的終端機視窗中執行。

a. 啟動 Redis 服務 (透過 Docker)

# 確保 Docker Desktop 正在執行
# 首次執行請用 run，之後只需要在 Docker 圖形介面中 start 即可
docker run -d --name my-redis-stack -p 6379:6379 redis/redis-stack:latest

b. 啟動 Celery 背景工人 (終端機一)

# (務必先啟用虛擬環境)
celery -A tasks.celery_app worker -l info -P eventlet

c. 啟動 Flask API 伺服器 (終端機二)

# (務必先啟用虛擬環境)
python app.py

d. 啟動前端介面

在您的檔案總管中，找到 static/ 資料夾。

直接用您的瀏覽器 (Chrome, Edge) 打開 index.html 檔案。

部署到雲端
本專案已包含 render.yaml 設定檔，可直接部署至 Render.com。