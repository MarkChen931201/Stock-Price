from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import ssl
import yfinance as yf
import pandas as pd
import joblib
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# 設置模板目錄，使用絕對路徑
template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

# 設置靜態文件目錄，使用絕對路徑
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 設定 SSL 上下文，忽略憑證驗證
ssl._create_default_https_context = ssl._create_unverified_context

# 載入預訓練模型
model = joblib.load("model.pkl")

# 定義 Pydantic 模型來驗證輸入資料
class PredictRequest(BaseModel):
    features: list

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/get_stock_price")
async def get_stock_price(stock_code: str):
    try:
        stock = yf.Ticker(stock_code)
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist["Close"].iloc[-1]
            return {"stock_code": stock_code, "price": price}
        else:
            return {"error": "No data found for the given stock code."}
    except Exception as e:
        return {"error": str(e)}

@app.get("/get_stock_trend")
async def get_stock_trend(stock_code: str):
    try:
        stock = yf.Ticker(stock_code)
        hist = stock.history(period="1mo")
        if not hist.empty:
            hist.reset_index(inplace=True)
            hist["Date"] = hist["Date"].dt.strftime("%Y-%m-%d")
            return {"stock_code": stock_code, "history": hist.to_dict(orient="records")}
        else:
            return {"error": "No data found for the given stock code."}
    except Exception as e:
        return {"error": str(e)}

@app.get("/get_stock_data")
async def get_stock_data(stock_code: str):
    """一次取得目前收盤價與近一個月趨勢資料。"""
    try:
        stock = yf.Ticker(stock_code)
        hist = stock.history(period="1mo")
        if hist.empty:
            return {"error": "No data found for the given stock code."}

        # 取得最新收盤價（使用同一份資料的最後一筆）
        latest_close = float(hist["Close"].iloc[-1])

        # 準備趨勢資料
        hist_reset = hist.reset_index()
        if isinstance(hist_reset.loc[0, "Date"], pd.Timestamp):
            hist_reset["Date"] = hist_reset["Date"].dt.strftime("%Y-%m-%d")

        return {
            "stock_code": stock_code,
            "price": latest_close,
            "history": hist_reset.to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/predict")
async def predict(request: PredictRequest):
    try:
        predictions = model.predict(request.features)
        return {"predictions": predictions.tolist()}
    except Exception as e:
        return {"error": str(e)}

@app.get("/predict_stock")
async def predict_stock(stock_code: str):
    """預測股票未來價格"""
    try:
        # 取得歷史資料作為特徵
        stock = yf.Ticker(stock_code)
        hist = stock.history(period="1mo")
        
        if hist.empty:
            return {"error": "No data found for the given stock code."}
        
        # 準備特徵資料 - 使用最近4天的收盤價作為特徵（匹配模型訓練時的特徵數量）
        recent_prices = hist["Close"].tail(4).values.reshape(1, -1)
        
        # 使用模型進行預測
        predictions = model.predict(recent_prices)
        
        # 計算預測漲跌幅
        current_price = float(hist["Close"].iloc[-1])
        predicted_price = float(predictions[0])
        price_change_pct = ((predicted_price - current_price) / current_price) * 100
        
        return {
            "stock_code": stock_code,
            "current_price": round(current_price, 2),
            "predicted_price": round(predicted_price, 2),
            "price_change": round(predicted_price - current_price, 2),
            "price_change_pct": round(price_change_pct, 2),
            "predictions": [round(predicted_price, 2)]
        }
    except Exception as e:
        return {"error": f"預測失敗: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
