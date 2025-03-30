import cv2
import numpy as np
from PIL import Image, ImageTk

def display_frame(frame, canvas, rotation=0):
    """
    在 Tkinter Canvas 上顯示 OpenCV 幀，支援旋轉並確保影片滿版顯示

    Args:
        frame: OpenCV 讀取的影片幀 (BGR 格式)
        canvas: Tkinter Canvas 對象
        rotation: 旋轉角度，可選值: 0, 90, 180, 270
    """
    # 先處理旋轉
    if rotation != 0:
        if rotation == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # 將 BGR 轉換為 RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 獲取 canvas 尺寸
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 確保 canvas 尺寸有效
    if canvas_width <= 1:
        canvas_width = int(canvas.cget("width"))
    if canvas_height <= 1:
        canvas_height = int(canvas.cget("height"))

    # 計算縮放比例，保持原始寬高比並確保填滿 canvas
    frame_height, frame_width = rgb_frame.shape[:2]
    width_ratio = canvas_width / frame_width
    height_ratio = canvas_height / frame_height

    # 使用較大的縮放比例確保填滿 canvas
    scale_ratio = max(width_ratio, height_ratio)

    # 縮放影片幀
    new_width = int(frame_width * scale_ratio)
    new_height = int(frame_height * scale_ratio)
    rgb_frame = cv2.resize(rgb_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # 如果縮放後的影片大於 canvas，需要裁剪中心部分
    if new_width > canvas_width or new_height > canvas_height:
        # 計算裁剪的起始位置，確保裁剪中心部分
        start_x = max(0, (new_width - canvas_width) // 2)
        start_y = max(0, (new_height - canvas_height) // 2)
        # 裁剪圖像
        rgb_frame = rgb_frame[start_y:start_y+canvas_height, start_x:start_x+canvas_width]
        # 重新檢查尺寸，確保不超過 canvas
        if rgb_frame.shape[1] > canvas_width:
            rgb_frame = rgb_frame[:, 0:canvas_width]
        if rgb_frame.shape[0] > canvas_height:
            rgb_frame = rgb_frame[0:canvas_height, :]

    # 轉換為 PIL 圖像，然後轉換為 Tkinter 圖像
    pil_img = Image.fromarray(rgb_frame)
    tk_img = ImageTk.PhotoImage(image=pil_img)

    # 保存參考以防止垃圾回收
    canvas.tk_img = tk_img

    # 清除當前畫布並顯示圖像
    canvas.delete("all")

    # 在畫布中央顯示圖像
    canvas.create_image(0, 0, anchor="nw", image=tk_img)