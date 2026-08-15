# ui_main.py
import sys
import time
import math
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGraphicsOpacityEffect, QLabel
)
from PyQt6.QtCore import (
    Qt, pyqtSlot, pyqtProperty, QTimer, QPropertyAnimation, QEasingCurve, 
    QParallelAnimationGroup, QSequentialAnimationGroup, QPauseAnimation, 
    QSize, QPoint, QRect
)
from PyQt6.QtGui import (
    QPainter, QColor, QPolygon, QRegion
)

# Import Config and UI Core
import config
import ui_core

# ==========================================
# 3. Main Window Logic
# ==========================================

class AnimationState(Enum):
    RUNNING = auto()
    T1_FREEZE = auto()
    T2_EXPAND = auto()
    T3_SUMMARY = auto()
    T4_DISAPPEAR = auto()
    T5_APPEAR = auto() 

class RaceMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Race Analytics Overlay")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.local_sector_config = getattr(config, 'SECTOR_CONFIG', [5, 5, 5])

        self.calculate_layout_metrics()
        zoom = getattr(config, 'UI_ZOOM', 1)
        self.resize(
            int(self.ui_total_width * zoom),
            int(600 * zoom)
        )
        self.position_window()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.layout = QVBoxLayout(central_widget)
        self.layout.setSpacing(8) 
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # === UI Instantiation ===
        # 1. Loop Panel
        s_init = len(self.local_sector_config) if self.local_sector_config else 5
        self.panel_loop = ui_core.TelemetryPanel("LAP TIME", s_init, "S", self.width_config, 
                                                 layout_mode='FULL', use_profile_name=True, custom_right_margin=45)
        
        # 2. Current Sector Panel
        ms_init = self.local_sector_config[0] if self.local_sector_config else 5
        self.panel_current_sector = ui_core.TelemetryPanel("CURRENT SECTOR", ms_init, "MS", self.width_config, 
                                                                 layout_mode='NO_TITLE', use_profile_name=False, custom_right_margin=45)
        
        # 3. Summary Panels
        self.summary_panels = []     
        for i in range(5): 
            p = ui_core.TelemetryPanel(f"SECTOR {i+1}", s_init, "", self.width_config, 
                                       layout_mode='SUMMARY', use_profile_name=False)
            p.hide() 
            self.summary_panels.append(p)
            
        # === Layout ===
        self.layout.addWidget(self.panel_loop)
        for p in self.summary_panels:
            self.layout.addWidget(p)
        self.layout.addWidget(self.panel_current_sector)
        self.layout.addStretch()
        
        # === Effects ===
        self._install_effects(self.panel_loop)
        self._install_effects(self.panel_current_sector)
        for p in self.summary_panels:
            self._install_effects(p)

        # === 启动动效：一开始淡入显示 ===
        # 初始设为透明
        self.panel_loop.graphicsEffect().setOpacity(0.0)
        self.panel_current_sector.graphicsEffect().setOpacity(0.0)
        
        # 延迟一点启动淡入，让界面先渲染出来
        QTimer.singleShot(100, self._start_initial_fade_in)

        self.sector_history = [] 
        self.anim_state = AnimationState.RUNNING
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.process_animation_sequence)
        self.anim_ts = 0
        
        self.sector_display_freeze_until = 5 
        
        self.is_switching_sector = False 
        self.is_resetting_anim = False 
        self.pending_abort = False 

        self.pending_segments = []
        self.pending_sectors = []
        
        self.active_anim_group = None
        self._next_sector_context = {} 

        self.panel_current_sector.update_block_labels(1)

    def _install_effects(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(1.0)
        widget.setGraphicsEffect(effect)

    def _start_initial_fade_in(self):
        targets = [self.panel_loop, self.panel_current_sector]
        anim = self.create_fade_animation(targets, "appear", duration=800)
        anim.start()
        self._intro_anim = anim 

    # ==========================================
    # Animation Factory
    # ==========================================
    
    def create_opacity_anim(self, widget, duration, start_val=0.0, end_val=1.0):
        eff = widget.graphicsEffect()
        if not eff or not isinstance(eff, QGraphicsOpacityEffect):
            self._install_effects(widget)
            eff = widget.graphicsEffect()
            
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(start_val)
        anim.setEndValue(end_val)
        anim.setEasingCurve(QEasingCurve.Type.Linear)
        return anim

    def create_fade_animation(self, widgets, direction="appear", duration=500):
        group = QParallelAnimationGroup()
        start_op, end_op = (0.0, 1.0) if direction == "appear" else (1.0, 0.0)

        for widget in widgets:
            anim = self.create_opacity_anim(widget, duration, start_op, end_op)
            group.addAnimation(anim)
        return group

    # ==========================================
    # Formatting & Layout
    # ==========================================
    @staticmethod
    def format_time_strict(seconds):
        if seconds is None: seconds = 0
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h >= 10: return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        if h > 0:   return f"{h:d}:{m:02d}:{s:02d}.{ms:03d}"
        if m >= 10: return f"{m:02d}:{s:02d}.{ms:03d}"
        if m > 0:   return f"{m:d}:{s:02d}.{ms:03d}"
        if s >= 10: return f"{s:02d}.{ms:03d}"
        return f"{s:d}.{ms:03d}"

    def calculate_layout_metrics(self):
        zoom = getattr(config, 'UI_ZOOM', 1)
        tpl_time = "88:88:88.888"
        tpl_delta = "+8888.888"
        w_time_large = ui_core.TextWidthCalculator.get_width(tpl_time, int(48 * zoom))
        w_delta_large = ui_core.TextWidthCalculator.get_width(tpl_delta, int(32 * zoom))
        w_time_small = ui_core.TextWidthCalculator.get_width(tpl_time, int(24 * zoom))
        w_delta_small = ui_core.TextWidthCalculator.get_width(tpl_delta, int(20 * zoom))
        w_block_text_max = ui_core.TextWidthCalculator.get_width("88:88.888", int(16 * zoom))
        w_sum_time = ui_core.TextWidthCalculator.get_width("88:88.888", int(20 * zoom))
        w_sum_delta = ui_core.TextWidthCalculator.get_width("+8.888", int(14 * zoom))
        
        top_row_min_width = w_time_large + 20 + w_delta_large + 30
        max_blocks = 5
        if self.local_sector_config:
            max_blocks = max(len(self.local_sector_config), max(self.local_sector_config))
        block_min_width = w_block_text_max + 10 
        bottom_row_min_width = block_min_width * max_blocks
        ui_width = int(max(520, top_row_min_width, bottom_row_min_width))
        
        self.ui_total_width = int(ui_width * zoom)
        self.width_config = {
            'time_large_w': w_time_large,
            'delta_large_w': w_delta_large,
            'time_small_w': w_time_small,
            'delta_small_w': w_delta_small,
            'block_text_w': w_block_text_max, 
            'block_width': ui_width / 5,
            'summary_time_w': w_sum_time,
            'summary_delta_w': w_sum_delta
        }

    def position_window(self):
        monitor_id = getattr(config, 'UI_MONITOR_ID', 0)
        zoom = getattr(config, 'UI_ZOOM', 1)
        config_x = getattr(config, 'UI_WINDOW_X', 60)
        config_y = getattr(config, 'UI_WINDOW_Y', 200)
        pos_mode = getattr(config, 'UI_WINDOW_LOCATED_POSITION', 'left').lower()
        screens = QApplication.screens()
        target_screen = screens[monitor_id] if 0 <= monitor_id < len(screens) else screens[0]
        screen_geo = target_screen.geometry()
        final_x = screen_geo.x() + int(config_x * zoom)
        final_y = screen_geo.y() + int(config_y * zoom)
        scaled_width = self.ui_total_width * zoom
        if pos_mode == 'mid':
            final_x -= (scaled_width / 2)
        elif pos_mode == 'right':
            final_x -= scaled_width
        self.move(int(final_x), int(final_y))

    # ==========================================
    # Slot Functions
    # ==========================================
    @pyqtSlot(list)
    def init_track_ui(self, sector_structure):
        self.local_sector_config = sector_structure
        for i, p in enumerate(self.summary_panels):
            if i < len(sector_structure):
                p.rebuild_blocks(sector_structure[i])
            else:
                p.hide()
        if sector_structure:
            self.panel_current_sector.rebuild_blocks(sector_structure[0])
            self.panel_current_sector.update_block_labels(1)

    @pyqtSlot(float)
    def slot_lap_start(self, timestamp):
        if self.anim_state == AnimationState.RUNNING:
            self.restore_live_ui()

    @pyqtSlot(float, float)
    def slot_update_time(self, total_elapsed, sector_elapsed):
        if self.is_resetting_anim: return
        if self.anim_state != AnimationState.RUNNING and self.anim_state != AnimationState.T5_APPEAR: 
            return
        
        self.panel_loop.update_time(self.format_time_strict(total_elapsed))
        
        if time.time() > self.sector_display_freeze_until:
            self.panel_current_sector.update_time(self.format_time_strict(sector_elapsed))

    @pyqtSlot(dict)
    def slot_on_segment(self, seg_data):
        if self.is_resetting_anim: return

        idx = seg_data.get('ui_index', 0)
        val = self.format_time_strict(seg_data['duration'])
        col = seg_data['color']
        
        is_anim_active = (self.anim_state == AnimationState.RUNNING or self.anim_state == AnimationState.T5_APPEAR)
        
        if not is_anim_active or self.is_switching_sector:
            self.pending_segments.append( (idx, val, col) )
        else:
            self.panel_current_sector.update_block(idx, val, col)
            mini_freeze = getattr(config, 'UI_MINI_SECTOR_FREEZE_TIME', 1.0)
            self.sector_display_freeze_until = time.time() + mini_freeze

    @pyqtSlot(int, int)
    def slot_switch_sector_panel(self, count, start_label):
        pass

    @pyqtSlot(dict)
    def slot_on_sector(self, sec_data):
        if self.is_resetting_anim: return

        is_anim_active = (self.anim_state == AnimationState.RUNNING or self.anim_state == AnimationState.T5_APPEAR)
        
        if not is_anim_active:
            self.pending_sectors.append(sec_data)
            return

        idx = sec_data['index'] 
        val = self.format_time_strict(sec_data['duration'])
        col = sec_data['color']
        delta = sec_data.get('delta', '')
        
        self.panel_loop.update_block(idx, val, col)
        self.panel_current_sector.update_delta(delta, col)
        
        next_sec_idx = idx + 1
        if hasattr(self, 'local_sector_config') and next_sec_idx < len(self.local_sector_config):
            next_count = self.local_sector_config[next_sec_idx]
            passed_cps = sum(self.local_sector_config[:next_sec_idx])
            start_label = passed_cps + 1
            
            self._next_sector_context = {
                'count': next_count,
                'label': start_label,
                'valid': True
            }
        else:
            self._next_sector_context = {'valid': False}

        freeze_duration = getattr(config, 'UI_SECTOR_FREEZE_TIME', 5.0)
        self.sector_display_freeze_until = time.time() + freeze_duration + 0.5
        
        self.is_switching_sector = True 
        QTimer.singleShot(int(freeze_duration * 1000), self._anim_sector_step1_disappear)

    @pyqtSlot(str)
    def slot_lap_abort(self, reason):
        if self.anim_state in [AnimationState.T1_FREEZE, AnimationState.T2_EXPAND, AnimationState.T3_SUMMARY, AnimationState.T4_DISAPPEAR]:
            self.pending_abort = True
            return
        self._anim_reset_start()

    # ==========================================
    # Reset (Abort)
    # ==========================================
    def _anim_reset_start(self):
        if self.is_resetting_anim: return 
        if self.active_anim_group and self.active_anim_group.state() == QParallelAnimationGroup.State.Running:
            self.active_anim_group.stop()
        
        self.is_resetting_anim = True
        self.is_switching_sector = False
        self.pending_segments.clear()
        self.pending_sectors.clear()

        group = self.create_fade_animation([self.panel_current_sector, self.panel_loop], "disappear", 500)
        group.finished.connect(self._anim_reset_step2_do_reset)
        group.start()
        self.active_anim_group = group

    def _anim_reset_step2_do_reset(self):
        self.restore_live_ui_anim() 
        self.is_resetting_anim = True 
        
        self.panel_loop.reset_content()
        self.panel_current_sector.reset_content()
        
        if self.local_sector_config:
            self.panel_current_sector.rebuild_blocks(self.local_sector_config[0])
            self.panel_current_sector.update_block_labels(1)
            
        group = self.create_fade_animation([self.panel_current_sector, self.panel_loop], "appear", 500)
        group.finished.connect(self._anim_reset_finish)
        group.start()
        self.active_anim_group = group

    def _anim_reset_finish(self):
        self.is_resetting_anim = False
        self.pending_abort = False
        self.sector_display_freeze_until = 0 

    # ==========================================
    # Sector Switch
    # ==========================================
    def _anim_sector_step1_disappear(self):
        if self.is_resetting_anim: return 
        if self.anim_state != AnimationState.RUNNING and self.anim_state != AnimationState.T5_APPEAR:
            return

        group = self.create_fade_animation([self.panel_current_sector], "disappear", 500)
        group.finished.connect(self._anim_sector_step2_reset_and_appear)
        group.start()
        self.active_anim_group = group 

    def _anim_sector_step2_reset_and_appear(self):
        if self.is_resetting_anim: return

        ctx = self._next_sector_context
        if ctx.get('valid', False):
            self.panel_current_sector.reset_content()
            self.panel_current_sector.rebuild_blocks(ctx['count'])
            self.panel_current_sector.update_block_labels(ctx['label'])
            self.panel_current_sector.init_main_timer_display()
        
        for p_idx, p_val, p_col in self.pending_segments:
            self.panel_current_sector.update_block(p_idx, p_val, p_col)
        self.pending_segments.clear()

        self.is_switching_sector = False 
        self.sector_display_freeze_until = 0 

        group = self.create_fade_animation([self.panel_current_sector], "appear", 500)
        group.finished.connect(self._anim_sector_finish) 
        group.start()
        self.active_anim_group = group

    def _anim_sector_finish(self):
        pass

    @pyqtSlot(dict)
    def slot_lap_finish(self, lap_data):
        if self.active_anim_group and self.active_anim_group.state() == QParallelAnimationGroup.State.Running:
            self.active_anim_group.stop()
        
        self.is_switching_sector = False
        self.is_resetting_anim = False
        self.pending_abort = False 

        self.sector_history = []
        sectors = lap_data.get('sectors', [])
        segments = lap_data.get('segments', [])
        seg_cursor = 0
        for i, sec in enumerate(sectors):
            sec_val = self.format_time_strict(sec['duration'])
            sec_col = sec['color']
            sec_delta = sec.get('delta', '') 
            count = self.local_sector_config[i] if i < len(self.local_sector_config) else 5
            mini_list = []
            for _ in range(count):
                if seg_cursor < len(segments):
                    s = segments[seg_cursor]
                    s_val = self.format_time_strict(s['duration'])
                    mini_list.append( (s_val, s['delta'], s['color']) )
                    seg_cursor += 1
            self.sector_history.append( (sec_val, sec_delta, sec_col, mini_list) )

        total_time_str = self.format_time_strict(lap_data['total_time'])
        self.panel_loop.update_time(total_time_str)
        self.panel_loop.update_delta(lap_data['delta'], lap_data['color'])
        if lap_data['color'] in ['purple', 'green']:
            self.panel_loop.show_new_record(lap_data['color'])
            
        self.anim_state = AnimationState.T1_FREEZE
        self.anim_ts = time.time()
        self.anim_timer.start(50)

    # ==========================================
    # Lap Finish Sequence
    # ==========================================
    def process_animation_sequence(self):
        now = time.time()
        elapsed = now - self.anim_ts
        
        T1_FREEZE = getattr(config, 'UI_FINISH_FREEZE_TIME', 1.5)
        T2_EXPAND = 1.0 
        T3_SUMMARY = getattr(config, 'UI_SUMMARY_DISPLAY_TIME', 3.0)
        T4_DISAPPEAR_DURATION = 0.5 
        T5_APPEAR_DURATION = 0.5
        
        if self.anim_state == AnimationState.T1_FREEZE:
            if elapsed >= T1_FREEZE:
                self.anim_state = AnimationState.T2_EXPAND
                self.anim_ts = now
                self.perform_expand_sequence()
        elif self.anim_state == AnimationState.T2_EXPAND:
            if elapsed >= T2_EXPAND:
                self.anim_state = AnimationState.T3_SUMMARY
                self.anim_ts = now
        elif self.anim_state == AnimationState.T3_SUMMARY:
            if elapsed >= T3_SUMMARY:
                self.anim_state = AnimationState.T4_DISAPPEAR
                self.anim_ts = now
                self.perform_disappear_sequence()
        elif self.anim_state == AnimationState.T4_DISAPPEAR:
            pass 
        elif self.anim_state == AnimationState.T5_APPEAR:
            if elapsed >= T5_APPEAR_DURATION:
                self.restore_live_ui_anim()

    def perform_expand_sequence(self):
        group1 = self.create_fade_animation([self.panel_current_sector], "disappear", 500)
        group1.start()
        self.active_anim_group = group1 
        QTimer.singleShot(500, self._step2_show_summary)

    def _step2_show_summary(self):
        active_summaries = []
        for i, p in enumerate(self.summary_panels):
            if i < len(self.sector_history):
                val, delta, col, mini_data = self.sector_history[i]
                p.update_summary_content(val, delta, col, mini_data)
                p.show()
                if not p.graphicsEffect(): self._install_effects(p)
                p.graphicsEffect().setOpacity(0.0)
                active_summaries.append(p)
            else:
                p.hide()
        
        group2 = self.create_fade_animation(active_summaries, "appear", 500)
        group2.start()
        self.active_anim_group = group2

    def perform_disappear_sequence(self):
        active_panels = [p for p in self.summary_panels if not p.isHidden()]
        targets = [self.panel_loop] + active_panels
        group1 = self.create_fade_animation(targets, "disappear", 500)
        group1.start()
        self.active_anim_group = group1
        QTimer.singleShot(500, self._step2_restore_and_appear)

    def _step2_restore_and_appear(self):
        for i, p in enumerate(self.summary_panels):
            p.hide()
            p.reset_content()
            if p.graphicsEffect(): p.graphicsEffect().setOpacity(1.0)
            
        if self.pending_abort:
            self.panel_current_sector.reset_content()
            self.panel_loop.reset_content()
            if self.local_sector_config:
                self.panel_current_sector.rebuild_blocks(self.local_sector_config[0])
                self.panel_current_sector.update_block_labels(1)
            self.pending_sectors.clear()
            self.pending_segments.clear()
            self.pending_abort = False
        else:
            if self.local_sector_config:
                self.panel_current_sector.rebuild_blocks(self.local_sector_config[0])
                self.panel_current_sector.update_block_labels(1)
            self.panel_current_sector.reset_content()
            self.panel_loop.reset_content()
            self.panel_loop.hide_new_record()
            self.panel_loop.update_delta("", "white")
            self.panel_current_sector.init_main_timer_display()
            self.restore_live_ui_data_only()
        
        self.panel_current_sector.show()
        if self.panel_current_sector.graphicsEffect():
            self.panel_current_sector.graphicsEffect().setOpacity(0.0)
        
        if self.panel_loop.graphicsEffect():
            self.panel_loop.graphicsEffect().setOpacity(0.0)
        
        self.anim_state = AnimationState.T5_APPEAR
        self.anim_ts = time.time()
        
        targets = [self.panel_loop, self.panel_current_sector]
        group2 = self.create_fade_animation(targets, "appear", 500)
        group2.start()
        self.active_anim_group = group2

    def restore_live_ui_anim(self):
        self.anim_state = AnimationState.RUNNING
        self.anim_timer.stop()
        self.sector_display_freeze_until = 0 
        self.is_switching_sector = False
        self.is_resetting_anim = False
        
        if self.panel_loop.graphicsEffect():
            self.panel_loop.graphicsEffect().setOpacity(1.0)
        if self.panel_current_sector.graphicsEffect():
            self.panel_current_sector.graphicsEffect().setOpacity(1.0)

    def restore_live_ui_data_only(self):
        for sec_data in self.pending_sectors:
            idx = sec_data['index'] 
            val = self.format_time_strict(sec_data['duration'])
            col = sec_data['color']
            delta = sec_data.get('delta', '')
            self.panel_loop.update_block(idx, val, col)
            self.panel_current_sector.update_delta(delta, col)
            
            next_sec_idx = idx + 1
            if hasattr(self, 'local_sector_config') and next_sec_idx < len(self.local_sector_config):
                next_count = self.local_sector_config[next_sec_idx]
                passed_cps = sum(self.local_sector_config[:next_sec_idx])
                start_label = passed_cps + 1
                self.panel_current_sector.reset_content()
                self.panel_current_sector.rebuild_blocks(next_count)
                self.panel_current_sector.update_block_labels(start_label)
                self.panel_current_sector.init_main_timer_display()
        self.pending_sectors.clear()

        for p_idx, p_val, p_col in self.pending_segments:
            self.panel_current_sector.update_block(p_idx, p_val, p_col)
        self.pending_segments.clear()
        
    def restore_live_ui(self):
        self.restore_live_ui_data_only()
        self.restore_live_ui_anim()
        for p in self.summary_panels: p.hide()
        self.panel_current_sector.show()

def init_gui():
    app = QApplication(sys.argv)
    font_family = ui_core.load_custom_font()
    sheet = ui_core.get_stylesheet_template().replace("__FONT_FAMILY__", f"{font_family}, 'Consolas', 'Monospace', sans-serif")
    app.setStyleSheet(sheet)
    window = RaceMainWindow()
    if getattr(config, 'ENABLE_UI', True):
        window.show()
    return app, window

if __name__ == "__main__":
    app, win = init_gui()
    sys.exit(app.exec())