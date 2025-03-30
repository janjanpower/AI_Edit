import cv2
import numpy as np
from PIL import Image, ImageTk

def display_frame(frame, canvas, rotation=0):
    """
    在 Tkinter Canvas 上顯示 OpenCV 幀，支援旋轉

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

    # 調整大小以適應 canvas
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 確保 canvas 尺寸有效
    if canvas_width <= 1:
        canvas_width = int(canvas.cget("width"))
    if canvas_height <= 1:
        canvas_height = int(canvas.cget("height"))

    # 計算縮放比例，保持原始寬高比
    frame_height, frame_width = rgb_frame.shape[:2]
    width_ratio = canvas_width / frame_width
    height_ratio = canvas_height / frame_height
    scale_ratio = min(width_ratio, height_ratio)

    # 縮放影片幀
    if scale_ratio != 1:
        new_width = int(frame_width * scale_ratio)
        new_height = int(frame_height * scale_ratio)
        rgb_frame = cv2.resize(rgb_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # 轉換為 PIL 圖像，然後轉換為 Tkinter 圖像
    pil_img = Image.fromarray(rgb_frame)
    tk_img = ImageTk.PhotoImage(image=pil_img)

    # 保存參考以防止垃圾回收
    canvas.tk_img = tk_img

    # 清除當前畫布並顯示圖像
    canvas.delete("all")

    # 在畫布中央顯示圖像
    x_position = max(0, (canvas_width - tk_img.width()) // 2)
    y_position = max(0, (canvas_height - tk_img.height()) // 2)
    canvas.create_image(x_position, y_position, anchor="nw", image=tk_img)