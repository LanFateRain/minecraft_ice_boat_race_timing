import json
import os
import time
import threading # 用于后台保存
import copy      # 用于数据快照
from datetime import datetime
import geometry_utils
import data_save
import config

# ==========================================
# 后台任务函数 (独立于类，避免 self 引用复杂化)
# ==========================================
def background_save_worker(json_filename, json_data, csv_handle, csv_path):
    """
    后台守护线程执行的逻辑：
    1. 写入 JSON (使用快照数据，原子写入)
    2. 关闭 CSV 文件句柄
    3. 调用绘图模块生成图片
    """
    # --- 1. JSON 保存 ---
    if json_filename and json_data:
        try:
            # 这里的 json_data 是主线程传过来的 deepcopy 快照，读写安全
            # 使用 Atomic Write (写临时文件 -> 重命名)，防止写入一半程序崩溃导致文件损坏
            temp_file = json_filename + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4)
            
            # Windows 下 rename 无法覆盖已存在文件，需先 remove
            if os.path.exists(json_filename):
                os.remove(json_filename)
            os.rename(temp_file, json_filename)
        except Exception as e:
            print(f"[System] ❌ 后台 JSON 保存失败: {e}")

    # --- 2. CSV 关闭与绘图 ---
    if csv_handle:
        try:
            csv_handle.close() # 在这里真正关闭文件，将缓冲区数据刷入磁盘
            # print(f"[Record] 数据保存成功 (后台): {os.path.basename(csv_path)}")
            
            # 如果绘图库可用，生成轨迹图
            if data_save.PLOT_AVAILABLE and csv_path:
                # print("[Plot] 正在生成分析图 (后台)...")
                data_save.plot_total.plot_track_data(csv_path)
        except Exception as e:
            print(f"[System] ❌ 后台 CSV 处理失败: {e}")


