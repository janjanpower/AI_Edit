import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from utils.dialog import simpledialog

class OutputPage:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.setup_ui()

    def setup_ui(self):
        # 頁面主框架
        self.content_frame = ttk.Frame(self.frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # 使用網格布局
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)  # 剪輯點列表可擴展

        # 輸出設置區域
        output_frame = ttk.LabelFrame(self.content_frame, text="輸出設置")
        output_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        # 配置輸出框架
        output_frame.columnconfigure(1, weight=1)

        self.output_btn = ttk.Button(output_frame, text="選擇輸出位置", command=self.select_output_path)
        self.output_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.output_path_label = ttk.Label(output_frame, text="尚未選擇輸出位置")
        self.output_path_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 確認剪輯點列表
        cuts_frame = ttk.LabelFrame(self.content_frame, text="確認剪輯點")
        cuts_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # 配置剪輯點框架
        cuts_frame.columnconfigure(0, weight=1)
        cuts_frame.rowconfigure(0, weight=1)

        # 顯示剪輯點的列表框和滾動條
        cuts_list_frame = ttk.Frame(cuts_frame)
        cuts_list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # 配置列表框架
        cuts_list_frame.columnconfigure(0, weight=1)
        cuts_list_frame.rowconfigure(0, weight=1)

        self.cuts_listbox = tk.Listbox(cuts_list_frame)
        self.cuts_listbox.grid(row=0, column=0, sticky="nsew")

        cuts_scroll = ttk.Scrollbar(cuts_list_frame, orient=tk.VERTICAL, command=self.cuts_listbox.yview)
        cuts_scroll.grid(row=0, column=1, sticky="ns")

        self.cuts_listbox.config(yscrollcommand=cuts_scroll.set)

        # 剪輯點操作按鈕
        cuts_btn_frame = ttk.Frame(cuts_frame)
        cuts_btn_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        self.remove_btn = ttk.Button(cuts_btn_frame, text="移除選中的剪輯點", command=self.remove_selected_cut)
        self.remove_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.add_btn = ttk.Button(cuts_btn_frame, text="增加剪輯點", command=self.add_cut_point)
        self.add_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 剪輯點詳情按鈕
        self.detail_btn = ttk.Button(
            cuts_btn_frame,
            text="顯示剪輯點詳情",
            command=self.show_cut_details
        )
        self.detail_btn.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # 剪輯點詳情顯示區
        self.cut_details_frame = ttk.LabelFrame(self.content_frame, text="剪輯點詳情")
        self.cut_details_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # 配置詳情框架
        self.cut_details_frame.columnconfigure(0, weight=1)
        self.cut_details_frame.rowconfigure(0, weight=1)

        self.cut_details_text = tk.Text(self.cut_details_frame, height=5)
        self.cut_details_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.cut_details_text.config(state=tk.DISABLED)

        # 導出按鈕
        export_frame = ttk.LabelFrame(self.content_frame, text="輸出設置")
        export_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        # 配置導出框架
        export_frame.columnconfigure(0, weight=1)

        self.export_btn = ttk.Button(export_frame, text="導出最終影片", command=self.export_final_video)
        self.export_btn.grid(row=0, column=0, padx=5, pady=5)

        # 初始更新佈局
        self.update_ui_layout()

    def update_ui_layout(self):
        """更新UI佈局以適應視窗大小變化或分頁切換"""
        # 獲取當前框架尺寸
        frame_width = self.frame.winfo_width()
        frame_height = self.frame.winfo_height()

        # 如果框架尺寸過小，使用合理的最小值
        if frame_width < 10:
            frame_width = 800
        if frame_height < 10:
            frame_height = 600

        # 調整列表框的高度
        list_height = max(8, min(15, int(frame_height / 50)))
        self.cuts_listbox.config(height=list_height)

        # 調整詳情文本區高度
        text_height = max(4, min(8, int(frame_height / 100)))
        self.cut_details_text.config(height=text_height)

        # 刷新框架，確保變更生效
        self.frame.update_idletasks()
    def disable_buttons(self):
        """禁用頁面按鈕"""
        self.output_btn.config(state=tk.DISABLED)
        self.remove_btn.config(state=tk.DISABLED)
        self.add_btn.config(state=tk.DISABLED)
        self.detail_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)

    def enable_buttons(self):
        """啟用頁面按鈕"""
        self.output_btn.config(state=tk.NORMAL)
        self.remove_btn.config(state=tk.NORMAL)
        self.add_btn.config(state=tk.NORMAL)
        self.detail_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)

    def select_output_path(self):
        """選擇輸出位置"""
        file_path = filedialog.asksaveasfilename(
            title="選擇輸出位置",
            defaultextension=".mp4",
            filetypes=(("MP4 影片", "*.mp4"), ("所有檔案", "*.*"))
        )

        if file_path:
            self.app.output_path = file_path
            self.output_path_label.config(text=os.path.basename(file_path))
            self.app.status_var.set(f"已設定輸出位置: {os.path.basename(file_path)}")

    def remove_selected_cut(self):
        """移除選中的剪輯點"""
        selected = self.cuts_listbox.curselection()
        if selected:
            index = selected[0]
            self.cuts_listbox.delete(index)
            self.app.final_cuts.pop(index)

            # 更新介面
            self.app.status_var.set(f"已移除剪輯點 {index+1}")

    def add_cut_point(self):
        """增加剪輯點"""
        # 簡單對話框讓使用者輸入時間
        time_str = simpledialog.askstring("增加剪輯點", "請輸入時間點 (分:秒):")
        if not time_str:
            return

        try:
            # 解析時間格式
            if ":" in time_str:
                mins, secs = map(int, time_str.split(":"))
                time_point = mins * 60 + secs
            else:
                time_point = float(time_str)

            # 檢查有效性
            if time_point < 0 or time_point > self.app.target_duration:
                messagebox.showerror("錯誤", f"時間點必須在 0 到 {self.app.target_duration:.2f} 秒之間")
                return

            # 添加到列表並排序
            self.app.final_cuts.append(time_point)
            self.app.final_cuts.sort()

            # 更新列表框
            self.cuts_listbox.delete(0, tk.END)
            for i, cut in enumerate(self.app.final_cuts):
                mins = int(cut / 60)
                secs = int(cut % 60)
                msec = int((cut - int(cut)) * 100)
                self.cuts_listbox.insert(tk.END, f"剪輯點 {i+1}: {mins:02d}:{secs:02d}.{msec:02d}")

            self.app.status_var.set(f"已添加剪輯點: {mins:02d}:{secs:02d}")

        except ValueError:
            messagebox.showerror("錯誤", "無效的時間格式。請使用 分:秒 或 秒數")

    def show_cut_details(self):
        """顯示剪輯點詳情"""
        # 獲取選中的剪輯點
        selected = self.cuts_listbox.curselection()
        if not selected:
            messagebox.showinfo("提示", "請先選擇一個剪輯點")
            return

        index = selected[0]
        cut_time = self.app.final_cuts[index]

        # 尋找該時間點附近的物件
        nearby_objects = {}

        # 搜索目標影片中該時間點前後1秒的物件
        for obj, (_, _, timestamps) in self.app.target_objects.items():
            for ts in timestamps:
                if abs(ts - cut_time) <= 1.0:  # 1秒內
                    if obj not in nearby_objects:
                        nearby_objects[obj] = 1
                    else:
                        nearby_objects[obj] += 1

        # 更新詳情顯示
        self.cut_details_text.config(state=tk.NORMAL)
        self.cut_details_text.delete(1.0, tk.END)

        mins = int(cut_time / 60)
        secs = int(cut_time % 60)
        msec = int((cut_time - int(cut_time)) * 100)

        details = [
            f"剪輯點 {index+1}: {mins:02d}:{secs:02d}.{msec:02d}",
            f"相對位置: 影片進度 {(cut_time / self.app.target_duration * 100):.1f}%",
            "",
            "附近出現的物件:"
        ]

        if nearby_objects:
            for obj, count in sorted(nearby_objects.items(), key=lambda x: x[1], reverse=True):
                is_important = "★" if obj in self.app.important_objects else ""
                # 獲取中文名稱
                chinese_name = self.app.get_chinese_name(obj)
                details.append(f"  {chinese_name}{is_important}: {count}次")
        else:
            details.append("  未檢測到物件")

        self.cut_details_text.insert(tk.END, "\n".join(details))
        self.cut_details_text.config(state=tk.DISABLED)

    def export_final_video(self):
        """導出最終影片"""
        if not self.app.target_video_path:
            messagebox.showerror("錯誤", "請先選擇目標素材")
            return

        if not self.app.output_path:
            messagebox.showerror("錯誤", "請先選擇輸出位置")
            return

        if not self.app.final_cuts:
            messagebox.showerror("錯誤", "沒有設定剪輯點")
            return

        # 禁用所有按鈕
        self.app.disable_all_buttons()

        # 創建進度窗口
        progress_window = tk.Toplevel(self.app.root)
        progress_window.title("導出中")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)

        # 進度標籤
        label = ttk.Label(progress_window, text="正在導出影片，請稍候...", font=("Arial", 12))
        label.pack(padx=20, pady=10)

        # 進度條
        progress_var = tk.IntVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100, length=350)
        progress_bar.pack(padx=20, pady=10)

        # 進度百分比
        percent_label = ttk.Label(progress_window, text="0%")
        percent_label.pack(pady=5)

        # 在新線程中處理影片
        self.app.status_var.set("正在導出影片...")
        threading.Thread(target=lambda: self.app.video_processor.export_video(
            self.app.target_video_path,
            self.app.output_path,
            self.app.final_cuts,
            self.app,
            progress_window,
            progress_var,
            percent_label
        )).start()