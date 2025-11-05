# 使用官方Python 3.11 slim基礎映像
FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴（包含網路工具和CA證書）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    ca-certificates \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製requirements文件
COPY requirements.txt .

# 安裝Python依賴
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建非root用戶並設置快取目錄
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    mkdir -p /home/app/.cache && \
    chown -R app:app /home/app/.cache
USER app

# 暴露端口
EXPOSE 8000

# 設置環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 啟動命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]