import requests
import sys
import time
import numpy as np
from tqdm import tqdm
import argparse

# --- API 端點 ---
INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"
KLINE_URL = "https://www.okx.com/api/v5/market/history-candles"

# --- 數據獲取函式 ---
def get_spot_instruments_by_quote(quote_currency):
    """從 OKX API 獲取指定報價貨幣的現貨交易對列表。"""
    params = {'instType': 'SPOT'}
    try:
        response = requests.get(INSTRUMENTS_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('code') == '0':
            instruments_data = data.get('data', [])
            filter_suffix = f'-{quote_currency.upper()}'
            instrument_ids = [item['instId'] for item in instruments_data if item['instId'].endswith(filter_suffix)]
            return instrument_ids
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def get_kline_data(instrument_id, timeframe='1H', limit='100'):
    """為指定的交易對獲取 K 線數據。"""
    params = {
        'instId': instrument_id,
        'bar': timeframe,
        'limit': limit
    }
    try:
        response = requests.get(KLINE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('code') == '0':
            return data.get('data', [])
        else:
            print(f"\n警告：無法獲取 {instrument_id} 的 K 線數據。原因：{data.get('msg')}")
            return None
    except requests.exceptions.RequestException:
        return None

# --- 分析模組 ---

def analyze_triangle_consolidation(kline_data, period=60):
    """分析 K 線數據是否符合三角收斂的簡化模型。"""
    if not kline_data or len(kline_data) < period:
        return False, "K 線數據不足"
    recent_klines = kline_data[:period]
    highs = np.array([float(k[2]) for k in recent_klines])
    lows = np.array([float(k[3]) for k in recent_klines])
    x = np.arange(len(highs))
    highs_slope, _ = np.polyfit(x, highs, 1)
    lows_slope, _ = np.polyfit(x, lows, 1)
    first_half_range = np.max(highs[period//2:]) - np.min(lows[period//2:])
    second_half_range = np.max(highs[:period//2]) - np.min(lows[:period//2])
    is_volatility_decreasing = second_half_range < first_half_range
    if highs_slope < 0 and lows_slope > 0 and is_volatility_decreasing:
        return True, f"符合三角收斂: 高點趨勢向下 (斜率: {highs_slope:.6f}), 低點趨勢向上 (斜率: {lows_slope:.6f})"
    else:
        return False, "不符合三角收斂"

def analyze_double_bottom(kline_data, period=60):
    """分析 K 線數據是否符合 W 底 (Double Bottom) 的簡化模型。"""
    if not kline_data or len(kline_data) < period:
        return False, "K 線數據不足"

    recent_klines = kline_data[:period]
    lows = np.array([float(k[3]) for k in recent_klines])
    close_prices = np.array([float(k[4]) for k in recent_klines])
    
    third = period // 3
    
    low_1_index = np.argmin(lows[2*third:])
    low_1_price = lows[2*third:][low_1_index]
    
    peak_index = np.argmax(close_prices[third:2*third])
    peak_price = close_prices[third:2*third][peak_index]
    
    low_2_index = np.argmin(lows[:third])
    low_2_price = lows[:third][low_2_index]

    are_lows_similar = abs(low_1_price - low_2_price) / low_1_price < 0.03
    avg_low_price = (low_1_price + low_2_price) / 2
    is_peak_significant = (peak_price - avg_low_price) / avg_low_price > 0.05
    is_rebounding = close_prices[0] > low_2_price

    if are_lows_similar and is_peak_significant and is_rebounding:
        desc = f"符合 W 底: 兩個低點約為 {avg_low_price:.4f}, 頸線高點為 {peak_price:.4f}"
        return True, desc
    else:
        return False, "不符合 W 底"

# --- 分析函式庫 (工具箱) ---
ANALYSIS_FUNCTIONS = {
    "triangle": analyze_triangle_consolidation,
    "double_bottom": analyze_double_bottom, # <--- 已新增 W底 工具
}

# --- 主程式執行區 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OKX 市場形態掃描器 v3.1")
    parser.add_argument("quote", help="您想掃描的報價貨幣，例如: USDT, BTC")
    parser.add_argument("--timeframe", default="1H", help="K 線時框 (例如: 15m, 1H, 4H, 1D)")
    parser.add_argument("--pattern", default="triangle", choices=ANALYSIS_FUNCTIONS.keys(), help="您想尋找的技術形態")
    parser.add_argument("--limit", type=int, help="要掃描的交易對數量 (預設為全部)")
    
    args = parser.parse_args()
    
    pairs = get_spot_instruments_by_quote(args.quote)
    
    if not pairs:
        print(f"未能獲取任何 {args.quote.upper()} 交易對，程式退出。")
        sys.exit()

    pairs_to_scan = pairs
    if args.limit:
        pairs_to_scan = pairs[:args.limit]
    
    print(f"\n掃描目標：{len(pairs_to_scan)} 個 {args.quote.upper()} 交易對")
    print(f"掃描時框：{args.timeframe}")
    print(f"尋找形態：{args.pattern}")
    
    selected_analysis_func = ANALYSIS_FUNCTIONS[args.pattern]
    
    found_list = []
    for pair in tqdm(pairs_to_scan, desc="掃描進度"):
        kline_data = get_kline_data(pair, timeframe=args.timeframe, limit='60')
        
        if kline_data:
            is_pattern, description = selected_analysis_func(kline_data)
            
            if is_pattern:
                result_string = f"✅ {pair}: {description}"
                found_list.append(result_string)

        time.sleep(0.1)

    print("\n" + "="*50)
    print("掃描完成！")
    if found_list:
        print(f"共找到 {len(found_list)} 個符合條件的目標：")
        for result in found_list:
            print(result)
    else:
        print("未找到符合條件的目標。")
    print("="*50)