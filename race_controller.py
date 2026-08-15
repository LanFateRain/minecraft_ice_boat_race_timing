# race_controller.py
import time
import sys
import config
from geometry_utils import point_to_line_segment_distance

class RaceController:
    STATE_IDLE = 0
    STATE_READY = 1
    STATE_RACING = 2

    def __init__(self, race_logic, ui_sink=None):
        self.race = race_logic
        self.ui = ui_sink
        self.current_state = self.STATE_IDLE
        self.has_left_start_zone = False
        self.START_GRACE_PERIOD = 0.5
        
        # [新增] 强制离开起点区域标志
        # 仅当【有效完赛】且【单圈模式】时置为 True
        self.needs_exit_start_zone = False 
        
        self._init_start_direction()

    def _init_start_direction(self):
        try:
            p1, p2 = config.START_LINE
            self.p1 = p1
            self.p2 = p2
            self.v_line_x = p2[0] - p1[0]
            self.v_line_z = p2[1] - p1[1]
            cx = (p1[0] + p2[0]) / 2
            cz = (p1[1] + p2[1]) / 2
            dir_cfg = getattr(config, 'START_DIRECTION', '+z').strip().lower()
            rx, rz = cx, cz
            if dir_cfg == '+x': rx += 1.0
            elif dir_cfg == '-x': rx -= 1.0
            elif dir_cfg == '+z': rz += 1.0
            elif dir_cfg == '-z': rz -= 1.0

            def cross(tx, tz):
                return self.v_line_x * (tz - p1[1]) - self.v_line_z * (tx - p1[0])
            self.target_sign = 1 if cross(rx, rz) > 0 else -1
        except Exception as e:
            print(f">>> ⚠️ 起点方向初始化失败: {e}")
            self.target_sign = 0

    def _check_is_forward(self, x, z):
        if not getattr(config, 'ENABLE_START_DIRECTION_CHECK', True):
            return True
        if self.target_sign == 0:
            return True
        cp = self.v_line_x * (z - self.p1[1]) - self.v_line_z * (x - self.p1[0])
        return (1 if cp > 0 else -1) == self.target_sign

    def step(self, x, z, speed):
        curr_pos = (x, z)
        
        # 计算距离
        d_start = point_to_line_segment_distance(curr_pos, config.START_LINE)

        # [逻辑修正] 检查冷却状态
        # 只有在 needs_exit_start_zone 为 True 时才阻塞
        if self.needs_exit_start_zone:
            if d_start > config.TRIGGER_DIST:
                self.needs_exit_start_zone = False
                print(">>> [Reset] 已离开触发区，系统就绪")
            else:
                sys.stdout.write(f"\r[Finish] 请离开起点区域重置... {d_start:.1f}m   ")
                sys.stdout.flush()
                return

        # [状态机逻辑]
        if self.current_state == self.STATE_IDLE:
            if d_start <= config.TRIGGER_DIST:
                self.current_state = self.STATE_READY
                print(f"\n>>> [READY] 车辆已就位 ({d_start:.2f}m)")
            else:
                # 只有在距离较近时才打印日志，避免刷屏
                if d_start < 20.0:
                    sys.stdout.write(f"\r[Wait] 回到起点... {d_start:.1f}m   ")
                    sys.stdout.flush()

        elif self.current_state == self.STATE_READY:
            # 只要离开触发区，且方向正确，就开始
            if d_start > config.TRIGGER_DIST:
                if self._check_is_forward(x, z):
                    print("\n>>> 🟢 [GO!] 计时开始")
                    self.race.start_new_lap()
                    if self.ui: self.ui.on_lap_start(self.race.current_lap_start_time)
                    self.current_state = self.STATE_RACING
                    self.has_left_start_zone = False
                else:
                    print("\n>>> [取消] 反向出发 / 离开方向错误")
                    self.current_state = self.STATE_IDLE
            else:
                sys.stdout.write(f"\r[READY] 等待出发... {d_start:.2f}m   ")
                sys.stdout.flush()

        elif self.current_state == self.STATE_RACING:
            self.race.update_continuous_data(x, z, speed)
            lap_elapsed = time.time() - self.race.current_lap_start_time
            sector_elapsed = time.time() - self.race.current_sector_start_time

            if self.ui and hasattr(self.ui, 'update_realtime_time'):
                self.ui.update_realtime_time(lap_elapsed, sector_elapsed)

            if d_start > config.TRIGGER_DIST:
                self.has_left_start_zone = True

            # 防抖动：刚出发或回退导致误判完赛
            if lap_elapsed > self.START_GRACE_PERIOD and d_start < config.TRIGGER_DIST:
                idx = self.race.next_target_index
                final_idx = len(self.race.checkpoints) - 1
                is_final_sprint = (idx == final_idx)
                
                if not is_final_sprint:
                    # 检查是否反向通过起点（回退）
                    at_forward = self._check_is_forward(x, z)
                    back_behind = not at_forward
                    # 或者虽然是正向，但是是从远处开回来的（绕圈回来但没过Checkpoint）
                    returned_front = at_forward and self.has_left_start_zone
                    
                    if back_behind or returned_front:
                        print("\n>>> [无效重置] 错误返回起点")
                        self.race.abort_lap()
                        if self.ui: self.ui.on_lap_abort("wrong_direction")
                        
                        # [逻辑优化] 错误返回起点，通常意味着车手在调整位置
                        # 我们直接转入 READY，允许他调整好后再次出发
                        self.current_state = self.STATE_READY
                        self.needs_exit_start_zone = False 
                        return

            # 检查 Checkpoint / 完赛
            if self.race.check_entry(x, z):
                result = self.race.process_hit()
                
                if 'segment' in result and self.ui:
                    self.ui.on_segment(result['segment'])
                
                if 'sector' in result and result['sector'] and self.ui:
                    self.ui.on_sector(result['sector'])
                    
                    if result.get('status') == 'running':
                        if hasattr(config, 'SECTOR_CONFIG'):
                            next_idx = result['sector']['index'] + 1
                            if next_idx < len(config.SECTOR_CONFIG):
                                count = config.SECTOR_CONFIG[next_idx]
                                passed = sum(config.SECTOR_CONFIG[:next_idx])
                                start_label = passed + 1
                                if hasattr(self.ui, 'switch_sector_panel'):
                                    self.ui.switch_sector_panel(count, start_label)

                status = result.get('status')
                if status == 'finished':
                    if self.ui: self.ui.on_lap_finish(result['lap_data'])
                    print(f">>> 🏁 完赛 {result['lap_data']['formatted_total_time']}")
                    
                    if config.CONTINUOUS_LAPPING:
                        # 连续圈：立即开始下一圈
                        self.race.start_new_lap(
                            explicit_start_time=result.get('finish_timestamp', time.time()),
                            last_pos_snapshot=(x, z, speed)
                        )
                        self.has_left_start_zone = False
                    else:
                        # 单圈模式：结束，必须离开区域
                        self.current_state = self.STATE_IDLE
                        self.needs_exit_start_zone = True 
                        
                elif status in ('invalid_missed', 'invalid_short'):
                    if self.ui: self.ui.on_lap_abort(status)
                    print(f">>> ⚠️ 成绩无效 ({status})")
                    
                    # [逻辑修正] 无效圈处理
                    # 不再强制要求离开区域。
                    # 如果车还在起点附近 (TRIGGER_DIST 内)，直接允许 READY，方便重试。
                    # 如果车在远处，转 IDLE，等他开回来。
                    
                    if d_start <= config.TRIGGER_DIST:
                        self.current_state = self.STATE_READY
                        print(">>> [Retry] 仍在起点区域，立即转为 READY")
                    else:
                        self.current_state = self.STATE_IDLE
                        print(">>> [Retry] 已重置，请返回起点")
                    
                    self.needs_exit_start_zone = False