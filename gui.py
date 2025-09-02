import customtkinter as ctk
import threading
import scanner

# --- 介面設定 & 中英對照字典 (保持不變) ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
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

# --- 主視窗 ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OKX 市場掃描器")
        self.geometry("500x550") # <--- 增加高度

        # --- 介面元件 ---
        # ... (上方的 Label, Entry, OptionMenu 保持不變) ...
        self.label_quote = ctk.CTkLabel(self, text="報價貨幣 (Quote Currency):")
        self.label_quote.pack(pady=(20, 5))
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

        # vvv --- 新增進度條和進度標籤 --- vvv
        self.progress_label = ctk.CTkLabel(self, text="進度: 0%")
        self.progress_label.pack()
        self.progressbar = ctk.CTkProgressBar(self, width=400)
        self.progressbar.set(0) # 設定初始值為 0
        self.progressbar.pack(pady=5)
        # ^^^ -------------------------- ^^^

        self.textbox_results = ctk.CTkTextbox(self, width=450, height=200)
        self.textbox_results.pack(pady=10)
        self.textbox_results.insert("0.0", "請設定參數後，點擊開始掃描...\n")

    def start_scan(self):
        # ... (前半段獲取參數的邏輯不變) ...
        quote = self.entry_quote.get()
        display_pattern = self.optionmenu_pattern.get()
        internal_pattern = PATTERN_MAP[display_pattern]
        display_timeframe = self.optionmenu_timeframe.get()
        internal_timeframe = TIMEFRAME_MAP[display_timeframe]
        if not quote:
            # ...
            self.textbox_results.delete("1.0", "end")
            self.textbox_results.insert("end", "錯誤：請輸入報價貨幣！\n")
            return
            
        # 重設進度條和介面狀態
        self.button_scan.configure(state="disabled", text="掃描中...")
        self.progressbar.set(0)
        self.progress_label.configure(text="進度: 0%")
        self.textbox_results.delete("1.0", "end")
        self.textbox_results.insert("end", f"掃描任務已啟動...\n目標: {quote.upper()} | 時框: {display_timeframe} | 型態: {display_pattern}\n\n")

        scan_thread = threading.Thread(
            target=self.run_scan_in_background,
            args=(quote, internal_timeframe, internal_pattern)
        )
        scan_thread.start()

    def run_scan_in_background(self, quote, timeframe, pattern):
        # 將 safe_update_progress 作為回呼函式傳遞給後端
        results = scanner.run_scan(quote, timeframe, pattern, progress_callback=self.safe_update_progress)
        self.after(0, self.update_results, results)
    
    # vvv --- 新增的兩個函式，用於安全地更新進度條 --- vvv
    def safe_update_progress(self, progress):
        """由背景執行緒呼叫，用來安全地排程主執行緒的 UI 更新。"""
        # self.after(0, ...) 會將 self.update_progress 的執行請求放入主執行緒的事件佇列中
        self.after(0, self.update_progress, progress)

    def update_progress(self, progress):
        """這個函式在主執行緒中執行，負責實際更新進度條元件。"""
        percentage = int(progress * 100)
        self.progress_label.configure(text=f"進度: {percentage}%")
        self.progressbar.set(progress)
    # ^^^ ------------------------------------------ ^^^

    def update_results(self, results):
        # ... (此函式與 v2.1 版本完全相同，為節省篇幅省略) ...
        if results:
            self.textbox_results.insert("end", f"掃描完成！找到 {len(results)} 個結果：\n")
            for result in results:
                self.textbox_results.insert("end", f"{result}\n")
        else:
            self.textbox_results.insert("end", "掃描完成，未找到符合條件的目標。\n")
        self.button_scan.configure(state="normal", text="開始掃描")

if __name__ == "__main__":
    app = App()
    app.mainloop()