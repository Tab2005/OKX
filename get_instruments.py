import requests
import sys
import time
import numpy as np
from tqdm import tqdm

# --- API 端點 ---
INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"
KLINE_URL = "https://www.okx.com/api/v5/market/history-candles"

# ... (上方的函式 get_spot_instruments_by_quote, get_kline_data, analyze_triangle_consolidation 保持不變，此處省略) ...
def get_spot_instruments_by_quote(quote_currency):
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

def analyze_triangle_consolidation(kline_data, period=60):
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


# --- 主程式執行區 (已修改) ---
if __name__ == "__main__":
    # vvv --- 新增的輔助說明邏輯 --- vvv
    # 檢查使用者是否提供了至少一個必要的參數（報價貨幣）
    if len(sys.argv) < 2:
        # 如果沒有，就印出詳細的使用說明
        print("\n" + "="*60)
        print(" 掃描器指令用法說明：")
        print("   python get_instruments.py [報價貨幣] [掃描數量(可選)]")
        print("\n [參數說明]")
        print("   [報價貨幣]: (必須) 您想掃描的交易對類型。範例: USDT, BTC, TWD")
        print("   [掃描數量]: (可選) 您想掃描的交易對數量。若不提供，則掃描全部。")
        print("\n [使用範例]")
        print("   1. 掃描所有 USDT 交易對:")
        print("      python get_instruments.py USDT")
        print("\n   2. 掃描前 20 個 BTC 交易對:")
        print("      python get_instruments.py BTC 20")
        print("="*60)
        sys.exit() # 顯示完說明後，安全退出程式
    # ^^^ --- 輔助說明邏輯結束 --- ^^^

    # --- 後續的程式碼邏輯與之前版本完全相同 ---
    quote_ccy = sys.argv[1]
    pairs = get_spot_instruments_by_quote(quote_ccy)
    
    if not pairs:
        print(f"未能獲取任何 {quote_ccy.upper()} 交易對，程式退出。")
        sys.exit()

    num_to_process_str = ""
    if len(sys.argv) > 2:
        num_to_process_str = sys.argv[2]

    pairs_to_scan = pairs
    if num_to_process_str:
        try:
            num = int(num_to_process_str)
            pairs_to_scan = pairs[:num]
        except ValueError:
            print(f"警告：數量 '{num_to_process_str}' 不是有效數字，將掃描全部 {len(pairs)} 個交易對。")
    
    print(f"\n共找到 {len(pairs)} 個 {quote_ccy.upper()} 現貨交易對。")
    print(f"開始掃描 {len(pairs_to_scan)} 個交易對的 1 小時 K 線，尋找三角收斂形態...")
    
    found_count = 0
    found_list = []

    for pair in tqdm(pairs_to_scan, desc="掃描進度"):
        kline_data = get_kline_data(pair, timeframe='1H', limit='60')
        
        if kline_data:
            is_pattern, description = analyze_triangle_consolidation(kline_data, period=60)
            
            if is_pattern:
                found_count += 1
                result_string = f"✅ {pair}: {description}"
                found_list.append(result_string)

        time.sleep(0.1)

    print("\n" + "="*50)
    print("掃描完成！")
    if found_count > 0:
        print(f"在 {len(pairs_to_scan)} 個交易對中，共找到 {found_count} 個符合條件的目標：")
        for result in found_list:
            print(result)
    else:
        print(f"在 {len(pairs_to_scan)} 個交易對中，未找到符合條件的目標。")
    print("="*50)