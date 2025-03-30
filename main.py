import sys
import tkinter as tk
from tkinter import messagebox

from ui.app import IntelligentVideoEditor


if __name__ == "__main__":
    # 檢查依賴
    try:
        import cv2
        import numpy as np

        # 嘗試導入物件檢測模型
        try:
            from ultralytics import YOLO
        except ImportError:
            if messagebox.askyesno("缺少依賴", "物件檢測功能需要額外的依賴庫，是否要安裝？"):
                import subprocess
                subprocess.call(["pip", "install", "ultralytics"])
                # 安裝完成後重新嘗試導入
                try:
                    from ultralytics import YOLO
                except ImportError:
                    messagebox.showwarning("警告", "無法安裝物件檢測依賴，將以基本模式運行")
    except ImportError as e:
        messagebox.showerror("錯誤", f"缺少必要依賴: {str(e)}")
        sys.exit(1)

    root = tk.Tk()
    app = IntelligentVideoEditor(root)
    root.mainloop()