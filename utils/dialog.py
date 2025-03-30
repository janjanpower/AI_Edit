import tkinter as tk
from tkinter import ttk

# 簡易對話框類
class simpledialog:
    @staticmethod
    def askstring(title, prompt):
        """
        創建一個簡單的輸入對話框
        """
        dialog = tk.Toplevel()
        dialog.title(title)
        dialog.geometry("300x150")
        dialog.resizable(False, False)

        ttk.Label(dialog, text=prompt).pack(pady=10)

        entry_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=entry_var, width=20)
        entry.pack(pady=10)
        entry.focus_set()

        result = [None]  # 使用列表存儲結果以便於在函數內修改

        def on_ok():
            result[0] = entry_var.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(dialog, text="確定", command=on_ok).pack(side=tk.LEFT, padx=20, pady=10)
        ttk.Button(dialog, text="取消", command=on_cancel).pack(side=tk.RIGHT, padx=20, pady=10)

        # 使對話框模態
        dialog.transient(dialog.master)
        dialog.grab_set()
        dialog.wait_window()

        return result[0]