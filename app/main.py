from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import ssl
import yfinance as yf
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pandas_datareader import data as pdr
from datetime import datetime, timedelta
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
# ---- 全域 Session 與簡易快取 ----
# 以全域 requests.Session 重用連線、降低 TLS 交握與 DNS 開銷
def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    })
    retry = Retry(
        total=2,  # 降低重試次數，避免 429 時拖慢
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

SESSION = _build_session()

# 簡易 TTL 快取，避免短時間重複請求外部來源
from time import time as _now
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
_CACHE: dict[tuple, dict] = {}

def _cache_get(key: tuple):
    item = _CACHE.get(key)
    if not item:
        return None
    if item["expire_at"] < _now():
        _CACHE.pop(key, None)
        return None
    return item["data"]

def _cache_set(key: tuple, data, ttl: int = CACHE_TTL_SECONDS):
    _CACHE[key] = {"expire_at": _now() + ttl, "data": data}


# 定義 Pydantic 模型來驗證輸入資料
class PredictRequest(BaseModel):
    features: list

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# ---- 資料抓取工具函式（具備多重備援） ----
def _period_to_start_end(period: str):
    """將 period 字串轉換為 start/end 日期（用於 Stooq 備援）。"""
    now = datetime.utcnow().date()
    period = (period or "1mo").lower()
    mapping = {
        "1d": 1,
        "5d": 7,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 365 * 5,
        "10y": 365 * 10,
        "ytd": 365,  # 近一年作為近似
        "max": 365 * 30,  # 近30年作為近似
    }
    days = mapping.get(period, 30)
    start = now - timedelta(days=days)
    end = now
    return start, end


def fetch_history_with_fallback(stock_code: str, period: str = "1mo") -> pd.DataFrame:
    """先用 yfinance.download 嘗試，失敗或為空時改用 Stooq (pandas-datareader)。"""
    # 1) yfinance.download 路徑（可帶自訂 session 和重試）
    try:
        df = yf.download(
            tickers=stock_code,
            period=period,
            progress=False,
            auto_adjust=False,
            threads=False,
            session=SESSION,
        )
        if isinstance(df, pd.DataFrame) and not df.empty:
            # yfinance 可能回傳 MultiIndex 欄，這裡展平成單層
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            return df
    except Exception:
        pass

    # 2) Stooq 備援：不需要金鑰，穩定性高，但資料更新略有延遲
    try:
        start, end = _period_to_start_end(period)
        df = pdr.DataReader(stock_code, "stooq", start=start, end=end)
        if isinstance(df, pd.DataFrame) and not df.empty:
            # stooq 回傳為降冪日期，轉為升冪
            df = df.sort_index()
            # 欄位名稱大小寫標準化
            df.columns = [col.capitalize() for col in df.columns]
            return df
    except Exception:
        pass

    # 3) 最後嘗試舊的 Ticker().history 做一次（有時候反而會成功）
    try:
        t = yf.Ticker(stock_code)
        df = t.history(period=period, timeout=30)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    except Exception:
        pass

    # 全部失敗則回傳空 DataFrame
    return pd.DataFrame()

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
async def get_stock_data(stock_code: str, period: str = "1mo"):
    """取得股票資料，支援不同時間範圍，內建多來源備援避免 429/封鎖。"""
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Fetching data for {stock_code} with period {period}")

    # 先查快取
    cache_key = (stock_code.upper(), period)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    hist = fetch_history_with_fallback(stock_code, period)
    if hist is None or hist.empty:
        return {"error": f"無法獲取股票 {stock_code} 的歷史資料。可能是資料來源限制（429）或網路問題，稍後再試。"}

    # 取得最新收盤價
    latest_close = float(hist["Close"].iloc[-1])

    # 準備趨勢資料
    hist_reset = hist.reset_index()
    # 將日期欄位標準化為字串
    date_col = None
    for candidate in ["Date", "date", "Datetime", "index"]:
        if candidate in hist_reset.columns:
            date_col = candidate
            break
    if date_col is None:
        # 若沒找到日期欄，使用第一欄
        date_col = hist_reset.columns[0]
    if isinstance(hist_reset.loc[0, date_col], (pd.Timestamp, datetime)):
        hist_reset[date_col] = pd.to_datetime(hist_reset[date_col]).dt.strftime("%Y-%m-%d")
    # 為前端統一名稱為 Date
    if date_col != "Date":
        hist_reset.rename(columns={date_col: "Date"}, inplace=True)

    # 計算統計資訊
    price_change = float(hist["Close"].iloc[-1] - hist["Close"].iloc[0])
    price_change_pct = (price_change / float(hist["Close"].iloc[0])) * 100

    logger.info(f"Successfully fetched data for {stock_code}")
    resp = {
        "stock_code": stock_code,
        "price": round(latest_close, 2),
        "price_change": round(price_change, 2),
        "price_change_pct": round(price_change_pct, 2),
        "period": period,
        "history": hist_reset.to_dict(orient="records"),
    }
    _cache_set(cache_key, resp)
    return resp

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
        # 取得歷史資料作為特徵（使用與上面一致的備援機制）
        hist = fetch_history_with_fallback(stock_code, period="1mo")
        if hist is None or hist.empty:
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
