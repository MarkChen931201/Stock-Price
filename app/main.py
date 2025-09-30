from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import ssl
import yfinance as yf
import pandas as pd
import joblib

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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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

@app.post("/predict")
async def predict(features: list):
    try:
        predictions = model.predict(features)
        return {"predictions": predictions.tolist()}
    except Exception as e:
        return {"error": str(e)}
