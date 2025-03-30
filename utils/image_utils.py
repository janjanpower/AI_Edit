import cv2
import tkinter as tk
from PIL import Image, ImageTk

def display_frame(frame, canvas):
    """
    將 OpenCV 幀顯示到 Tkinter Canvas 上
    修復圖像方向問題
    """
    # 調整幀大小來適應畫布
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # 如果畫布還沒有實際大小，使用默認值
    if canvas_width <= 1:
        canvas_width = 640
    if canvas_height <= 1:
        canvas_height = 360

    # 計算縮放比例
    frame_height, frame_width = frame.shape[:2]
    scale_width = canvas_width / frame_width
    scale_height = canvas_height / frame_height
    scale = min(scale_width, scale_height)

    # 計算新的尺寸
    new_width = int(frame_width * scale)
    new_height = int(frame_height * scale)

    # 調整大小
    resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # 將 BGR 轉換為 RGB (OpenCV 使用 BGR，而 PIL 使用 RGB)
    rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    # 轉換為 PIL Image 和 PhotoImage
    image = Image.fromarray(rgb_frame)
    photo = ImageTk.PhotoImage(image=image)

    # 顯示圖像
    canvas.create_image(canvas_width//2, canvas_height//2, image=photo, anchor=tk.CENTER)
    canvas.image = photo  # 保持引用，防止被垃圾回收