# ==========================================
# 核心逻辑类
# ==========================================
class RaceLogic:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        
        # --- 1. 动态计算文件名 ---
        suffix = getattr(config, 'HISTORY_FILE_SUFFIX', '')
        if suffix:
            self.history_filename = f'race_history_{suffix}.json'
        else:
            self.history_filename = 'race_history.json'
        self.save_enabled = getattr(config, 'ENABLE_HISTORY_SAVE', True)
        
        if not self.test_mode:
            mode_str = "读写模式" if self.save_enabled else "只读模式 (不保存)"
            print(f"[System] 历史文件目标: {self.history_filename} [{mode_str}]")

        # --- 2. 直接从 Config 获取 Checkpoints ---
        self.checkpoints = config.CHECKPOINTS
        print(f"[System] RaceLogic 已同步 {len(self.checkpoints)} 个检查点 (Config源)")

        self.best_lap = None
        self.history = []
        self.total_valid_laps_count = 0 
        
        self.recorder = None
        if config.SAVE_DATA and not self.test_mode:
            print("[System] 轨迹记录已开启")
            self.recorder = data_save.DataRecorder()
        
        self.next_target_index = 0 
        self.current_lap_start_time = 0
        self.last_checkpoint_time = 0
        self.visited_checkpoints_count = 0
        self.current_sector_start_time = 0
        
        self.current_lap_data = {"segments": [], "sectors": [], "total_time": 0}
        
        # 3. 加载历史
        if not self.test_mode:
            self.load_history()

    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_filename):
            try:
                with open(self.history_filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                
                self.total_valid_laps_count = len(self.history)
                print(f"[System] 正在重构 {len(self.history)} 条历史记录...")
                self.rebuild_stats_from_history()
                
            except Exception as e:
                print(f"[System] 历史读取错误 ({e})，初始化默认值...")
                self.init_default_best_lap()
        else:
            print(f"[System] 历史文件不存在，初始化默认值...")
            self.init_default_best_lap()

    def init_default_best_lap(self):
        """构建默认标准成绩 (25分钟)"""
        segs, secs = [], []
        sec_counter = 0
        now_ts = time.time()
        now_str = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d %H:%M:%S")

        default_seg_time = 60.0
        default_sec_time = 300.0
        default_total_time = 1500.0

        for i, cp in enumerate(self.checkpoints):
            # Mini-Sector
            segs.append({
                "index": i, "name": cp['name'], 
                "duration": default_seg_time, 
                "formatted_time": self.format_time(default_seg_time), 
                "delta": "+0.000", "color": "yellow",
                "timestamp": now_ts, "match_time": now_str,
                "rolling_queue": [] 
            })
            
            # Sector
            if cp.get('is_sector', False):
                secs.append({
                    "index": sec_counter, "name": cp['name'], 
                    "duration": default_sec_time, 
                    "formatted_duration": self.format_time(default_sec_time),
                    "color": "yellow",
                    "timestamp": now_ts, "match_time": now_str,
                    "rolling_queue": [] 
                })
                sec_counter += 1
        
        self.best_lap = {
            "total_time": default_total_time, 
            "formatted_total_time": self.format_time(default_total_time),
            "segments": segs, 
            "sectors": secs, 
            "delta": "+0.000", 
            "color": "yellow", 
            "timestamp": now_ts, "match_time": now_str,
            "rolling_queue": [] 
        }
        
        # 如果是第一次创建且允许保存，则立即写入默认文件
        if not self.history and not self.test_mode and self.save_enabled:
            try:
                with open(self.history_filename, 'w', encoding='utf-8') as f:
                    json.dump({"best_lap": self.best_lap, "history": self.history}, f, indent=4)
                print(f"[System] 已创建默认历史文件: {self.history_filename}")
            except Exception as e:
                print(f"[System] ⚠️ 无法创建历史文件: {e}")

    def rebuild_stats_from_history(self):
        self.init_default_best_lap()
        if not self.history: return
        
        enable_stage_rolling = getattr(config, 'ENABLE_STAGE_ROLLING_WINDOW_BEST', True)
        stage_window = getattr(config, 'STAGE_ROLLING_WINDOW_SIZE', 10)
        enable_loop_rolling = getattr(config, 'ENABLE_LOOP_ROLLING_WINDOW_BEST', True)
        loop_window = getattr(config, 'LOOP_ROLLING_WINDOW_SIZE', 20)

        for idx, lap_data in enumerate(self.history):
            current_lap_idx = idx + 1 
            lap_data['lap_index'] = current_lap_idx
            
            if lap_data['total_time'] < self.best_lap['total_time']:
                self._update_best_lap_fields(lap_data)

            for i, seg in enumerate(lap_data.get('segments', [])):
                if i < len(self.best_lap['segments']):
                    if seg['duration'] < self.best_lap['segments'][i]['duration']:
                        self._update_best_segment_fields(i, seg)

            for i, sec in enumerate(lap_data.get('sectors', [])):
                if i < len(self.best_lap['sectors']):
                    if sec['duration'] < self.best_lap['sectors'][i]['duration']:
                        self._update_best_sector_fields(i, sec)

            if enable_loop_rolling:
                q = self.best_lap.get('rolling_queue', [])
                self.best_lap['rolling_queue'] = self._update_monotonic_queue(
                    q, lap_data['total_time'], current_lap_idx, loop_window
                )
            
            if enable_stage_rolling:
                for i, seg in enumerate(lap_data.get('segments', [])):
                    if i < len(self.best_lap['segments']):
                        q = self.best_lap['segments'][i].get('rolling_queue', [])
                        self.best_lap['segments'][i]['rolling_queue'] = self._update_monotonic_queue(
                            q, seg['duration'], current_lap_idx, stage_window
                        )
                for i, sec in enumerate(lap_data.get('sectors', [])):
                    if i < len(self.best_lap['sectors']):
                        q = self.best_lap['sectors'][i].get('rolling_queue', [])
                        self.best_lap['sectors'][i]['rolling_queue'] = self._update_monotonic_queue(
                            q, sec['duration'], current_lap_idx, stage_window
                        )

        bt = self.best_lap.get('formatted_total_time', 'N/A')
        print(f"[System] 历史数据重构完成。当前基准: {bt}")

    # 以下辅助更新方法展开写，方便阅读
    def _update_best_lap_fields(self, source_data):
        self.best_lap.update({
            'total_time': source_data['total_time'],
            'formatted_total_time': source_data['formatted_total_time'],
            'delta': source_data.get('delta', '+0.000'),
            'color': source_data.get('color', 'yellow'),
            'timestamp': source_data.get('timestamp', time.time()),
            'match_time': source_data.get('match_time', '')
        })

    def _update_best_segment_fields(self, idx, source_seg):
        self.best_lap['segments'][idx].update({
            'duration': source_seg['duration'],
            'formatted_time': source_seg['formatted_time'],
            'color': source_seg.get('color', 'yellow'),
            'timestamp': source_seg.get('timestamp'),
            'match_time': source_seg.get('match_time')
        })

    def _update_best_sector_fields(self, idx, source_sec):
        self.best_lap['sectors'][idx].update({
            'duration': source_sec['duration'],
            'formatted_duration': source_sec['formatted_duration'],
            'color': source_sec.get('color', 'yellow'),
            'timestamp': source_sec.get('timestamp'),
            'match_time': source_sec.get('match_time')
        })

    def _update_monotonic_queue(self, queue, new_time, new_index, window_size):
        if queue is None: queue = []
        while queue and new_index - queue[0]['index'] >= window_size:
            queue.pop(0)
        while queue and queue[-1]['time'] >= new_time:
            queue.pop()
        queue.append({'index': new_index, 'time': new_time})
        return queue

    def check_entry(self, car_x, car_z):
        if not self.checkpoints: return False
        if self.next_target_index >= len(self.checkpoints): return False
        
        target = self.checkpoints[self.next_target_index]
        target_line = target.get('line', target.get('shape_config'))
        
        dist = geometry_utils.point_to_line_segment_distance((car_x, car_z), target_line)
        return dist <= target['trigger_dist']

    def update_continuous_data(self, x, z, speed):
        if self.recorder and self.recorder.is_recording:
            self.recorder.log_step([time.time(), x, 0.0, z, speed])

    def start_new_lap(self, explicit_start_time=None, last_pos_snapshot=None):
        if explicit_start_time:
            self.current_lap_start_time = explicit_start_time
        else:
            self.current_lap_start_time = time.time()
            
        self.last_checkpoint_time = self.current_lap_start_time
        self.current_sector_start_time = self.current_lap_start_time
        self.visited_checkpoints_count = 0
        self.next_target_index = 0
        self.current_lap_data = {"segments": [], "sectors": [], "total_time": 0}
        
        print(f"\n=== 新圈开始 ===")
        if self.checkpoints:
            print(f">>> 🎯 目标: {self.checkpoints[0]['name']}")
            
        if self.recorder: 
            self.recorder.start_new_session(['time', 'x', 'y', 'z', 'speed'])
            if explicit_start_time and last_pos_snapshot:
                # 记录缝合数据，用于连接上一圈的轨迹
                patch_row = [explicit_start_time, last_pos_snapshot[0], 0.0, last_pos_snapshot[1], last_pos_snapshot[2]]
                self.recorder.log_step(patch_row)
                print(f"[System] 已执行数据缝合 (延时补偿: {time.time() - explicit_start_time:.3f}s)")

    def process_hit(self):
        current_idx = self.next_target_index
        if current_idx >= len(self.checkpoints): return {"status": "error"}

        result = self.process_checkpoint(current_idx)
        status = result.get('status', 'running')
        
        if status == 'running':
            if current_idx + 1 < len(self.checkpoints):
                self.next_target_index = current_idx + 1
        return result

    def get_comparison_baseline(self, best_item_dict, default_val, enable_rolling):
        if not best_item_dict: return default_val
        if enable_rolling:
            queue = best_item_dict.get('rolling_queue', [])
            if queue:
                return queue[0]['time']
        return best_item_dict.get('duration', best_item_dict.get('total_time', default_val))

    def process_checkpoint(self, cp_index):
        if self.current_lap_start_time == 0: self.start_new_lap()
        
        now = time.time()
        now_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

        cp = self.checkpoints[cp_index]
        self.visited_checkpoints_count += 1
        
        is_last_point = (cp_index == len(self.checkpoints) - 1)
        is_major_trigger = cp.get('is_sector', False)
        
        # ==========================================
        # 1. Mini-Sector 处理
        # ==========================================
        seg_dur = now - self.last_checkpoint_time
        self.last_checkpoint_time = now
        
        best_seg_dict = None
        if self.best_lap and cp_index < len(self.best_lap['segments']): 
            best_seg_dict = self.best_lap['segments'][cp_index]
            
        limit = config.DEFAULT_SEGMENT_TIME if hasattr(config, 'DEFAULT_SEGMENT_TIME') else 60.0
        stage_rolling_enabled = getattr(config, 'ENABLE_STAGE_ROLLING_WINDOW_BEST', False)
        baseline_time = self.get_comparison_baseline(best_seg_dict, limit, stage_rolling_enabled)
        
        c, d = self.get_color_and_delta(seg_dur, baseline_time, limit, config.TIME_DELAY_LIMIT_1, config.TIME_DELAY_LIMIT_2)
        
        seg_rec = {
            "index": cp_index, "name": cp['name'], 
            "duration": seg_dur, "formatted_time": self.format_time(seg_dur), 
            "delta": d, "color": c,
            "timestamp": now, "match_time": now_str
        }
        self.current_lap_data['segments'].append(seg_rec)
        
        blk = self.get_status_block(c)
        print(f"[{cp['name']}] Mini-Sector {cp_index + 1}: {seg_rec['formatted_time']} ({d}) {blk}")

        # ==========================================
        # 2. Sector 处理
        # ==========================================
        sec_rec = None
        if is_major_trigger:
            sec_dur = now - self.current_sector_start_time
            sec_idx = len(self.current_lap_data['sectors'])
            
            best_sec_dict = None
            if self.best_lap and sec_idx < len(self.best_lap['sectors']): 
                best_sec_dict = self.best_lap['sectors'][sec_idx]
            
            factor = 5 
            sector_factor = getattr(config, 'SECTOR_TIME_DELAY_FACTOR', 0.4)
            sector_limit1 = config.TIME_DELAY_LIMIT_1 * factor * sector_factor
            sector_limit2 = config.TIME_DELAY_LIMIT_2 * factor * sector_factor

            baseline_sec_time = self.get_comparison_baseline(best_sec_dict, 300.0, stage_rolling_enabled)
            
            sc, sd = self.get_color_and_delta(sec_dur, baseline_sec_time, 300.0, sector_limit1, sector_limit2)
            
            sec_rec = {
                "index": sec_idx, "name": cp['name'], 
                "duration": sec_dur, "formatted_duration": self.format_time(sec_dur),
                "delta": sd, 
                "color": sc,
                "timestamp": now, "match_time": now_str
            }
            self.current_lap_data['sectors'].append(sec_rec)
            self.current_sector_start_time = now 
            
            s_blk = self.get_status_block(sc)
            print(f"★ [{cp['name']}] Sector {sec_idx+1}: {sec_rec['formatted_duration']} ({sd}) {s_blk}")

        # ==========================================
        # 3. 构建并返回结果
        # ==========================================
        result = {
            "status": "running", 
            "segment": seg_rec, 
            "sector": sec_rec
        }

        # 4. Lap Finish 判断
        if is_last_point:
            finish_result = self.attempt_finish_lap()
            result.update(finish_result)
            
        return result

    def attempt_finish_lap(self):
        now = time.time()
        now_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        total_time = now - self.current_lap_start_time
        
        if self.visited_checkpoints_count < len(self.checkpoints):
            print(f"⚠️ [无效圈] 漏点 ({self.visited_checkpoints_count}/{len(self.checkpoints)})")
            self.abort_lap() 
            self.start_new_lap()
            return {"status": "invalid_missed"}

        if total_time < config.MIN_LAP_TIME:
            print(f"⚠️ [无效圈] 时间过短 (<{config.MIN_LAP_TIME}s)")
            self.abort_lap()
            self.start_new_lap()
            return {"status": "invalid_short"}

        self.current_lap_data['total_time'] = total_time
        self.current_lap_data['formatted_total_time'] = self.format_time(total_time)
        self.current_lap_data['timestamp'] = now
        self.current_lap_data['match_time'] = now_str
        
        # 计算 Loop Delta
        loop_rolling_enabled = getattr(config, 'ENABLE_LOOP_ROLLING_WINDOW_BEST', False)
        baseline_total = self.get_comparison_baseline(self.best_lap, 1500.0, loop_rolling_enabled)
        
        loop_factor = getattr(config, 'LOOP_TIME_DELAY_FACTOR', 0.16)
        total_segments_count = len(self.checkpoints)
        if total_segments_count == 0: total_segments_count = 25 
        
        loop_limit1 = config.TIME_DELAY_LIMIT_1 * total_segments_count * loop_factor
        loop_limit2 = config.TIME_DELAY_LIMIT_2 * total_segments_count * loop_factor
        
        lc, ld = self.get_color_and_delta(total_time, baseline_total, 1500.0, loop_limit1, loop_limit2)
        
        self.current_lap_data['delta'] = ld
        self.current_lap_data['color'] = lc
        
        finish_name = self.checkpoints[-1]['name']
        l_blk = self.get_status_block(lc)
        print(f"★★ [{finish_name}] Loop: {self.current_lap_data['formatted_total_time']} ({ld}) {l_blk}")

        # === 核心修改区：准备异步数据，彻底消除卡顿 ===
        final_data_for_ui = self.current_lap_data.copy()
        
        json_snapshot_data = None
        csv_handle = None
        csv_path = None
        
        # 1. 更新内存数据 (逻辑同步执行，确保内存中 Best Lap 立即更新)
        if not self.test_mode and self.save_enabled:
            self._update_memory_history_logic() 
            # 创建快照供后台写入，deepcopy 防止后续数据变动影响写入
            json_snapshot_data = {
                "best_lap": copy.deepcopy(self.best_lap),
                "history": list(self.history)
            }
        
        # 2. 剥离 CSV 句柄 (Recorder 立即交出控制权)
        if self.recorder and self.recorder.is_recording:
            # 拿到旧句柄，Recorder 内部 self.file_handle 变 None，可以立即开始下一次记录
            csv_handle, csv_path = self.recorder.detach_current_session()
        
        # 3. 启动后台线程 (IO 耗时操作全部在此)
        if json_snapshot_data or csv_handle:
            t = threading.Thread(
                target=background_save_worker, 
                args=(self.history_filename, json_snapshot_data, csv_handle, csv_path)
            )
            t.daemon = True
            t.start()
            print(">>> 🏁 完赛! (后台正在保存数据...)")
        else:
            print(">>> 🏁 完赛! (无数据需保存)")

        return {"status": "finished", "lap_data": final_data_for_ui, "finish_timestamp": now}

    def _update_memory_history_logic(self):
        """
        同步执行所有内存数据的更新。
        确保下一圈开始时，self.best_lap 已经是最新状态。
        """
        self.total_valid_laps_count += 1
        current_lap_idx = self.total_valid_laps_count
        self.current_lap_data['lap_index'] = current_lap_idx

        stage_rolling_enabled = getattr(config, 'ENABLE_STAGE_ROLLING_WINDOW_BEST', True)
        stage_window = getattr(config, 'STAGE_ROLLING_WINDOW_SIZE', 10)
        loop_rolling_enabled = getattr(config, 'ENABLE_LOOP_ROLLING_WINDOW_BEST', True)
        loop_window = getattr(config, 'LOOP_ROLLING_WINDOW_SIZE', 20)

        if self.best_lap is None: self.init_default_best_lap()

        if self.current_lap_data['total_time'] < self.best_lap['total_time']:
            print(f"🎉 New Absolute Record! ({self.current_lap_data['formatted_total_time']})")
            self._update_best_lap_fields(self.current_lap_data)

        if loop_rolling_enabled:
            q = self.best_lap.get('rolling_queue', [])
            self.best_lap['rolling_queue'] = self._update_monotonic_queue(q, self.current_lap_data['total_time'], current_lap_idx, loop_window)
        else:
            self.best_lap['rolling_queue'] = []

        for i, curr_seg in enumerate(self.current_lap_data['segments']):
            if i >= len(self.best_lap['segments']): break
            best_seg = self.best_lap['segments'][i]
            if curr_seg['duration'] < best_seg['duration']: self._update_best_segment_fields(i, curr_seg)
            if stage_rolling_enabled:
                seg_q = best_seg.get('rolling_queue', [])
                self.best_lap['segments'][i]['rolling_queue'] = self._update_monotonic_queue(seg_q, curr_seg['duration'], current_lap_idx, stage_window)
            else: self.best_lap['segments'][i]['rolling_queue'] = []

        for i, curr_sec in enumerate(self.current_lap_data['sectors']):
            if i >= len(self.best_lap['sectors']): break
            best_sec = self.best_lap['sectors'][i]
            if curr_sec['duration'] < best_sec['duration']: self._update_best_sector_fields(i, curr_sec)
            if stage_rolling_enabled:
                sec_q = best_sec.get('rolling_queue', [])
                self.best_lap['sectors'][i]['rolling_queue'] = self._update_monotonic_queue(sec_q, curr_sec['duration'], current_lap_idx, stage_window)
            else: self.best_lap['sectors'][i]['rolling_queue'] = []

        self.history.append(self.current_lap_data)

    def abort_lap(self):
        target_file = None
        if self.recorder:
            if hasattr(self.recorder, 'current_filepath'): target_file = self.recorder.current_filepath
            
        if self.recorder: self.recorder.discard_recording() 
            
    def get_color_and_delta(self, current, best_ref, default_val, limit1, limit2):
        ref = best_ref if best_ref is not None else default_val
        delta = current - ref
        d_str = f"+{delta:.3f}" if delta > 0 else f"{delta:.3f}"
        if delta <= -limit1: return "purple", d_str
        if delta < 0: return "green", d_str
        if delta <= limit2: return "yellow", d_str
        return "red", d_str
    
    @staticmethod
    def get_status_block(color_name):
        mapping = {"purple": "🟪", "green": "🟩", "yellow": "🟨", "red": "🟥"}
        return mapping.get(color_name, "")
    
    @staticmethod
    def format_time(seconds):
        if seconds is None: seconds = 0
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        elif m > 0:
            return f"{m:02d}:{s:02d}.{ms:03d}"
        else:
            return f"{s:02d}.{ms:03d}"
    
    def stop(self):
        if self.recorder: self.recorder.discard_recording()

if __name__ == "__main__":
    pass