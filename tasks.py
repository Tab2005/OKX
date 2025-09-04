import sys
import os

# 只有當這個檔案是被 Celery worker 執行時，才進行 monkey_patch
if 'celery' in sys.argv[0]:
    import eventlet
    eventlet.monkey_patch()

import time
import requests
import numpy as np
from celery import Celery, states
from celery.exceptions import Ignore
from dotenv import load_dotenv
import json

# 讀取 .env 檔案
load_dotenv()

# --- 設定 Celery ---
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery_app = Celery('tasks', broker=redis_url, backend=redis_url)

# --- 轉接頭架構 ---
class BaseExchange:
    def __init__(self): self.name = "Base Exchange"
    def get_instruments_by_quote(self, quote_currency, market_type='spot'): raise NotImplementedError
    def get_kline_data(self, instrument_id, timeframe, market_type='spot', limit=100): raise NotImplementedError

class OkxAdapter(BaseExchange):
    def __init__(self):
        super().__init__(); self.name = "OKX"; self.base_url = "https://www.okx.com"
    def get_instruments_by_quote(self, quote_currency, market_type='spot'):
        url = self.base_url + "/api/v5/public/instruments"
        inst_type = 'SPOT' if market_type == 'spot' else 'SWAP'
        params = {'instType': inst_type}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status(); data = response.json()
            if data.get('code') == '0':
                instruments_data = data.get('data', []); quote = quote_currency.upper()
                if market_type == 'spot':
                    filter_suffix = f'-{quote}'
                    return [item['instId'] for item in instruments_data if item['instId'].endswith(filter_suffix)]
                else:
                    filter_suffix = f'-{quote}-SWAP'
                    return [item['instId'] for item in instruments_data if item['instId'].endswith(filter_suffix)]
            else: print(f"[ERROR] OKX API returned an error: {data.get('msg')}")
        except requests.exceptions.RequestException as e: print(f"[ERROR] OKX API request failed: {e}")
        return None
    def get_kline_data(self, instrument_id, timeframe, market_type='spot', limit=100):
        url = self.base_url + "/api/v5/market/history-candles"
        params = {'instId': instrument_id, 'bar': timeframe, 'limit': str(limit)}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status(); data = response.json()
            if data.get('code') == '0': return data.get('data', [])
        except requests.exceptions.RequestException as e: print(f"\n[ERROR] Failed to get kline for {instrument_id} from OKX: {e}")
        return None

