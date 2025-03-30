import cv2
import numpy as np
import os
from tkinter import messagebox

class VideoProcessor:
    def __init__(self):
        pass

    def analyze_example_video(self, video_path, app, use_object_detection=True):
        """分析範例影片的剪輯風格和物件特徵"""
        # 打開影片
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("無法打開範例影片")

        # 獲取影片信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = frame_count / fps if fps > 0 else 0

        # 重置物件統計
        app.example_objects = {}
        object_track = {}  # 用於追蹤物件 {object_id: {class_id, last_seen, duration}}

        # 場景變化檢測閾值
        threshold = 35
        min_scene_length = int(fps * 0.5)

        # 開始分析
        prev_frame = None
        frame_idx = 0
        app.cut_points = []  # 清空剪輯點列表

        # 每隔幾幀進行物件檢測以提高速度
        detection_interval = 5  # 每5幀檢測一次物件

        # 如果使用物件檢測，確保模型已加載
        if use_object_detection and app.object_model:
            # 禁用模型的詳細輸出
            app.object_model.verbose = False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 轉換為灰度用於場景變化檢測
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 物件檢測 (每隔幾幀)
            if frame_idx % detection_interval == 0 and use_object_detection:
                # 更新進度
                progress = (frame_idx / frame_count) * 100
                app.root.after(0, lambda p=progress: app.update_progress(f"分析進度: {p:.1f}%, 檢測物件中..."))

                # 進行物件檢測
                results = app.object_model(frame)

                # 處理檢測結果
                timestamp = frame_idx / fps
                detected_objects = {}

                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        # 獲取類別、置信度和座標
                        cls_id = int(box.cls[0])
                        cls_name = app.object_model.names[cls_id]
                        conf = float(box.conf[0])

                        # 只考慮高置信度的檢測結果
                        if conf > 0.5:
                            if cls_name not in detected_objects:
                                detected_objects[cls_name] = 1
                            else:
                                detected_objects[cls_name] += 1

                            # 更新物件統計
                            if cls_name not in app.example_objects:
                                app.example_objects[cls_name] = [1, 0, [timestamp]]
                            else:
                                app.example_objects[cls_name][0] += 1
                                app.example_objects[cls_name][2].append(timestamp)

            # 場景變化檢測
            if prev_frame is None:
                prev_frame = gray
                frame_idx += 1
                continue

            # 計算兩幀間的差異
            diff = cv2.absdiff(prev_frame, gray)
            _, diff = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

            # 計算差異百分比
            change_percentage = (np.count_nonzero(diff) * 100) / diff.size

            # 如果變化超過閾值且與前一個剪輯點間隔足夠，標記為剪輯點
            if change_percentage > threshold:
                if not app.cut_points or (frame_idx - app.cut_points[-1]) > min_scene_length:
                    time_point = frame_idx / fps
                    app.cut_points.append(frame_idx)
                    app.root.after(0, lambda: app.update_progress(f"檢測到剪輯點: {time_point:.2f}秒"))

            prev_frame = gray
            frame_idx += 1

            # 每50幀更新進度
            if frame_idx % 50 == 0 and frame_idx % detection_interval != 0:
                progress = (frame_idx / frame_count) * 100
                app.root.after(0, lambda p=progress: app.update_progress(f"分析進度: {p:.1f}%"))

        # 計算每類物件的平均持續時間
        for obj, (count, _, timestamps) in app.example_objects.items():
            # 如果該物件出現超過1次，計算平均間隔
            if len(timestamps) > 1:
                total_interval = timestamps[-1] - timestamps[0]
                avg_duration = total_interval / (len(timestamps) - 1)
                app.object_durations[obj] = avg_duration

        # 計算片段時長和物件關聯性
        app.segment_durations = []

        # 計算剪輯點間的物件轉場關係
        if len(app.cut_points) >= 2:
            for i in range(len(app.cut_points) - 1):
                start_time = app.cut_points[i] / fps
                end_time = app.cut_points[i + 1] / fps
                duration = end_time - start_time
                app.segment_durations.append(duration)

                # 找出該片段的主要物件
                segment_objects = []
                for obj, (_, _, timestamps) in app.example_objects.items():
                    for ts in timestamps:
                        if start_time <= ts <= end_time:
                            segment_objects.append(obj)
                            break

                # 記錄前後片段物件轉場關係
                if i > 0 and segment_objects:
                    prev_start = app.cut_points[i-1] / fps
                    prev_end = start_time
                    prev_objects = []
                    for obj, (_, _, timestamps) in app.example_objects.items():
                        for ts in timestamps:
                            if prev_start <= ts <= prev_end:
                                prev_objects.append(obj)
                                break

                    for prev_obj in prev_objects:
                        for curr_obj in segment_objects:
                            key = (prev_obj, curr_obj)
                            if key not in app.object_transitions:
                                app.object_transitions[key] = 1
                            else:
                                app.object_transitions[key] += 1

        # 加上最後一個片段
        if app.cut_points:
            last_duration = (frame_count - app.cut_points[-1]) / fps
            app.segment_durations.append(last_duration)

        # 計算平均片段時長
        if app.segment_durations:
            app.avg_segment_duration = sum(app.segment_durations) / len(app.segment_durations)
        else:
            app.avg_segment_duration = total_duration

        # 計算剪輯密度 (每分鐘剪輯次數)
        if total_duration > 0:
            app.cutting_density = len(app.cut_points) / (total_duration / 60)
        else:
            app.cutting_density = 0

        # 找出最重要的物件 (出現次數最多的5種)
        important_objects = sorted(app.example_objects.items(),
                                key=lambda x: x[1][0],
                                reverse=True)[:5]
        app.important_objects = [obj[0] for obj in important_objects]

        cap.release()

    def apply_cutting_style(self, video_path, app, object_priority=0.7, density_factor=1.0):
        """將分析出的剪輯風格應用到目標影片"""
        # 打開目標影片
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("無法打開目標素材")

        # 獲取影片信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = frame_count / fps if fps > 0 else 0

        # 重置目標影片物件統計
        app.target_objects = {}

        # 設置分析參數
        threshold = 35  # 場景變化檢測閾值

        # 開始分析
        prev_frame = None
        frame_idx = 0
        app.suggested_cuts = []  # 清空建議剪輯點列表
        scene_changes = []  # 所有潛在的場景變化點
        object_scenes = []  # 包含重要物件的場景 [(開始幀, 結束幀, 物件列表)]

        # 每隔幾幀進行物件檢測
        detection_interval = 10  # 每10幀檢測一次物件

        # 當前場景的物件
        current_scene_start = 0
        current_scene_objects = set()

        while True:
            ret, frame = cap.read()
            if not ret:
                # 處理最後一個場景
                if current_scene_objects and frame_idx > current_scene_start:
                    object_scenes.append((current_scene_start, frame_idx, list(current_scene_objects)))
                break

            # 轉換為灰度用於場景變化檢測
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 物件檢測 (每隔幾幀)
            if frame_idx % detection_interval == 0:
                # 更新進度
                progress = (frame_idx / frame_count) * 100
                app.root.after(0, lambda p=progress: app.update_progress(f"分析進度: {p:.1f}%, 檢測物件中..."))

                # 進行物件檢測
                results = app.object_model(frame)

                # 處理檢測結果
                timestamp = frame_idx / fps
                frame_objects = set()

                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        # 獲取類別、置信度和座標
                        cls_id = int(box.cls[0])
                        cls_name = app.object_model.names[cls_id]
                        conf = float(box.conf[0])

                        # 只考慮高置信度的檢測結果
                        if conf > 0.5:
                            # 加入該幀的物件集合
                            frame_objects.add(cls_name)

                            # 更新物件統計
                            if cls_name not in app.target_objects:
                                app.target_objects[cls_name] = [1, 0, [timestamp]]
                            else:
                                app.target_objects[cls_name][0] += 1
                                app.target_objects[cls_name][2].append(timestamp)

                # 檢查是否有重要物件
                important_detected = False
                for obj in app.important_objects:
                    if obj in frame_objects:
                        important_detected = True
                        current_scene_objects.add(obj)

            # 場景變化檢測
            if prev_frame is None:
                prev_frame = gray
                frame_idx += 1
                continue

            # 計算兩幀間的差異
            diff = cv2.absdiff(prev_frame, gray)
            _, diff = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

            # 計算差異百分比
            change_percentage = (np.count_nonzero(diff) * 100) / diff.size

            # 記錄所有潛在的場景變化點及其變化強度
            if change_percentage > threshold / 2:
                scene_changes.append((frame_idx, change_percentage))

                # 如果變化強度足夠大，考慮結束當前場景並開始新場景
                if change_percentage > threshold:
                    # 確保場景足夠長
                    if frame_idx - current_scene_start > fps * 0.5:
                        # 存儲當前場景信息
                        if current_scene_objects:
                            object_scenes.append((current_scene_start, frame_idx, list(current_scene_objects)))

                        # 開始新場景
                        current_scene_start = frame_idx
                        current_scene_objects = set()

            prev_frame = gray
            frame_idx += 1

            # 每50幀更新進度
            if frame_idx % 50 == 0 and frame_idx % detection_interval != 0:
                progress = (frame_idx / frame_count) * 100
                app.root.after(0, lambda p=progress: app.update_progress(f"分析進度: {p:.1f}%"))

        # 基於物件和場景變化選擇剪輯點
        app.root.after(0, lambda: app.update_progress("基於物件和場景變化選擇剪輯點..."))

        # 排序場景變化點
        scene_changes.sort(key=lambda x: x[0])

        # 應用範例影片剪輯風格到物件場景
        candidate_cuts = []

        # 基於物件場景選擇剪輯點
        for i, (start, end, objects) in enumerate(object_scenes):
            # 檢查是否有重要物件
            has_important = any(obj in app.important_objects for obj in objects)

            if has_important:
                # 保留包含重要物件的場景
                # 計算該場景的理想展示時長 (基於範例影片)
                ideal_duration = 0
                for obj in objects:
                    if obj in app.object_durations:
                        ideal_duration = max(ideal_duration, app.object_durations[obj])

                if ideal_duration == 0:
                    # 使用範例影片的平均片段時長
                    ideal_duration = app.avg_segment_duration

                # 實際場景時長
                actual_duration = (end - start) / fps

                # 如果場景太長，考慮切分
                if actual_duration > ideal_duration * 1.5:
                    # 在場景中找適合的切點
                    scene_internal_changes = [
                        (idx, score) for idx, score in scene_changes
                        if start < idx < end
                    ]

                    # 選擇變化最顯著的點
                    scene_internal_changes.sort(key=lambda x: x[1], reverse=True)

                    # 切分成適合長度的片段
                    segments_needed = int(actual_duration / ideal_duration)

                    if segments_needed > 1 and scene_internal_changes:
                        # 選擇top n-1個變化點作為剪輯點
                        for j in range(min(segments_needed - 1, len(scene_internal_changes))):
                            candidate_cuts.append(scene_internal_changes[j][0])

                # 場景結束是潛在剪輯點
                candidate_cuts.append(end)
            else:
                # 不包含重要物件的場景，僅考慮剪輯密度
                if i > 0:  # 不是第一個場景
                    # 考慮剪輯密度
                    candidate_cuts.append(end)

        # 根據目標剪輯密度過濾剪輯點
        target_density = app.cutting_density * density_factor
        target_cuts_count = int((total_duration / 60) * target_density)

        # 確保至少有一個剪輯點
        if target_cuts_count < 1:
            target_cuts_count = 1

        # 排序和過濾剪輯點
        candidate_cuts.sort()

        # 移除太近的剪輯點
        min_interval = fps * 1.0  # 最小間隔1秒
        filtered_cuts = []
        last_cut = -min_interval

        for cut in candidate_cuts:
            if cut - last_cut >= min_interval:
                filtered_cuts.append(cut)
                last_cut = cut

        # 如果剪輯點太多，選擇間隔分布最均勻的點
        if len(filtered_cuts) > target_cuts_count:
            # 使用等距採樣
            indices = np.linspace(0, len(filtered_cuts) - 1, target_cuts_count, dtype=int)
            filtered_cuts = [filtered_cuts[i] for i in indices]

        # 轉換為秒
        app.suggested_cuts = [cut / fps for cut in filtered_cuts]

        # 設置為最終剪輯點
        app.final_cuts = app.suggested_cuts.copy()

        cap.release()

    def export_video(self, input_path, output_path, cut_points, app, progress_window, progress_var, percent_label):
        """導出最終剪輯影片，移除淡入淡出效果"""
        try:
            # 加载目標影片
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                app.root.after(0, lambda: messagebox.showerror("錯誤", "無法打開目標素材"))
                return

            # 獲取影片信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 創建輸出影片寫入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            # 準備剪輯點，轉換為幀索引
            cut_frames = [int(cut * fps) for cut in cut_points]
            # 在開頭加上0，在結尾加上總幀數
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cut_frames = [0] + cut_frames + [frame_count]

            # 創建片段列表（開始幀和結束幀的對）
            segments = []
            for i in range(len(cut_frames) - 1):
                # 如果是偶數序號的片段，保留它
                if i % 2 == 0:
                    segments.append((cut_frames[i], cut_frames[i+1]))

            # 計算總幀數
            total_frames_to_process = sum(end - start for start, end in segments)
            processed_frames = 0

            # 處理每個片段
            for seg_idx, (start, end) in enumerate(segments):
                # 設置開始位置
                cap.set(cv2.CAP_PROP_POS_FRAMES, start)

                # 讀取並寫入該片段的每一幀
                for frame_idx in range(start, end):
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # 寫入幀
                    out.write(frame)

                    # 更新進度
                    processed_frames += 1
                    progress = int((processed_frames / total_frames_to_process) * 100)
                    progress_var.set(progress)
                    app.root.after(0, lambda p=progress: percent_label.config(text=f"{p}%"))

                    # 每10幀更新一次UI，避免過於頻繁
                    if processed_frames % 10 == 0:
                        app.root.update_idletasks()

            # 釋放資源
            cap.release()
            out.release()

            # 導出完成
            app.root.after(0, lambda: app.status_var.set("導出完成"))
            app.root.after(0, lambda: messagebox.showinfo("成功", "影片導出成功！"))
            app.root.after(0, lambda: progress_window.destroy())
            app.root.after(0, lambda: app.enable_all_buttons())  # 啟用所有按鈕

        except Exception as e:
            app.root.after(0, lambda: messagebox.showerror("錯誤", f"導出過程中發生錯誤: {str(e)}"))
            app.root.after(0, lambda: progress_window.destroy())
            app.root.after(0, lambda: app.enable_all_buttons())  # 啟用所有按鈕