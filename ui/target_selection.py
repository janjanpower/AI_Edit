import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk

class ObjectSelectionTool:
    """用於在影片幀上選擇特定目標物件的工具"""

    def __init__(self, parent, app, canvas):
        self.parent = parent
        self.app = app
        self.canvas = canvas
        self.selection_active = False
        self.start_x = 0
        self.start_y = 0
        self.current_rectangle = None
        self.selected_roi = None
        self.original_frame = None

        # 創建控制界面
        self.create_controls()

        # 綁定鼠標事件
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def create_controls(self):
        """創建控制界面"""
        # 創建框架
        self.control_frame = ttk.Frame(self.parent)
        self.control_frame.pack(fill=tk.X, pady=5)

        # 添加按鈕
        self.select_btn = ttk.Button(
            self.control_frame,
            text="選擇目標物件",
            command=self.start_selection
        )
        self.select_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(
            self.control_frame,
            text="清除選擇",
            command=self.clear_selection
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn.config(state=tk.DISABLED)

        # 添加描述標籤
        self.status_label = ttk.Label(
            self.control_frame,
            text="未選擇目標物件"
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

    def start_selection(self):
        """開始選擇目標物件"""
        if self.app.target_cap and self.app.target_cap.isOpened():
            # 重置影片到第一幀
            self.app.target_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.app.target_cap.read()

            if ret:
                # 儲存原始幀以便稍後處理
                self.original_frame = frame.copy()
                # 顯示影片幀並啟用選擇
                self.selection_active = True
                self.status_label.config(text="請在影片上框選目標物件")

                # 禁用選擇按鈕
                self.select_btn.config(state=tk.DISABLED)

    def on_mouse_down(self, event):
        """鼠標按下事件處理"""
        if not self.selection_active:
            return

        # 記錄起始點
        self.start_x = event.x
        self.start_y = event.y

        # 創建矩形
        if self.current_rectangle:
            self.canvas.delete(self.current_rectangle)

        self.current_rectangle = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2
        )

    def on_mouse_move(self, event):
        """鼠標移動事件處理"""
        if not self.selection_active or not self.current_rectangle:
            return

        # 更新矩形大小
        self.canvas.coords(
            self.current_rectangle,
            self.start_x, self.start_y, event.x, event.y
        )

    def on_mouse_up(self, event):
        """鼠標釋放事件處理"""
        if not self.selection_active or not self.current_rectangle:
            return

        # 獲取選擇區域
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        # 確保選擇區域有一定大小
        if (x2 - x1) < 20 or (y2 - y1) < 20:
            self.status_label.config(text="選擇區域太小，請重新選擇")
            return

        # 轉換畫布坐標到原始影片幀坐標
        # 獲取畫布和影片幀的尺寸
        canvas_width = int(self.canvas.cget("width"))
        canvas_height = int(self.canvas.cget("height"))
        frame_height, frame_width = self.original_frame.shape[:2]

        # 計算縮放比例
        width_ratio = frame_width / canvas_width
        height_ratio = frame_height / canvas_height

        # 轉換坐標
        x1_frame = int(x1 * width_ratio)
        y1_frame = int(y1 * height_ratio)
        x2_frame = int(x2 * width_ratio)
        y2_frame = int(y2 * height_ratio)

        # 確保坐標在影片幀範圍內
        x1_frame = max(0, min(x1_frame, frame_width - 1))
        y1_frame = max(0, min(y1_frame, frame_height - 1))
        x2_frame = max(0, min(x2_frame, frame_width - 1))
        y2_frame = max(0, min(y2_frame, frame_height - 1))

        # 存儲選擇的ROI
        self.selected_roi = (x1_frame, y1_frame, x2_frame - x1_frame, y2_frame - y1_frame)
        self.app.target_object_roi = self.selected_roi

        # 從ROI區域提取目標物件特徵
        self.extract_target_features()

        # 更新標籤
        self.status_label.config(text=f"目標物件已選擇 [{x1_frame},{y1_frame},{x2_frame},{y2_frame}]")

        # 啟用清除按鈕
        self.clear_btn.config(state=tk.NORMAL)

        # 結束選擇模式
        self.selection_active = False

    def extract_target_features(self):
        """從選擇區域提取目標物件特徵"""
        if self.original_frame is None or self.selected_roi is None:
            return

        x, y, w, h = self.selected_roi
        roi = self.original_frame[y:y+h, x:x+w]

        # 使用物件檢測模型檢測目標物件
        results = self.app.object_model(roi)

        # 找出檢測框最大的物件作為目標
        best_target = None
        max_area = 0

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # 獲取類別、置信度和座標
                cls_id = int(box.cls[0])
                cls_name = self.app.object_model.names[cls_id]
                conf = float(box.conf[0])

                # 只考慮高置信度的檢測結果
                if conf > 0.5:
                    # 獲取框的座標
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    area = (x2 - x1) * (y2 - y1)

                    if area > max_area:
                        max_area = area
                        best_target = {
                            'class': cls_name,
                            'confidence': conf,
                            'bbox': (x1, y1, x2, y2),
                            'color_hist': self.calculate_color_histogram(roi)
                        }

        # 如果找到目標，存儲其特徵
        if best_target:
            self.app.target_object_features = best_target

            # 獲取中文名稱
            chinese_name = self.app.get_chinese_name(best_target['class'])

            self.status_label.config(
                text=f"已識別為 {chinese_name} (置信度: {best_target['confidence']:.2f})"
            )
        else:
            # 如果沒有檢測到物件，使用顏色直方圖作為特徵
            self.app.target_object_features = {
                'class': 'unknown',
                'confidence': 1.0,
                'bbox': (0, 0, w, h),
                'color_hist': self.calculate_color_histogram(roi)
            }
            self.status_label.config(text="無法識別物件類型，將使用顏色特徵")

    def calculate_color_histogram(self, image):
        """計算影像的顏色直方圖作為特徵"""
        # 轉換到HSV色彩空間
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 計算直方圖
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])

        # 歸一化直方圖
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

        return hist

    def clear_selection(self):
        """清除目標物件選擇"""
        if self.current_rectangle:
            self.canvas.delete(self.current_rectangle)
            self.current_rectangle = None

        self.selected_roi = None
        self.app.target_object_roi = None
        self.app.target_object_features = None

        self.status_label.config(text="未選擇目標物件")
        self.select_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.DISABLED)