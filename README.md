# 🚀 股價預測系統 Docker 部署指南

## 📋 專案概述

這是一個基於FastAPI和機器學習的股價預測系統，支援46支熱門股票的即時查詢、K線圖顯示和AI預測功能。

## 🎯 功能特色

- 📊 **即時股價查詢**：支援46支美股
- 📈 **專業K線圖**：手繪Canvas K棒圖表
- 🔮 **AI股價預測**：機器學習模型預測
- ⭐ **收藏功能**：本地儲存常用股票
- 🎨 **財務風格UI**：專業金融界面設計
- ⏰ **多時間範圍**：1週到1年的歷史數據

## 🐳 Docker 快速部署

### 方法一：使用部署腳本（推薦）

```bash
# 構建並運行（一鍵部署）
./deploy.sh

# 或者指定版本
./deploy.sh v1.0

# 僅構建映像
./deploy.sh latest build

# 僅運行容器
./deploy.sh latest run

# 查看狀態
./deploy.sh latest status
```

### 方法二：使用 Docker Compose

```bash
# 構建並啟動
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down
```

### 方法三：手動 Docker 命令

```bash
# 1. 構建映像
docker build -t stock-price-predictor .

# 2. 運行容器
docker run -d \
  --name stock-price-app \
  -p 8000:8000 \
  --restart unless-stopped \
  stock-price-predictor

# 3. 查看狀態
docker ps
```

## 🌐 訪問應用

部署成功後，在瀏覽器中訪問：
- **應用界面**：http://localhost:8000
- **API文檔**：http://localhost:8000/docs
- **健康檢查**：http://localhost:8000/health

## 🌍 透過 Nginx + DuckDNS 反向代理（HTTPS）

以下配置讓你使用 DuckDNS 網域（例如 `myhome.duckdns.org`）+ Let's Encrypt 憑證，將外網 443/80 反向代理到 FastAPI：

1) 申請 DuckDNS 網域與 Token（https://www.duckdns.org/）

2) 編輯 `nginx/conf.d/stock-price.conf`
- 將 `YOUR_DUCKDNS_DOMAIN` 替換為你的網域（例：`myhome.duckdns.org`）。

3) 建立 `.env` 檔案（放在專案根目錄），內容包含：
```
DUCKDNS_SUBDOMAINS=myhome
DUCKDNS_TOKEN=你的DuckDNS Token
DOMAIN=myhome.duckdns.org
EMAIL=你用於申請憑證的Email
```

4) 啟動服務（先讓 nginx 起來）
```bash
docker compose up -d nginx duckdns stock-price-app
```

5) 首次簽發憑證（webroot 模式）
```bash
DOMAIN=$DOMAIN EMAIL=$EMAIL bash scripts/init-letsencrypt.sh
```

6) 啟動自動續期服務（每天固定嘗試續期）
```bash
docker compose up -d certbot
```

完成後，瀏覽器以 `https://myhome.duckdns.org/` 存取，即由 Nginx 反代到後端 `stock-price-app:8000`。

注意：你的路由器/雲主機需將 80/443 端口轉發到此機器；若在 macOS 本機，請確保 Docker Desktop 未被其他服務佔用 80/443。

## 🛠️ Docker 管理命令

```bash
# 查看容器狀態
docker ps

# 查看應用日誌
docker logs stock-price-app

# 進入容器
docker exec -it stock-price-app bash

# 重啟容器
docker restart stock-price-app

# 停止並刪除容器
docker stop stock-price-app
docker rm stock-price-app

# 刪除映像
docker rmi stock-price-predictor
```

## 📁 專案結構

```
Stock-Price/
├── app/                    # 應用程式代碼
│   ├── main.py            # FastAPI 主程式
│   ├── static/            # 靜態文件
│   └── templates/         # HTML 模板
├── model.pkl              # 訓練好的ML模型
├── requirements.txt       # Python依賴
├── Dockerfile            # Docker映像定義
├── docker-compose.yml    # Docker Compose配置
├── deploy.sh             # 部署腳本
└── .dockerignore         # Docker忽略文件
```

## 🔧 環境變數

| 變數名 | 預設值 | 說明 |
|--------|--------|------|
| `PYTHONPATH` | `/app` | Python模組路徑 |
| `PYTHONUNBUFFERED` | `1` | 不緩衝輸出 |

## 📊 支援股票

**科技巨頭**：AAPL, GOOGL, MSFT, META, AMZN 等
**半導體**：NVDA, AMD, INTC, TSM, QCOM 等
**金融服務**：JPM, BAC, V, MA, PYPL 等
**電動車**：TSLA, F, GM, RIVN, LCID 等
**中概股**：BABA, JD, PDD, BIDU, NIO 等

## 🚨 故障排除

### 常見問題

1. **端口佔用**
```bash
# 查找佔用8000端口的進程
lsof -i :8000
# 殺死進程
kill -9 <PID>
```

2. **模型文件缺失**
```bash
# 確保model.pkl存在
ls -la model.pkl
```

3. **容器無法啟動**
```bash
# 查看詳細日誌
docker logs stock-price-app
```

4. **顯示「無法獲取股票歷史資料」或 429**

Yahoo 可能在短時間大量請求時回應 429（流量限制）。本專案已內建多來源備援：

- 首選 yfinance（Yahoo Finance）
- 備援使用 Stooq（pandas-datareader）

若仍遇到暫時性錯誤，請隔幾分鐘再嘗試，或更換網路環境。

## 🎯 API 端點

- `GET /` - 主頁面
- `GET /health` - 健康檢查
- `GET /get_stock_data` - 獲取股票數據
- `GET /predict_stock` - 股價預測

## 🏷️ 版本標籤

推薦的Docker標籤命名：
- `stock-price-predictor:latest` - 最新版本
- `stock-price-predictor:v1.0` - 穩定版本
- `stock-price-predictor:dev` - 開發版本

## 📞 支援

如有問題，請檢查：
1. Docker是否正確安裝
2. 端口8000是否可用
3. 模型文件是否存在
4. 網路連接是否正常（用於股票數據獲取）