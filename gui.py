import customtkinter as ctk
import threading
import scanner

# --- 介面設定 ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- 中英對照字典 ---
PATTERN_MAP = {
    "三角收斂": "triangle",
    "W底型態": "double_bottom",
    "上升三角形": "ascending_triangle",
}
TIMEFRAME_MAP = {
    "15分鐘": "15m",
    "30分鐘": "30m",
    "1小時": "1H",
    "1天": "1D",
}
EXCHANGE_MAP = {
    "OKX": "okx",
    "Binance (幣安)": "binance",
}

# --- 主視窗 ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("多交易所市場掃描器")
        self.geometry("500x580")

        # --- 介面元件 ---
        self.label_exchange = ctk.CTkLabel(self, text="交易所 (Exchange):")
        self.label_exchange.pack(pady=(20, 5))
        self.optionmenu_exchange = ctk.CTkOptionMenu(self, values=list(EXCHANGE_MAP.keys()))
        self.optionmenu_exchange.pack(pady=5)

        self.label_quote = ctk.CTkLabel(self, text="報價貨幣 (Quote Currency):")
        self.label_quote.pack(pady=(15, 5))
        self.entry_quote = ctk.CTkEntry(self, placeholder_text="例如: USDT")
        self.entry_quote.pack(pady=5)

        self.label_timeframe = ctk.CTkLabel(self, text="K線時框 (Timeframe):")
        self.label_timeframe.pack(pady=(15, 5))
        self.optionmenu_timeframe = ctk.CTkOptionMenu(self, values=list(TIMEFRAME_MAP.keys()))
        self.optionmenu_timeframe.pack(pady=5)

        self.label_pattern = ctk.CTkLabel(self, text="技術形態 (Pattern):")
        self.label_pattern.pack(pady=(15, 5))
        self.optionmenu_pattern = ctk.CTkOptionMenu(self, values=list(PATTERN_MAP.keys()))
        self.optionmenu_pattern.pack(pady=5)

        self.button_scan = ctk.CTkButton(self, text="開始掃描", command=self.start_scan)
        self.button_scan.pack(pady=20)

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.pack()

        self.progress_label = ctk.CTkLabel(self, text="進度: 0%")
        self.progress_label.pack()
        self.progressbar = ctk.CTkProgressBar(self, width=400)
        self.progressbar.set(0)
        self.progressbar.pack(pady=5)

        self.textbox_results = ctk.CTkTextbox(self, width=450, height=200)
        self.textbox_results.pack(pady=10)
        self.textbox_results.insert("0.0", "請設定參數後，點擊開始掃描...\n")

    def start_scan(self):
        quote = self.entry_quote.get()
        display_pattern = self.optionmenu_pattern.get()
        internal_pattern = PATTERN_MAP[display_pattern]
        display_timeframe = self.optionmenu_timeframe.get()
        internal_timeframe = TIMEFRAME_MAP[display_timeframe]
        display_exchange = self.optionmenu_exchange.get()
        internal_exchange = EXCHANGE_MAP[display_exchange]
        
        if not quote:
            self.textbox_results.delete("1.0", "end")
            self.textbox_results.insert("end", "錯誤：請輸入報價貨幣！\n")
            return
            
        self.button_scan.configure(state="disabled", text="掃描中...")
        self.status_label.configure(text="正在獲取交易對列表...")
        self.progressbar.set(0)
        self.progress_label.configure(text="進度: 0%")
        self.textbox_results.delete("1.0", "end")
        self.textbox_results.insert("end", f"掃描任務已啟動...\n交易所: {display_exchange} | 目標: {quote.upper()} | 時框: {display_timeframe} | 型態: {display_pattern}\n\n")

        scan_thread = threading.Thread(
            target=self.run_scan_in_background,
            args=(internal_exchange, quote, internal_timeframe, internal_pattern)
        )
        scan_thread.start()

    def run_scan_in_background(self, exchange_name, quote, timeframe, pattern):
        exchange_class = scanner.EXCHANGE_ADAPTERS[exchange_name]
        exchange_adapter = exchange_class()
        
        results = scanner.run_scan(
            exchange_adapter, quote, timeframe, pattern,
            progress_callback=self.safe_update_progress,
            count_callback=self.safe_update_count
        )
        self.after(0, self.update_results, results)

    def safe_update_count(self, count):
        self.after(0, self.update_count, count)

    def update_count(self, count):
        self.status_label.configure(text=f"共找到 {count} 個交易對，開始掃描...")

    def safe_update_progress(self, progress):
        self.after(0, self.update_progress, progress)

    def update_progress(self, progress):
        percentage = int(progress * 100)
        self.progress_label.configure(text=f"進度: {percentage}%")
        self.progressbar.set(progress)

    def update_results(self, results):
        self.status_label.configure(text="掃描完成！")
        if results:
            self.textbox_results.insert("end", f"掃描完成！找到 {len(results)} 個結果：\n")
            for result in results:
                self.textbox_results.insert("end", f"{result}\n")
        else:
            self.textbox_results.insert("end", "掃描完成，未找到符合條件的目標。\n")
        self.button_scan.configure(state="normal", text="開始掃描")

# --- 程式進入點 ---
if __name__ == "__main__":
    app = App()
    app.mainloop()