import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

from ui.analysis_page import AnalysisPage
from ui.application_page import ApplicationPage
from ui.output_page import OutputPage
from core.video_processor import VideoProcessor
from utils.dialog import simpledialog

class IntelligentVideoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("智能影片剪輯系統")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        # 初始化變數
        self.example_video_path = None
        self.target_video_path = None
        self.output_path = None

        self.example_cap = None
        self.target_cap = None

        self.example_duration = 0
        self.target_duration = 0

        # 初始化影片處理器
        self.video_processor = VideoProcessor()

        # 物件分析相關
        self.example_objects = {}  # 存儲範例影片中的物件 {物件類別: [出現次數, 總時長, [時間戳列表]]}
        self.target_objects = {}   # 存儲目標影片中的物件
        self.important_objects = []  # 使用者選定的重要物件
        self.object_model = None  # 物件檢測模型

        # 剪輯偏好
        self.object_transitions = {}  # 物件間的轉場模式 {(物件A, 物件B): 次數}
        self.object_durations = {}    # 每類物件的平均展示時長

        # 分析結果
        self.cut_points = []  # 範例影片的剪輯點
        self.segment_durations = []  # 範例影片的片段時長列表
        self.avg_segment_duration = 0  # 平均片段時長
        self.cutting_density = 0  # 剪輯密度 (每分鐘剪輯次數)

        # 自動剪輯結果
        self.suggested_cuts = []  # 建議的剪輯點
        self.final_cuts = []  # 最終的剪輯點

        # 設置UI
        self.create_ui()

    def create_ui(self):
        # 主框架
        main_frame = ttk.Notebook(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 創建三個主要頁面
        self.analysis_page = AnalysisPage(main_frame, self)
        self.application_page = ApplicationPage(main_frame, self)
        self.output_page = OutputPage(main_frame, self)

        # 將頁面添加到筆記本控件
        main_frame.add(self.analysis_page.frame, text="分析範例影片")
        main_frame.add(self.application_page.frame, text="應用到新素材")
        main_frame.add(self.output_page.frame, text="預覽與輸出")

        # 狀態欄
        self.status_var = tk.StringVar()
        self.status_var.set("就緒")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def disable_all_buttons(self):
        """禁用所有操作按鈕"""
        # 各頁面禁用按鈕
        self.analysis_page.disable_buttons()
        self.application_page.disable_buttons()
        self.output_page.disable_buttons()

        # 更新UI
        self.root.update()

    def enable_all_buttons(self):
        """啟用所有操作按鈕"""
        # 各頁面啟用按鈕
        self.analysis_page.enable_buttons()
        self.application_page.enable_buttons()
        self.output_page.enable_buttons()

        # 更新UI
        self.root.update()

    def update_progress(self, message):
        """更新進度信息"""
        self.status_var.set(message)

    # 在app.py中的initialize_object_detection方法中添加禁用更新檢查：

    def initialize_object_detection(self):
        """初始化物件檢測模型"""
        try:
            self.status_var.set("正在加載物件檢測模型...")

            # 禁用自動更新檢查
            import os
            os.environ['ULTRALYTICS_SKIP_VERSION_CHECK'] = '1'
            os.environ['YOLO_VERBOSE'] = 'False'

            # 使用YOLOv5
            from ultralytics import YOLO
            # 禁用自動更新檢查
            YOLO.checks = lambda *args, **kwargs: None
            self.object_model = YOLO("yolov8n.pt")  # 使用較小的模型確保速度
            # 禁用日誌輸出
            self.object_model.verbose = False

            self.status_var.set("物件檢測模型加載完成")
        except Exception as e:
            messagebox.showerror("錯誤", f"加載物件檢測模型失敗: {str(e)}")
            self.status_var.set("物件檢測模型加載失敗")