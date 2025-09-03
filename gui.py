import customtkinter as ctk
import threading
import scanner
import tkinter as tk

# --- 介面設定 & 中英對照字典 (保持不變) ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
PATTERN_MAP = {"全部做多型態": "long_patterns", "三角收斂": "triangle", "W底型態": "double_bottom", "上升三角形": "ascending_triangle"}
TIMEFRAME_MAP = {"5分鐘": "5m", "15分鐘": "15m", "30分鐘": "30m", "1小時": "1H", "4小時": "4H", "1天": "1D"}
EXCHANGE_MAP = {"OKX": "okx", "Binance (幣安)": "binance"}
MARKET_MAP = {"現貨市場": "spot", "永續合約": "swap"}
QUOTE_CURRENCIES = ["USDT", "USDC"]

# --- 主視窗 ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 輔助市場掃描器 v3.3")
        self.geometry("600x700")

        self.active_ai_widget = None
        self.active_ai_button = None

        # --- 介面元件 (佈局保持不變) ---
        self.label_exchange = ctk.CTkLabel(self, text="交易所 (Exchange):"); self.label_exchange.pack(pady=(20, 5))
        self.optionmenu_exchange = ctk.CTkOptionMenu(self, values=list(EXCHANGE_MAP.keys())); self.optionmenu_exchange.pack(pady=5)
        self.label_market = ctk.CTkLabel(self, text="市場類型 (Market Type):"); self.label_market.pack(pady=(15, 5))
        self.optionmenu_market = ctk.CTkOptionMenu(self, values=list(MARKET_MAP.keys())); self.optionmenu_market.pack(pady=5)
        self.label_quote = ctk.CTkLabel(self, text="報價貨幣 (Quote Currency):"); self.label_quote.pack(pady=(15, 5))
        self.optionmenu_quote = ctk.CTkOptionMenu(self, values=QUOTE_CURRENCIES); self.optionmenu_quote.pack(pady=5)
        self.label_timeframe = ctk.CTkLabel(self, text="K線時框 (Timeframe):"); self.label_timeframe.pack(pady=(15, 5))
        self.optionmenu_timeframe = ctk.CTkOptionMenu(self, values=list(TIMEFRAME_MAP.keys())); self.optionmenu_timeframe.pack(pady=5)
        self.label_pattern = ctk.CTkLabel(self, text="技術形態 (Pattern):"); self.label_pattern.pack(pady=(15, 5))
        self.optionmenu_pattern = ctk.CTkOptionMenu(self, values=list(PATTERN_MAP.keys())); self.optionmenu_pattern.pack(pady=5)
        self.button_scan = ctk.CTkButton(self, text="開始掃描", command=self.start_scan)
        self.button_scan.pack(pady=20)
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray"); self.status_label.pack()
        self.progress_label = ctk.CTkLabel(self, text="進度: 0%"); self.progress_label.pack()
        self.progressbar = ctk.CTkProgressBar(self, width=400); self.progressbar.set(0); self.progressbar.pack(pady=5)
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="掃描結果")
        self.results_frame.pack(pady=10, padx=10, fill="both", expand=True)

    def start_scan(self):
        quote = self.optionmenu_quote.get(); display_pattern = self.optionmenu_pattern.get(); internal_pattern = PATTERN_MAP[display_pattern]; display_timeframe = self.optionmenu_timeframe.get(); internal_timeframe = TIMEFRAME_MAP[display_timeframe]; display_exchange = self.optionmenu_exchange.get(); internal_exchange = EXCHANGE_MAP[display_exchange]; display_market = self.optionmenu_market.get(); internal_market = MARKET_MAP[display_market]
        self.button_scan.configure(state="disabled", text="掃描中...")
        self.status_label.configure(text="正在獲取交易對列表...")
        self.progressbar.set(0); self.progress_label.configure(text="進度: 0%")
        for widget in self.results_frame.winfo_children(): widget.destroy()
        scan_thread = threading.Thread(target=self.run_scan_in_background, args=(internal_exchange, internal_market, quote, internal_timeframe, internal_pattern))
        scan_thread.start()

    def run_scan_in_background(self, exchange_name, market_type, quote, timeframe, pattern):
        exchange_class = scanner.EXCHANGE_ADAPTERS[exchange_name]
        exchange_adapter = exchange_class()
        results = scanner.run_scan(exchange_adapter, market_type, quote, timeframe, pattern, progress_callback=self.safe_update_progress, count_callback=self.safe_update_count)
        self.after(0, self.update_results_ui, results)

    def update_results_ui(self, results):
        self.status_label.configure(text="掃描完成！")
        if not results: ctk.CTkLabel(self.results_frame, text="未找到符合條件的目標。").pack(padx=10, pady=10)
        else:
            for result in results: self.add_result_widget(result)
        self.button_scan.configure(state="normal", text="開始掃描")

    # vvv --- 唯一的修改點在這裡 --- vvv
    def add_result_widget(self, result_data):
        if result_data['status'] == "breakout_up": emoji = "🔥"
        elif result_data['status'] == "breakout_down": emoji = "💧"
        else: emoji = "⏳"
        result_text = f"{emoji} [{result_data['exchange'].upper()}-{result_data['market'].upper()}] {result_data['pair']}\n{result_data['description']}"
        
        # 調整 1: 增加每個結果項目的上下外邊距
        item_frame = ctk.CTkFrame(self.results_frame)
        item_frame.pack(fill="x", padx=10, pady=(5, 10)) # pady=(上方, 下方)

        result_textbox = ctk.CTkTextbox(item_frame, height=40, activate_scrollbars=False)
        result_textbox.insert("1.0", result_text)
        result_textbox.configure(state="disabled", fg_color="transparent")
        result_textbox.pack(side="left", fill="x", expand=True, padx=10, pady=10) # 增加內邊距

        if "breakout" in result_data['status']:
            ai_button = ctk.CTkButton(item_frame, text="🤖 AI 分析", width=100)
            ai_button.configure(command=lambda data=result_data, button=ai_button, frame=item_frame: self.toggle_ai_analysis(data, button, frame))
            ai_button.pack(side="right", padx=10, pady=10) # 增加內邊距

    def toggle_ai_analysis(self, result_data, button, parent_frame):
        is_closing = self.active_ai_widget is not None and self.active_ai_button == button
        if self.active_ai_widget:
            self.active_ai_widget.destroy()
            self.active_ai_widget = None
        if self.active_ai_button:
            self.active_ai_button.configure(text="🤖 AI 分析")
            self.active_ai_button = None
        if is_closing:
            return
        button.configure(text="讀取中...")
        self.active_ai_button = button
        
        # 調整 2: 讓 AI 分析框也有外邊距
        ai_textbox = ctk.CTkTextbox(self.results_frame, height=150, wrap="word") # wrap="word" 自動換行
        ai_textbox.insert("1.0", "AI 正在分析中，請稍候...")
        ai_textbox.configure(state="disabled")
        # padx 增加左右外邊距, pady 增加上下外邊距
        ai_textbox.pack(after=parent_frame, fill="x", padx=10, pady=(0, 10))
        self.active_ai_widget = ai_textbox
        
        threading.Thread(target=self.run_ai_analysis_in_background, args=(result_data, ai_textbox)).start()
    # ^^^ -------------------------- ^^^

    def run_ai_analysis_in_background(self, result_data, target_textbox):
        analysis_text = scanner.get_gemini_analysis(result_data)
        self.after(0, self.update_ai_result, target_textbox, analysis_text)
        
    def update_ai_result(self, target_textbox, analysis_text):
        target_textbox.configure(state="normal")
        target_textbox.delete("1.0", "end")
        target_textbox.insert("1.0", analysis_text)
        target_textbox.configure(state="disabled")
        if self.active_ai_button:
            self.active_ai_button.configure(text="隱藏分析")
            
    def safe_update_count(self, count): self.after(0, self.update_count, count)
    def update_count(self, count): self.status_label.configure(text=f"共找到 {count} 個交易對，開始掃描...")
    def safe_update_progress(self, progress): self.after(0, self.update_progress, progress)
    def update_progress(self, progress):
        percentage = int(progress * 100); self.progress_label.configure(text=f"進度: {percentage}%"); self.progressbar.set(progress)

if __name__ == "__main__":
    app = App()
    app.mainloop()