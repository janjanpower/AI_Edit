import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import cv2

from utils.image_utils import display_frame

class AnalysisPage:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.setup_ui()

    def setup_ui(self):
        # 主框架使用網格布局
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)  # 預覽區域可擴展

        # 上傳範例影片區域
        upload_frame = ttk.LabelFrame(self.frame, text="上傳範例影片")
        upload_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        # 上傳區域使用網格布局
        upload_frame.columnconfigure(1, weight=1)

        self.upload_btn = ttk.Button(upload_frame, text="選擇範例影片", command=self.select_example_video)
        self.upload_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.example_video_label = ttk.Label(upload_frame, text="尚未選擇影片")
        self.example_video_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 範例影片預覽區域
        preview_frame = ttk.LabelFrame(self.frame, text="範例影片預覽")
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # 配置預覽框架
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        # 使用更大的初始尺寸，確保有足夠的顯示區域
        self.example_canvas = tk.Canvas(preview_frame, bg="black", width=640, height=360)
        self.example_canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # 分析控制區域
        control_frame = ttk.LabelFrame(self.frame, text="分析控制")
        control_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # 分析控制使用網格布局
        control_frame.columnconfigure(1, weight=1)

        self.analyze_btn = ttk.Button(control_frame, text="分析範例影片", command=self.analyze_example_video)
        self.analyze_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 添加物件分析選項
        self.object_analysis_var = tk.BooleanVar(value=True)
        obj_checkbox = ttk.Checkbutton(
            control_frame,
            text="啟用物件識別分析",
            variable=self.object_analysis_var
        )
        obj_checkbox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 分析結果區域
        result_frame = ttk.LabelFrame(self.frame, text="分析結果")
        result_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        # 配置結果框架
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        # 分析結果顯示區
        self.result_text = tk.Text(result_frame, height=8)
        self.result_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.result_text.config(state=tk.DISABLED)

        # 物件選擇區域 - 初始不創建，等分析完後動態添加
        self.object_selection_frame = None

        # 啟用所有框架的擴展功能
        for child in self.frame.winfo_children():
            if isinstance(child, ttk.LabelFrame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, (tk.Canvas, tk.Text)):
                        # Canvas 和 Text 需要能夠擴展
                        grandchild.bind("<Configure>", lambda e, widget=grandchild: self.update_widget_size(e, widget))

        # 綁定視窗大小變化事件
        self.frame.bind("<Configure>", self.on_frame_configure)

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

        # 計算適合的預覽Canvas尺寸
        canvas_width = min(640, frame_width - 30)
        canvas_height = min(360, int(frame_height * 0.5))

        # 更新Canvas尺寸
        self.example_canvas.config(width=canvas_width, height=canvas_height)

        # 刷新框架，確保變更生效
        self.frame.update_idletasks()

        # 如果有影片幀，重新顯示
        if hasattr(self.app, 'example_cap') and self.app.example_cap is not None and self.app.example_cap.isOpened():
            current_pos = self.app.example_cap.get(cv2.CAP_PROP_POS_FRAMES)
            self.app.example_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.app.example_cap.read()
            if ret:
                from utils.image_utils import display_frame
                display_frame(frame, self.example_canvas, self.app.example_rotation)
            # 恢復原來的播放位置
            self.app.example_cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

    def on_frame_configure(self, event):
        """處理框架大小變化事件"""
        # 更新所有子元件尺寸
        width = event.width
        height = event.height

        # 確保預覽區域得到足夠空間
        for child in self.frame.winfo_children():
            if isinstance(child, ttk.LabelFrame) and "預覽" in child.cget("text"):
                # 計算合適的高度比例 (約佔總高度的60%)
                preview_height = int(height * 0.6)
                self.example_canvas.config(height=max(200, preview_height - 20))

    def update_widget_size(self, event, widget):
        """更新特定元件尺寸"""
        # 針對不同類型元件進行適當調整
        if isinstance(widget, tk.Canvas):
            # Canvas 已經通過 sticky 設置自動填充，無需額外處理
            pass
        elif isinstance(widget, tk.Text):
            # 根據框架高度調整文本區域高度
            parent_height = widget.master.winfo_height()
            text_height = max(6, min(12, parent_height // 20))
            widget.config(height=text_height)

    def disable_buttons(self):
        """禁用頁面按鈕"""
        self.upload_btn.config(state=tk.DISABLED)
        self.analyze_btn.config(state=tk.DISABLED)

    def enable_buttons(self):
        """啟用頁面按鈕"""
        self.upload_btn.config(state=tk.NORMAL)
        self.analyze_btn.config(state=tk.NORMAL)

    def select_example_video(self):
        """選擇範例影片"""
        file_path = filedialog.askopenfilename(
            title="選擇範例影片",
            filetypes=(("影片檔案", "*.mp4 *.avi *.mov *.mkv"), ("所有檔案", "*.*"))
        )

        if file_path:
            self.app.example_video_path = file_path
            self.example_video_label.config(text=os.path.basename(file_path))
            self.app.status_var.set(f"已選擇範例影片: {os.path.basename(file_path)}")

            # 嘗試打開影片並顯示第一幀
            self.app.example_cap = cv2.VideoCapture(file_path)
            if self.app.example_cap.isOpened():
                # 循環嘗試獲取有效幀
                valid_frame = False
                for _ in range(10):  # 嘗試前10幀
                    ret, frame = self.app.example_cap.read()
                    if ret and frame is not None and frame.size > 0:
                        valid_frame = True
                        display_frame(frame, self.example_canvas)
                        break

                # 如果沒找到有效幀，顯示錯誤
                if not valid_frame:
                    messagebox.showerror("錯誤", "無法從影片中讀取有效幀")
                    self.app.status_var.set("讀取影片幀失敗")
                    return

                # 獲取影片總時長
                fps = self.app.example_cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(self.app.example_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.app.example_duration = frame_count / fps if fps > 0 else 0
            else:
                messagebox.showerror("錯誤", "無法打開影片檔案")
                self.app.status_var.set("無法打開影片檔案")

    def analyze_example_video(self):
        """分析範例影片"""
        if not self.app.example_video_path:
            messagebox.showerror("錯誤", "請先選擇範例影片")
            return

        self.app.status_var.set("正在分析範例影片...")
        self.app.disable_all_buttons()  # 禁用所有按鈕

        # 在新線程中執行分析，避免UI凍結
        threading.Thread(target=self._analyze_example_thread).start()

    def _analyze_example_thread(self):
        """在單獨線程中執行影片分析"""
        try:
            # 確保物件檢測模型已加載
            if self.app.object_model is None:
                self.app.initialize_object_detection()

            self.app.video_processor.analyze_example_video(
                self.app.example_video_path,
                self.app,
                self.object_analysis_var.get()
            )

            # 分析完成，更新UI
            self.app.root.after(0, self.update_analysis_results)

        except Exception as e:
            self.app.root.after(0, lambda: messagebox.showerror("錯誤", f"分析過程中發生錯誤: {str(e)}"))
        finally:
            self.app.root.after(0, lambda: self.app.enable_all_buttons())
            self.app.root.after(0, lambda: self.app.status_var.set("分析完成"))

    def update_analysis_results(self):
        """更新分析結果顯示"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)

        results = [
            f"範例影片總長度: {self.app.example_duration:.2f} 秒",
            f"檢測到的剪輯點數量: {len(self.app.cut_points)} 個",
            f"平均片段長度: {self.app.avg_segment_duration:.2f} 秒",
            f"剪輯密度: {self.app.cutting_density:.2f} 次/分鐘",
            "",
            "物件分析結果:",
        ]

        # 添加排序後的物件列表
        if self.app.example_objects:
            sorted_objects = sorted(self.app.example_objects.items(),
                                key=lambda x: x[1][0],
                                reverse=True)

            for obj_name, (count, _, timestamps) in sorted_objects[:8]:  # 顯示前8個物件
                results.append(f"  {obj_name}: 出現 {count} 次")

            # 添加重要物件的剪輯模式
            results.append("")
            results.append("物件剪輯模式:")

            for i, obj in enumerate(self.app.important_objects[:3]):  # 只顯示前3個重要物件
                if obj in self.app.object_durations:
                    results.append(f"  {obj}: 平均展示時長 {self.app.object_durations[obj]:.2f} 秒")
        else:
            results.append("  未檢測到物件，請確認物件檢測模型是否正確加載")

        results.append("")
        results.append("剪輯風格分析:")
        results.append(f"  {'快節奏' if self.app.cutting_density > 15 else '中等節奏' if self.app.cutting_density > 8 else '慢節奏'} 剪輯")

        self.result_text.insert(tk.END, "\n".join(results))
        self.result_text.config(state=tk.DISABLED)

        # 更新重要物件選擇介面
        self.update_object_selection()

    def update_object_selection(self):
        """更新物件選擇介面"""
        # 檢查是否已有物件選擇框架
        if hasattr(self, 'object_selection_frame'):
            self.object_selection_frame.destroy()

        # 創建物件選擇框架
        self.object_selection_frame = ttk.LabelFrame(self.frame, text="選擇重要物件")
        self.object_selection_frame.pack(fill=tk.X, padx=10, pady=10)

        # 創建物件選擇的檢查框
        self.object_vars = {}

        if self.app.example_objects:
            # 排序物件，出現次數最多的在前
            sorted_objects = sorted(self.app.example_objects.items(),
                                key=lambda x: x[1][0],
                                reverse=True)

            # 創建檢查框框架，使用網格布局
            check_frame = ttk.Frame(self.object_selection_frame)
            check_frame.pack(fill=tk.X, padx=5, pady=5)

            # 每行最多4個檢查框
            for i, (obj_name, (count, _, _)) in enumerate(sorted_objects[:12]):  # 最多顯示12個物件
                self.object_vars[obj_name] = tk.BooleanVar(value=(obj_name in self.app.important_objects))

                row = i // 4
                col = i % 4

                ttk.Checkbutton(
                    check_frame,
                    text=f"{obj_name} ({count})",
                    variable=self.object_vars[obj_name]
                ).grid(row=row, column=col, padx=5, pady=2, sticky=tk.W)

            # 添加確認按鈕
            ttk.Button(
                self.object_selection_frame,
                text="確認選擇",
                command=self.update_important_objects
            ).pack(pady=5)

    def update_important_objects(self):
        """更新重要物件列表"""
        # 更新重要物件列表
        self.app.important_objects = [
            obj for obj, var in self.object_vars.items() if var.get()
        ]

        # 更新狀態
        self.app.status_var.set(f"已更新重要物件: {', '.join(self.app.important_objects)}")

        # 如果沒有選擇物件，使用默認的前5個
        if not self.app.important_objects:
            sorted_objects = sorted(self.app.example_objects.items(),
                                key=lambda x: x[1][0],
                                reverse=True)[:5]
            self.app.important_objects = [obj[0] for obj in sorted_objects]
            self.app.status_var.set(f"使用默認重要物件: {', '.join(self.app.important_objects)}")
