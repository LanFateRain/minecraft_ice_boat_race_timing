# main.py
import sys
import time
import traceback
import signal # 用于处理 Ctrl+C
import config

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer

# 导入业务模块
from race_logic import RaceLogic
from race_controller import RaceController
from ocr_engine import DigitOCR

# ==========================================
# 信号发射器 (保持不变)
# ==========================================
class SignalingSink(QObject):
    sig_init_track = pyqtSignal(list)
    sig_lap_start = pyqtSignal(float)
    sig_update_time = pyqtSignal(float, float) # total, sector
    sig_segment = pyqtSignal(dict)
    sig_sector = pyqtSignal(dict)
    sig_lap_finish = pyqtSignal(dict)
    sig_lap_abort = pyqtSignal(str)
    sig_switch_sector = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.current_sector_ms_count = 0 

    def on_lap_start(self, timestamp):
        self.current_sector_ms_count = 0
        self.sig_lap_start.emit(timestamp)

    def update_realtime_time(self, lap_elapsed, sector_elapsed):
        self.sig_update_time.emit(lap_elapsed, sector_elapsed)

    def on_segment(self, segment_data):
        segment_data['ui_index'] = self.current_sector_ms_count
        self.current_sector_ms_count += 1
        self.sig_segment.emit(segment_data)

    def on_sector(self, sector_data):
        self.current_sector_ms_count = 0 
        self.sig_sector.emit(sector_data)

    def on_lap_finish(self, lap_data):
        self.sig_lap_finish.emit(lap_data)

    def on_lap_abort(self, reason):
        self.current_sector_ms_count = 0
        self.sig_lap_abort.emit(reason)
        
    def switch_sector_panel(self, count, label):
        self.sig_switch_sector.emit(count, label)

# ==========================================
# 游戏逻辑线程
# ==========================================
class GameThread(QThread):
    def __init__(self, sink):
        super().__init__()
        self.sink = sink
        self.running = True
        self.race_logic_instance = None # [新增] 持有引用，方便查看状态

    def run(self):
        print(">>> [Core] 逻辑线程启动")
        
        ocr = DigitOCR(training_mode=False)
        # 将实例赋值给 self，确保生命周期可控
        self.race_logic_instance = RaceLogic(test_mode=False)
        controller = RaceController(self.race_logic_instance, ui_sink=self.sink)
        
        # 赛道结构推导
        sector_structure = []
        if hasattr(config, 'SECTOR_CONFIG'):
            sector_structure = config.SECTOR_CONFIG
            self.sink.sig_init_track.emit(sector_structure)

        loop_interval = 1.0 / config.LIMIT_FPS
        
        try:
            while self.running:
                t0 = time.time()

                x = ocr.safe_float(ocr.read_region(0))
                z = ocr.safe_float(ocr.read_region(1))
                s = ocr.safe_float(ocr.read_region(2))

                controller.step(x, z, s)
                
                dt = time.time() - t0
                if dt < loop_interval:
                    time.sleep(loop_interval - dt)

        except Exception:
            traceback.print_exc()
        finally:
            print(">>> [Core] 正在执行停止清理...")
            # 关键：在这里调用 stop，会触发 recorder.discard_recording()
            if self.race_logic_instance:
                self.race_logic_instance.stop()
            print(">>> [Core] 逻辑线程已安全停止 (CSV清理完成)")

    def stop(self):
        self.running = False
        # 不在这里调用 wait()，防止在信号处理中死锁，由外部调用 wait

# ==========================================
# 主入口 (大幅修改以支持 Ctrl+C)
# ==========================================
def main():
    print("===========================")
    print("      赛车计时系统启动      ")
    print("===========================")

    # 1. 即使不启用 UI，也建议创建一个 QCoreApplication 以保持事件循环一致性
    # 但这里我们主要处理 config.ENABLE_UI = True 的情况
    app = None
    window = None
    
    if config.ENABLE_UI:
        import ui_main
        app, window = ui_main.init_gui()
    else:
        from PyQt6.QtCore import QCoreApplication
        app = QCoreApplication(sys.argv)

    # 2. 设置信号连接
    sink = SignalingSink()
    if config.ENABLE_UI and window:
        sink.sig_init_track.connect(window.init_track_ui)
        sink.sig_lap_start.connect(window.slot_lap_start)
        sink.sig_update_time.connect(window.slot_update_time)
        sink.sig_segment.connect(window.slot_on_segment)
        sink.sig_sector.connect(window.slot_on_sector)
        sink.sig_lap_finish.connect(window.slot_lap_finish)
        sink.sig_lap_abort.connect(window.slot_lap_abort)
        sink.sig_switch_sector.connect(window.slot_switch_sector_panel)
    
    # 3. 启动逻辑线程
    game_thread = GameThread(sink)
    game_thread.start()

    # ==========================================
    # [新增] 信号处理逻辑
    # ==========================================
    def sigint_handler(sig, frame):
        print("\n>>> 🛑 捕获 Ctrl+C，正在安全退出...")
        
        # 1. 停止逻辑线程 (打破 while 循环)
        game_thread.stop()
        
        # 2. 等待线程清理完成 (执行 finally 块中的 remove csv)
        # wait() 会阻塞直到线程结束
        print(">>> [System] 等待后台线程清理数据...")
        game_thread.wait()
        
        # 3. 退出 Qt 应用
        if app:
            app.quit()

    # 注册 Ctrl+C 信号
    signal.signal(signal.SIGINT, sigint_handler)

    # [关键技巧] 使用 QTimer 定期唤醒 Python 解释器
    # 否则 app.exec() 会阻塞，导致 Python 无法处理 SIGINT
    timer = QTimer()
    timer.start(500) # 每 500ms 唤醒一次
    timer.timeout.connect(lambda: None) # 什么都不做，只是为了让解释器运行

    # 4. 进入事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()