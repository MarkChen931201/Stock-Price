import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib
import os
import sys

# 爬取數據
def fetch_data(stock_code):
    stock = yf.Ticker(stock_code)
    hist = stock.history(period="6mo")
    hist.reset_index(inplace=True)
    hist["Date"] = pd.to_datetime(hist["Date"])
    return hist

# 擴展特徵
def expand_features(data):
    data["SMA_5"] = data["Close"].rolling(window=5).mean()  # 5日移動平均線
    data["SMA_10"] = data["Close"].rolling(window=10).mean()  # 10日移動平均線
    data["Volatility"] = data["Close"].rolling(window=5).std()  # 5日波動率
    data.dropna(inplace=True)  # 移除包含 NaN 的行
    return data

# 更新準備數據函數以包含擴展特徵和特徵選擇
def prepare_data(data):
    data = expand_features(data)
    data["Future_Close"] = data["Close"].shift(-1)
    data.dropna(inplace=True)

    # 特徵選擇
    feature_columns = ["Close", "SMA_5", "SMA_10", "Volatility"]
    X = data[feature_columns]
    y = data["Future_Close"]

    return train_test_split(X, y, test_size=0.2, random_state=42)

# 訓練模型並輸出特徵重要性
def train_model(X_train, y_train):
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 輸出特徵重要性
    feature_importances = model.feature_importances_
    for feature, importance in zip(X_train.columns, feature_importances):
        print(f"特徵: {feature}, 重要性: {importance}")

    return model

# 確保保存模型的路徑正確處理空格
model_path = os.path.join(os.getcwd(), "model.pkl")

if __name__ == "__main__":
    # 確保路徑處理正確，避免空格問題
    script_path = os.path.abspath(__file__)
    sys.path.append(os.path.dirname(script_path))

    stock_code = "AAPL"  # 替換為你想要的股票代碼
    data = fetch_data(stock_code)
    X_train, X_test, y_train, y_test = prepare_data(data)

    model = train_model(X_train, y_train)

    # 評估模型
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print(f"模型均方誤差: {mse}")

    # 保存模型
    joblib.dump(model, model_path)
    print(f"模型已保存為 {model_path}")
