import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from ui.target_selection import ObjectSelectionTool
from utils.image_utils import display_frame


class ApplicationPage:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.rotation_angle = 0  # 預設旋轉角度為0
        self.setup_ui()
        # 初始化為 None，之後再創建
        self.object_selection_tool = None

    def setup_ui(self):
        # 上傳目標素材區域
        target_frame = ttk.LabelFrame(self.frame, text="上傳目標素材")
        target_frame.pack(fill=tk.X, padx=10, pady=10)

        self.target_btn = ttk.Button(target_frame, text="選擇目標素材", command=self.select_target_video)
        self.target_btn.pack(pady=10)

        self.target_video_label = ttk.Label(target_frame, text="尚未選擇素材")
        self.target_video_label.pack(pady=5)

        # 影片旋轉控制
        rotation_frame = ttk.Frame(target_frame)
        rotation_frame.pack(fill=tk.X, pady=5)

        ttk.Label(rotation_frame, text="影片旋轉：").pack(side=tk.LEFT, padx=5)

        # 建立旋轉按鈕
        self.rotate_btn = ttk.Button(rotation_frame, text="旋轉 180°", command=self.toggle_rotation)
        self.rotate_btn.pack(side=tk.LEFT, padx=5)
        self.rotate_btn.config(state=tk.DISABLED)  # 初始禁用

        # 目標影片預覽區域
        preview_frame = ttk.LabelFrame(self.frame, text="目標素材預覽")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.target_canvas = tk.Canvas(preview_frame, bg="black", width=640, height=360)
        self.target_canvas.pack(pady=10)

        # 應用剪輯風格區域
        apply_frame = ttk.LabelFrame(self.frame, text="應用剪輯風格")
        apply_frame.pack(fill=tk.X, padx=10, pady=10)

        # 物件優先設置
        obj_frame = ttk.Frame(apply_frame)
        obj_frame.pack(fill=tk.X, pady=5)

        ttk.Label(obj_frame, text="物件優先級:").pack(side=tk.LEFT, padx=10)
        self.object_priority_var = tk.DoubleVar(value=0.7)  # 預設70%物件優先，30%場景變化
        self.object_scale = ttk.Scale(
            obj_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            length=300,
            variable=self.object_priority_var
        )
        self.object_scale.pack(side=tk.LEFT, padx=5)
        ttk.Label(obj_frame, text="場景變化").pack(side=tk.LEFT)
        ttk.Label(obj_frame, text="物件優先").pack(side=tk.RIGHT)

        # 剪輯密度調整
        density_frame = ttk.Frame(apply_frame)
        density_frame.pack(fill=tk.X, pady=5)

        ttk.Label(density_frame, text="剪輯密度調整:").pack(side=tk.LEFT, padx=10)
        self.density_var = tk.DoubleVar(value=1.0)
        self.density_scale = ttk.Scale(
            density_frame,
            from_=0.5,
            to=1.5,
            orient=tk.HORIZONTAL,
            length=300,
            variable=self.density_var
        )
        self.density_scale.pack(side=tk.LEFT, padx=5)
        ttk.Label(density_frame, text="低").pack(side=tk.LEFT)
        ttk.Label(density_frame, text="高").pack(side=tk.RIGHT)

        # 套用按鈕
        self.apply_btn = ttk.Button(apply_frame, text="套用剪輯風格", command=self.apply_cutting_style)
        self.apply_btn.pack(pady=10)

        # 結果預覽
        self.cut_preview_text = tk.Text(apply_frame, height=6, width=80)
        self.cut_preview_text.pack(pady=10, padx=10, fill=tk.X)
        self.cut_preview_text.config(state=tk.DISABLED)

    def toggle_rotation(self):
        """切換影片旋轉角度"""
        if self.rotation_angle == 0:
            self.rotation_angle = 180
        else:
            self.rotation_angle = 0

        # 更新按鈕文字
        self.rotate_btn.config(text=f"旋轉 {(self.rotation_angle + 180) % 360}°")

        # 重新顯示影片幀
        if self.app.target_cap and self.app.target_cap.isOpened():
            # 先將影片指針設置到開頭
            self.app.target_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.app.target_cap.read()
            if ret:
                display_frame(frame, self.target_canvas, self.rotation_angle)

            # 記錄旋轉狀態到app
            self.app.target_rotation = self.rotation_angle

    def disable_buttons(self):
        """禁用頁面按鈕"""
        self.target_btn.config(state=tk.DISABLED)
        self.apply_btn.config(state=tk.DISABLED)
        self.object_scale.config(state=tk.DISABLED)
        self.density_scale.config(state=tk.DISABLED)
        self.rotate_btn.config(state=tk.DISABLED)

        # 如果已創建物件選擇工具，禁用其按鈕
        if self.object_selection_tool:
            self.object_selection_tool.select_btn.config(state=tk.DISABLED)
            self.object_selection_tool.clear_btn.config(state=tk.DISABLED)

    def enable_buttons(self):
        """啟用頁面按鈕"""
        self.target_btn.config(state=tk.NORMAL)
        self.apply_btn.config(state=tk.NORMAL)
        self.object_scale.config(state=tk.NORMAL)
        self.density_scale.config(state=tk.NORMAL)

        # 只有在有影片時才啟用旋轉按鈕
        if self.app.target_video_path:
            self.rotate_btn.config(state=tk.NORMAL)

        # 如果已創建物件選擇工具，啟用其按鈕
        if self.object_selection_tool:
            self.object_selection_tool.select_btn.config(state=tk.NORMAL)
            if self.app.target_object_roi:
                self.object_selection_tool.clear_btn.config(state=tk.NORMAL)

    def select_target_video(self):
        """選擇目標素材"""
        file_path = filedialog.askopenfilename(
            title="選擇目標素材",
            filetypes=(("影片檔案", "*.mp4 *.avi *.mov *.mkv"), ("所有檔案", "*.*"))
        )

        if file_path:
            self.app.target_video_path = file_path
            self.target_video_label.config(text=os.path.basename(file_path))
            self.app.status_var.set(f"已選擇目標素材: {os.path.basename(file_path)}")

            # 嘗試打開影片並顯示第一幀
            self.app.target_cap = cv2.VideoCapture(file_path)
            if self.app.target_cap.isOpened():
                ret, frame = self.app.target_cap.read()
                if ret:
                    display_frame(frame, self.target_canvas, self.rotation_angle)

                # 獲取影片總時長
                fps = self.app.target_cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(self.app.target_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.app.target_duration = frame_count / fps if fps > 0 else 0

                # 創建目標物件選擇工具
                if self.object_selection_tool is None:
                    self.object_selection_tool = ObjectSelectionTool(self.frame, self.app, self.target_canvas)

                # 啟用旋轉按鈕
                self.rotate_btn.config(state=tk.NORMAL)

                # 存儲目前的旋轉角度到app
                self.app.target_rotation = self.rotation_angle

    def apply_cutting_style(self):
        """應用剪輯風格"""
        if not self.app.target_video_path:
            messagebox.showerror("錯誤", "請先選擇目標素材")
            return

        if not self.app.cut_points:
            messagebox.showerror("錯誤", "請先分析範例影片")
            return

        self.app.status_var.set("正在應用剪輯風格...")
        self.app.disable_all_buttons()

        # 在新線程中執行，避免UI凍結
        threading.Thread(target=self._apply_style_thread).start()

    def _apply_style_thread(self):
        """在單獨線程中執行風格應用"""
        try:
            # 確保物件檢測模型已加載
            if self.app.object_model is None:
                self.app.initialize_object_detection()

            # 確保有重要物件選擇
            if not self.app.important_objects:
                self.app.root.after(0, lambda: messagebox.showwarning("警告", "未選擇重要物件，將使用預設物件"))
                # 使用默認物件 (最常見的5個)
                sorted_objects = sorted(self.app.example_objects.items(),
                                    key=lambda x: x[1][0],
                                    reverse=True)[:5]
                self.app.important_objects = [obj[0] for obj in sorted_objects]

            # 調用核心處理器進行風格應用
            self.app.video_processor.apply_cutting_style(
                self.app.target_video_path,
                self.app,
                self.object_priority_var.get(),
                self.density_var.get()
            )

            # 更新UI
            self.app.root.after(0, self.update_cuts_preview)

        except Exception as e:
            error_msg = str(e)
            self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("錯誤", f"錯誤: {msg}"))
        finally:
            self.app.root.after(0, lambda: self.app.enable_all_buttons())
            self.app.root.after(0, lambda: self.app.status_var.set("應用完成"))

    def update_cuts_preview(self):
        """更新剪輯預覽"""
        # 更新剪輯預覽文本
        self.cut_preview_text.config(state=tk.NORMAL)
        self.cut_preview_text.delete(1.0, tk.END)

        # 找出目標影片中的重要物件
        target_important = []
        for obj in self.app.important_objects:
            if obj in self.app.target_objects:
                occurrences = self.app.target_objects[obj][0]
                target_important.append(f"{obj} ({occurrences}次)")

        preview = [
            f"目標素材總長度: {self.app.target_duration:.2f} 秒",
            f"檢測到的重要物件: {', '.join(target_important) if target_important else '無'}",
            f"建議的剪輯點數量: {len(self.app.suggested_cuts)} 個",
            f"每分鐘剪輯頻率: {len(self.app.suggested_cuts) / (self.app.target_duration / 60):.2f} 次/分鐘",
            "",
            "請前往「預覽與輸出」標籤確認剪輯點"
        ]

        self.cut_preview_text.insert(tk.END, "\n".join(preview))
        self.cut_preview_text.config(state=tk.DISABLED)

        # 更新剪輯點列表
        self.app.output_page.cuts_listbox.delete(0, tk.END)
        for i, cut in enumerate(self.app.final_cuts):
            mins = int(cut / 60)
            secs = int(cut % 60)
            msec = int((cut - int(cut)) * 100)
            self.app.output_page.cuts_listbox.insert(tk.END, f"剪輯點 {i+1}: {mins:02d}:{secs:02d}.{msec:02d}")