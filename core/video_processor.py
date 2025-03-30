import cv2
import numpy as np
import os
from tkinter import messagebox

class VideoProcessor:
    def __init__(self):
        pass

    def analyze_example_video(self, video_path, app, use_object_detection=True, rotation=0):
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

            # 應用旋轉
            if rotation != 0:
                if rotation == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif rotation == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif rotation == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

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
        """將分析出的剪輯風格應用到目標影片，支持目標物件追蹤"""
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
        app.target_object_track_ids = set()
        app.target_object_timestamps = []

        # 設置分析參數
        threshold = 35  # 場景變化檢測閾值

        # 開始分析
        prev_frame = None
        frame_idx = 0
        app.suggested_cuts = []  # 清空建議剪輯點列表
        scene_changes = []  # 所有潛在的場景變化點
        object_scenes = []  # 包含重要物件的場景 [(開始幀, 結束幀, 物件列表)]
        target_object_occurrences = []  # 目標物件出現的段落 [(開始幀, 結束幀)]

        # 每隔幾幀進行物件檢測
        detection_interval = 10  # 每10幀檢測一次物件

        # 當前場景的物件
        current_scene_start = 0
        current_scene_objects = set()

        # 使用 Ultralytics 追蹤功能
        tracker_active = app.target_object_features is not None
        target_similarity_threshold = 0.6  # 目標物件相似度閾值

        # 追蹤目標物件
        target_object_class = None
        if app.target_object_features and 'class' in app.target_object_features:
            target_object_class = app.target_object_features['class']

        # 目標物件狀態
        target_object_tracking = False
        target_object_start_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                # 處理最後一個場景
                if current_scene_objects and frame_idx > current_scene_start:
                    object_scenes.append((current_scene_start, frame_idx, list(current_scene_objects)))

                # 處理最後一個目標物件片段
                if target_object_tracking and target_object_start_frame is not None:
                    target_object_occurrences.append((target_object_start_frame, frame_idx))

                break

            # 應用旋轉
            if app.target_rotation != 0:
                if app.target_rotation == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif app.target_rotation == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif app.target_rotation == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # 轉換為灰度用於場景變化檢測
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 物件檢測和追蹤 (每隔幾幀)
            if frame_idx % detection_interval == 0:
                # 更新進度
                progress = (frame_idx / frame_count) * 100
                app.root.after(0, lambda p=progress: app.update_progress(f"分析進度: {p:.1f}%, 檢測物件中..."))

                # 進行物件檢測與追蹤
                if tracker_active:
                    # 使用追蹤功能
                    results = app.object_model.track(frame, persist=True)
                else:
                    # 只進行檢測
                    results = app.object_model(frame)

                # 處理檢測和追蹤結果
                timestamp = frame_idx / fps
                frame_objects = set()
                target_object_detected = False

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

                            # 檢查是否是目標物件類型
                            if target_object_class and cls_name == target_object_class:
                                # 獲取物件區域
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                obj_region = frame[int(y1):int(y2), int(x1):int(x2)]

                                if obj_region.size > 0:  # 確保區域有效
                                    # 提取物件特徵
                                    obj_features = self.extract_object_features(obj_region)

                                    # 比較與目標物件的相似度
                                    similarity = self.compare_features(
                                        app.target_object_features,
                                        obj_features
                                    )

                                    if similarity > target_similarity_threshold:
                                        target_object_detected = True

                                        # 如果有追蹤ID，記錄它
                                        if hasattr(box, 'id') and box.id is not None:
                                            track_id = int(box.id)
                                            app.target_object_track_ids.add(track_id)

                # 更新目標物件追蹤狀態
                if target_object_detected:
                    # 記錄目標物件時間戳
                    app.target_object_timestamps.append(timestamp)

                    # 如果之前沒有追蹤，開始新的追蹤段落
                    if not target_object_tracking:
                        target_object_tracking = True
                        target_object_start_frame = frame_idx
                else:
                    # 如果之前在追蹤，結束追蹤段落
                    if target_object_tracking:
                        target_object_tracking = False
                        if target_object_start_frame is not None:
                            target_object_occurrences.append(
                                (target_object_start_frame, frame_idx)
                            )
                            target_object_start_frame = None

                # 更新當前場景物件
                for obj in frame_objects:
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

        # 如果有特定目標物件，優先處理包含目標物件的片段
        if tracker_active and target_object_occurrences:
            app.root.after(0, lambda: app.update_progress(f"發現目標物件出現 {len(target_object_occurrences)} 次"))

            # 處理每個目標物件出現的段落
            for start_frame, end_frame in target_object_occurrences:
                # 將段落起始和結束點加入候選剪輯點
                candidate_cuts.append(start_frame)
                candidate_cuts.append(end_frame)

                # 如果段落較長，考慮在段落內部添加剪輯點
                segment_duration = (end_frame - start_frame) / fps

                if segment_duration > app.avg_segment_duration * 1.5:
                    # 在段落中找適合的切點
                    internal_changes = [
                        (idx, score) for idx, score in scene_changes
                        if start_frame < idx < end_frame
                    ]

                    # 選擇變化最顯著的點
                    internal_changes.sort(key=lambda x: x[1], reverse=True)

                    # 添加適當數量的內部剪輯點
                    segments_needed = int(segment_duration / app.avg_segment_duration)

                    if segments_needed > 1 and internal_changes:
                        for i in range(min(segments_needed - 1, len(internal_changes))):
                            candidate_cuts.append(internal_changes[i][0])

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

    def compare_features(self, features1, features2):
        """比較兩個物件特徵的相似度"""
        if features1 is None or features2 is None:
            return 0

        # 比較顏色直方圖
        if 'color_hist' in features1 and 'color_hist' in features2:
            similarity = cv2.compareHist(
                features1['color_hist'],
                features2['color_hist'],
                cv2.HISTCMP_CORREL
            )
            return max(0, similarity)  # 確保相似度非負

        return 0

    def extract_object_features(self, image):
        """從物件圖像中提取特徵"""
        if image.size == 0 or image.shape[0] == 0 or image.shape[1] == 0:
            return None

        # 轉換到HSV色彩空間
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        except:
            return None

        # 計算直方圖
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])

        # 歸一化直方圖
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

        return {'color_hist': hist}

    # 完整替換 export_video 函數，徹底避免 lambda 作用域問題

    def export_video(self, input_path, output_path, cut_points, app, progress_window, progress_var, percent_label):
        """導出最終剪輯影片，包含原始音頻"""

        # 定義所有需要的回調函數，避免使用 lambda
        def show_error(message):
            """顯示錯誤訊息"""
            messagebox.showerror("錯誤", message)
            progress_window.destroy()
            app.enable_all_buttons()

        def show_success(message):
            """顯示成功訊息"""
            messagebox.showinfo("成功", message)
            progress_window.destroy()
            app.enable_all_buttons()

        def update_status(message):
            """更新狀態欄"""
            app.status_var.set(message)

        def update_progress(value):
            """更新進度條"""
            progress_var.set(value)
            percent_label.config(text=f"{value}%")

        def finish_with_error(message):
            """錯誤完成處理"""
            app.root.after(0, lambda: show_error(message))

        def finish_with_success(message, final_path):
            """成功完成處理"""
            app.root.after(0, lambda: show_success(message))
            app.root.after(0, lambda: update_status(f"影片已導出至: {final_path}"))

        # 正式執行導出
        try:
            import os
            import subprocess
            import shutil

            # 檢查輸出目錄
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    return finish_with_error(f"無法創建輸出目錄: {str(e)}")

            # 確認可寫入
            try:
                temp_test_file = output_path + ".test"
                with open(temp_test_file, 'w') as f:
                    f.write("test")
                os.remove(temp_test_file)
            except Exception as e:
                return finish_with_error(f"輸出路徑不可寫: {str(e)}")

            # 檢查剪輯點
            if not cut_points:
                return finish_with_error("沒有設定剪輯點")

            # 打開影片
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                return finish_with_error("無法打開目標素材")

            # 獲取影片信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 創建臨時檔案
            temp_output = output_path + ".temp.mp4"
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except Exception as e:
                    return finish_with_error(f"無法刪除已存在的臨時文件: {str(e)}")

            # 建立檔案寫入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
            if not out.isOpened():
                return finish_with_error("無法創建輸出視頻文件")

            # 處理剪輯點
            cut_frames = [int(cut * fps) for cut in cut_points]
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cut_frames = [0] + cut_frames + [frame_count]

            # 建立片段
            segments = []
            for i in range(len(cut_frames) - 1):
                if i % 2 == 0:
                    segments.append((cut_frames[i], cut_frames[i+1]))

            # 計算總幀數
            total_frames_to_process = sum(end - start for start, end in segments)
            if total_frames_to_process <= 0:
                cap.release()
                return finish_with_error("沒有要處理的視頻幀")

            # 處理視頻
            app.root.after(0, lambda: update_status("正在處理視頻幀..."))
            processed_frames = 0

            for start, end in segments:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                for frame_idx in range(start, end):
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # 應用旋轉
                    if app.target_rotation != 0:
                        if app.target_rotation == 90:
                            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                        elif app.target_rotation == 180:
                            frame = cv2.rotate(frame, cv2.ROTATE_180)
                        elif app.target_rotation == 270:
                            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

                    # 寫入幀
                    out.write(frame)

                    # 更新進度
                    processed_frames += 1
                    progress = int((processed_frames / total_frames_to_process) * 80)
                    app.root.after(0, lambda p=progress: update_progress(p))

                    # 更新UI
                    if processed_frames % 10 == 0:
                        app.root.update_idletasks()

            # 釋放資源
            cap.release()
            out.release()

            # 檢查臨時檔案
            if not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
                return finish_with_error("視頻處理失敗，臨時文件創建失敗")

            # 處理音頻
            app.root.after(0, lambda: update_status("處理音頻中..."))
            app.root.after(0, lambda: update_progress(80))

            # 確保輸出路徑不存在
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception as e:
                    return finish_with_error(f"無法刪除已存在的輸出文件: {str(e)}")

            # 檢查 ffmpeg
            try:
                subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                app.root.after(0, lambda: update_status("未檢測到ffmpeg，將輸出無聲影片"))
                shutil.copy(temp_output, output_path)

                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    if os.path.exists(temp_output):
                        try:
                            os.remove(temp_output)
                        except:
                            pass

                    app.root.after(0, lambda: update_progress(100))
                    return finish_with_success("影片導出成功！", output_path)
                else:
                    return finish_with_error("影片輸出失敗")

            # 創建音頻處理命令
            audio_filter = ""
            for i, (start, end) in enumerate(segments):
                if i > 0:
                    audio_filter += ";"
                start_time = start / fps
                end_time = end / fps
                if i == 0:
                    audio_filter += f"[0:a]atrim=start={start_time}:end={end_time},asetpts=PTS-STARTPTS[a{i}]"
                else:
                    audio_filter += f"[0:a]atrim=start={start_time}:end={end_time},asetpts=PTS-STARTPTS[a{i}]"

            # 連接音頻片段
            if segments:
                for i in range(len(segments)):
                    audio_filter += f"[a{i}]"
                audio_filter += f"concat=n={len(segments)}:v=0:a=1[outa]"

                # FFmpeg 命令
                cmd = [
                    "ffmpeg",
                    "-i", temp_output,
                    "-i", input_path,
                    "-filter_complex", audio_filter,
                    "-map", "0:v",
                    "-map", "[outa]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    "-y",
                    output_path
                ]

                # 執行 FFmpeg
                try:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()

                    if process.returncode != 0:
                        app.root.after(0, lambda: update_status("音頻處理出錯，將輸出無聲影片"))
                        print(f"FFmpeg錯誤: {stderr.decode('utf-8', errors='replace')}")
                        shutil.copy(temp_output, output_path)

                    # 檢查輸出
                    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                        shutil.copy(temp_output, output_path)

                except Exception as e:
                    app.root.after(0, lambda: update_status(f"音頻處理出錯: {str(e)}"))
                    print(f"音頻處理錯誤: {str(e)}")
                    shutil.copy(temp_output, output_path)

            # 最終檢查
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                app.root.after(0, lambda: update_progress(100))

                # 清理臨時文件
                if os.path.exists(temp_output):
                    try:
                        os.remove(temp_output)
                    except Exception as e:
                        print(f"刪除臨時文件失敗: {str(e)}")

                return finish_with_success("影片導出成功！", output_path)
            else:
                return finish_with_error("影片輸出失敗")

        except Exception as e:
            return finish_with_error(f"導出過程中發生錯誤: {str(e)}")