class BinanceAdapter(BaseExchange):
    def __init__(self):
        super().__init__(); self.name = "Binance"; self.spot_url = "https://api.binance.com/api/v3"; self.futures_url = "https://fapi.binance.com/fapi/v1"
    def get_instruments_by_quote(self, quote_currency, market_type='spot'):
        url = self.spot_url + "/exchangeInfo" if market_type == 'spot' else self.futures_url + "/exchangeInfo"
        try:
            response = requests.get(url, timeout=10); response.raise_for_status(); data = response.json(); quote = quote_currency.upper()
            if market_type == 'spot': return [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING' and s['quoteAsset'] == quote]
            else: return [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING' and s['quoteAsset'] == quote and s['contractType'] == 'PERPETUAL']
        except requests.exceptions.RequestException as e: print(f"[ERROR] Binance API request failed: {e}")
        return None
    def get_kline_data(self, instrument_id, timeframe, market_type='spot', limit=100):
        url = self.spot_url + "/klines" if market_type == 'spot' else self.futures_url + "/klines"
        timeframe_map = {"5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"}
        api_timeframe = timeframe_map.get(timeframe, "1h")
        params = {'symbol': instrument_id, 'interval': api_timeframe, 'limit': str(limit)}
        try:
            response = requests.get(url, params=params, timeout=10); response.raise_for_status(); return response.json()
        except requests.exceptions.RequestException as e: print(f"\n[ERROR] Failed to get kline for {instrument_id} from Binance: {e}")
        return None

# --- 分析模組 ---
def analyze_triangle_consolidation(kline_data, period=60): #...
    if not kline_data or len(kline_data) < period: return False, None, "K 線數據不足"
    recent_klines = kline_data[:period]; highs = np.array([float(k[2]) for k in recent_klines]); lows = np.array([float(k[3]) for k in recent_klines]); closes = np.array([float(k[4]) for k in recent_klines]); x = np.arange(len(highs)); highs_slope, highs_intercept = np.polyfit(x, highs, 1); lows_slope, lows_intercept = np.polyfit(x, lows, 1); first_half_range = np.max(highs[period//2:]) - np.min(lows[period//2:]); second_half_range = np.max(highs[:period//2]) - np.min(lows[:period//2]); is_volatility_decreasing = second_half_range < first_half_range
    if highs_slope < 0 and lows_slope > 0 and is_volatility_decreasing:
        resistance_level = highs_intercept; support_level = lows_intercept; latest_close = closes[0]
        if latest_close > resistance_level: return True, "breakout_up", f"三角收斂 向上突破! 壓力線: {resistance_level:.4f}"
        elif latest_close < support_level: return True, "breakout_down", f"三角收斂 向下跌破! 支撐線: {support_level:.4f}"
        else: return True, "forming", f"符合三角收斂 (壓力:{resistance_level:.4f} / 支撐:{support_level:.4f})"
    return False, None, "不符合三角收斂"
def analyze_double_bottom(kline_data, period=60): #...
    if not kline_data or len(kline_data) < period: return False, None, "K 線數據不足"
    recent_klines = kline_data[:period]; lows = np.array([float(k[3]) for k in recent_klines]); closes = np.array([float(k[4]) for k in recent_klines]); third = period // 3; low_1_price = np.min(lows[2*third:]); peak_price = np.max(closes[third:2*third]); low_2_price = np.min(lows[:third]); are_lows_similar = abs(low_1_price - low_2_price) / low_1_price < 0.03; avg_low_price = (low_1_price + low_2_price) / 2; is_peak_significant = (peak_price - avg_low_price) / avg_low_price > 0.05; is_rebounding = closes[0] > low_2_price
    if are_lows_similar and is_peak_significant and is_rebounding:
        neckline = peak_price; latest_close = closes[0]
        if latest_close > neckline: return True, "breakout_up", f"W底 頸線突破! 頸線: {neckline:.4f}"
        else: return True, "forming", f"符合 W 底 (等待突破頸線 {neckline:.4f})"
    return False, None, "不符合 W 底"
def analyze_ascending_triangle(kline_data, period=60): #...
    if not kline_data or len(kline_data) < period: return False, None, "K 線數據不足"
    recent_klines = kline_data[:period]; highs = np.array([float(k[2]) for k in recent_klines]); lows = np.array([float(k[3]) for k in recent_klines]); closes = np.array([float(k[4]) for k in recent_klines]); x = np.arange(len(highs)); highs_slope, _ = np.polyfit(x, highs, 1); lows_slope, _ = np.polyfit(x, lows, 1); is_lows_rising = lows_slope > 0; is_highs_flat = abs(highs_slope) < (lows_slope * 0.25)
    if is_lows_rising and is_highs_flat:
        resistance_level = np.mean(highs[:period//2]); latest_close = closes[0]
        if latest_close > resistance_level: return True, "breakout_up", f"上升三角形 壓力線突破! 壓力線: {resistance_level:.4f}"
        else: return True, "forming", f"符合上升三角形 (等待突破 {resistance_level:.4f})"
    return False, None, "不符合上升三角形"

# --- 函式庫/工具箱 ---
ANALYSIS_FUNCTIONS = {"triangle": analyze_triangle_consolidation, "double_bottom": analyze_double_bottom, "ascending_triangle": analyze_ascending_triangle}
EXCHANGE_ADAPTERS = {"okx": OkxAdapter, "binance": BinanceAdapter}
PATTERN_GROUPS = {"long_patterns": ["triangle", "double_bottom", "ascending_triangle"]}

# --- 背景任務 ---
@celery_app.task(bind=True)
def run_scan_task(self, exchange_name, market_type, quote, timeframe, pattern, limit=None):
    # ... (此函式保持不變) ...
    exchange_class = EXCHANGE_ADAPTERS[exchange_name]; exchange_adapter = exchange_class()
    pairs = exchange_adapter.get_instruments_by_quote(quote, market_type=market_type)
    if not pairs:
        self.update_state(state=states.FAILURE, meta={'exc': f'Could not fetch instrument list from {exchange_adapter.name}.'}); raise Ignore()
    pairs_to_scan = pairs[:limit] if limit else pairs; total_pairs = len(pairs_to_scan)
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': total_pairs, 'status': 'Initializing...'})
    found_list = []; patterns_to_check = PATTERN_GROUPS.get(pattern, [pattern])
    for i, pair in enumerate(pairs_to_scan):
        kline_data = exchange_adapter.get_kline_data(pair, timeframe=timeframe, market_type=market_type, limit=60)
        if kline_data:
            for pattern_name in patterns_to_check:
                selected_analysis_func = ANALYSIS_FUNCTIONS[pattern_name]
                is_pattern, status, description = selected_analysis_func(kline_data)
                if is_pattern:
                    found_list.append({"exchange": exchange_adapter.name, "market": market_type, "pair": pair, "timeframe": timeframe, "status": status, "description": description}); break
        self.update_state(state='PROGRESS', meta={'current': i + 1, 'total': total_pairs, 'status': f'Scanning {pair}'}); time.sleep(0.1)
    return {'current': total_pairs, 'total': total_pairs, 'status': 'Scan Complete!', 'result': found_list}

@celery_app.task
def get_gemini_analysis_task(signal_info):
    """呼叫 Gemini API 的背景任務。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return "AI 分析失敗：找不到 GEMINI_API_KEY 環境變數。"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
    prompt = f"""您是一位專業的加密貨幣市場分析師。一個交易訊號剛剛在 {signal_info['timeframe']} 線圖上被偵測到。
- **交易所**: {signal_info['exchange']} ({signal_info['market']} 市場)
- **交易對**: {signal_info['pair']}
- **訊號**: {signal_info['description']}
請基於最新的市場新聞與數據 (透過 Google 搜尋)，提供一份簡潔的分析報告，包含以下幾點：
1.  **目前市場情緒**: 市場對此資產的普遍看法是看漲、看跌還是中性？
2.  **相關新聞**: 有沒有任何可能支持或反駁此技術訊號的近期新聞？
3.  **潛在風險**: 在根據此訊號進行交易前，應考慮哪些立即性的風險？
請以條列式重點摘要回覆。"""
    payload = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=30)
        response.raise_for_status(); result = response.json()
        if "candidates" in result and result["candidates"]: return result["candidates"][0]["content"]["parts"][0]["text"]
        return "AI 分析失敗：模型未返回有效內容。"
    except requests.exceptions.RequestException as e: return f"AI 分析失敗：API 請求錯誤 - {e}"
    except (KeyError, IndexError) as e: return f"AI 分析失敗：無法解析 API 回應 - {e}"
