# ui_core.py
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QPointF, QVariantAnimation
from PyQt6.QtGui import QPainter, QColor, QFontDatabase, QFont, QFontMetrics, QPolygonF, QBrush, QPainterPath
import config

# ==========================================
# 静态资源与样式
# ==========================================

COLOR_MAP = {
    "purple": "#d66aff", "green":  "#43d335", "yellow": "#ffd700", 
    "red":    "#ff4d4d", "gray":   "#888888", "white":  "#ffffff",
}

CURRENT_FONT_FAMILY = "sans-serif"

def ui_scale(value):
    """Scale UI geometry values according to config.UI_ZOOM."""
    zoom = getattr(config, 'UI_ZOOM', 1)
    return int(round(value * zoom))

def load_custom_font():
    """加载自定义字体，被 main.py 调用"""
    global CURRENT_FONT_FAMILY
    font_file = getattr(config, 'FONT_FILE_NAME', "Formula1-Display-Regular.ttf")
    # 假设 font 文件夹在当前目录
    base_path = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_path, 'font', font_file)
    
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                CURRENT_FONT_FAMILY = families[0]
                return f"'{CURRENT_FONT_FAMILY}'"
    CURRENT_FONT_FAMILY = "Consolas" 
    return "'Consolas', 'Monospace', sans-serif"

def get_stylesheet_template():
    return """
    QWidget { background-color: transparent; }
    QLabel { 
        color: white; 
        font-weight: bold; 
        font-family: __FONT_FAMILY__;
    }
    .user-name-label {
        font-size: 22px; 
        color: #ffffff; 
        background-color: transparent; 
        padding-left: 8px;
    }
    .title-label { 
        font-size: 14px; 
        color: #cccccc; 
        background-color: transparent; 
        font-weight: normal; 
    }
    /* 内部小格子 */
    QFrame.status-block { 
        background-color: transparent; 
        border: none;
    }
    """

# ==========================================
# 基础组件 (Label, Line, Overlay)
# ==========================================

class F1Label(QWidget):
    """自定义标签，强制执行“数字等宽”渲染"""
    def __init__(self, text="--", font_size=16, align=Qt.AlignmentFlag.AlignCenter, parent=None):
        super().__init__(parent)
        self.text_content = text
        self.font_size = font_size
        self.alignment = align
        self.text_color = QColor("white")
        self.metrics = self._calculate_metrics()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _calculate_metrics(self):
        font = QFont(CURRENT_FONT_FAMILY)
        font.setPixelSize(self.font_size)
        font.setBold(True)
        fm = QFontMetrics(font)
        return {
            'digit': fm.horizontalAdvance('8'),
            'colon': fm.horizontalAdvance(':'),
            'dot':   fm.horizontalAdvance('.'),
            'sign':  fm.horizontalAdvance('+'),
            'font':  font, 'fm': fm, 'height': fm.height(),
            'ascent': fm.ascent(), 'descent': fm.descent()
        }

    def sizeHint(self):
        w = self._calculate_draw_width(self.text_content)
        return QSize(w, self.metrics['height'])

    def minimumSizeHint(self):
        return self.sizeHint()

    def set_text(self, text):
        if self.text_content != text:
            self.text_content = text
            self.updateGeometry() 
            self.update() 
            if self.parentWidget():
                self.parentWidget().update()

    def set_color(self, color_str):
        c = QColor(COLOR_MAP.get(color_str, "#ffffff"))
        if self.text_color != c:
            self.text_color = c
            self.update()

    def _calculate_draw_width(self, text):
        total_w = 0
        for char in text:
            if char.isdigit(): total_w += self.metrics['digit']
            elif char == ':': total_w += self.metrics['colon']
            elif char == '.': total_w += self.metrics['dot']
            elif char in ['+', '-']: total_w += self.metrics['sign']
            else: total_w += self.metrics['fm'].horizontalAdvance(char)
        return total_w

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.metrics['font'])
        painter.setPen(self.text_color)
        
        content_width = self._calculate_draw_width(self.text_content)
        
        if self.alignment & Qt.AlignmentFlag.AlignRight:
            x = self.width() - content_width
        elif self.alignment & Qt.AlignmentFlag.AlignLeft:
            x = 0
        else:
            x = (self.width() - content_width) / 2
            
        y = (self.height() + self.metrics['ascent'] - self.metrics['descent']) / 2
        
        current_x = x
        for char in self.text_content:
            draw_w = 0
            if char.isdigit(): draw_w = self.metrics['digit']
            elif char == ':': draw_w = self.metrics['colon']
            elif char == '.': draw_w = self.metrics['dot']
            elif char in ['+', '-']: draw_w = self.metrics['sign']
            else: draw_w = self.metrics['fm'].horizontalAdvance(char)
            
            char_real_w = self.metrics['fm'].horizontalAdvance(char)
            offset = (draw_w - char_real_w) / 2
            painter.drawText(int(current_x + offset), int(y), char)
            current_x += draw_w

class LineBar(QWidget):
    def __init__(self, height=3, color_hex="#888888", parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.current_color = QColor(color_hex)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_color_hex(self, color_hex):
        c = QColor(color_hex)
        if self.current_color != c:
            self.current_color = c
            self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.current_color)
        painter.fillRect(self.rect(), self.current_color)

class ShineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.shine_progress = -1.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(1200) 
        self.anim.setKeyValues([(0.0, 0.0), (0.25, 0.35), (0.75, 0.65), (1.0, 1.0)])
        self.anim.valueChanged.connect(self._update_shine)
        self.anim.finished.connect(self._end_shine)

    def start_shine(self):
        if self.anim.state() == QVariantAnimation.State.Running: self.anim.stop()
        self.anim.start()
    def _update_shine(self, value): self.shine_progress = value; self.update()
    def _end_shine(self): self.shine_progress = -1.0; self.update()

    def paintEvent(self, event):
        if self.shine_progress < 0: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        painter.setClipPath(path)
        
        w = self.width(); h = self.height(); slant_offset = h 
        line1_w = 30; line2_w = 240; gap = 40
        trail_length = line1_w + gap + line2_w + slant_offset
        start_x = -trail_length - 50; end_x = w + trail_length + 50
        total_distance = end_x - start_x
        current_head_x = start_x + (total_distance * self.shine_progress)
        
        shine_color = QColor(255, 255, 255, 80)
        painter.setBrush(QBrush(shine_color)); painter.setPen(Qt.PenStyle.NoPen)
        
        x1 = current_head_x
        p1 = QPolygonF([QPointF(x1, 0), QPointF(x1 + line1_w, 0), QPointF(x1 + line1_w - slant_offset, h), QPointF(x1 - slant_offset, h)])
        painter.drawPolygon(p1)
        
        x2 = x1 - gap - line2_w
        p2 = QPolygonF([QPointF(x2, 0), QPointF(x2 + line2_w, 0), QPointF(x2 + line2_w - slant_offset, h), QPointF(x2 - slant_offset, h)])
        painter.drawPolygon(p2)

class TextWidthCalculator:
    @staticmethod
    def get_width(template_text, font_size):
        dummy = F1Label(template_text, font_size)
        return dummy._calculate_draw_width(template_text) + 4 

# ==========================================
# 复合组件 (StatusBlock, SummaryHeader, Panel)
# ==========================================

class StatusBlock(QFrame):
    def __init__(self, label_text, width_config, parent=None):
        super().__init__(parent)
        self.setProperty("class", "status-block")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) 
        layout.setSpacing(ui_scale(0)) 
        layout.addStretch()
        
        self.lbl_name = QLabel(label_text)
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setStyleSheet(f"font-size: {ui_scale(16)}px; font-weight: bold; color: #888888; border: none; background: transparent; padding: 0px;")
        layout.addWidget(self.lbl_name)
        
        layout.addSpacing(ui_scale(2))
        
        self.lbl_time = F1Label("--", font_size=ui_scale(16), align=Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.set_color("gray")
        self.lbl_time.setFixedWidth(width_config['block_text_w'])
        self.lbl_time.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.lbl_time, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(ui_scale(1))
        
        self.line_bar = LineBar(height=ui_scale(3), color_hex=COLOR_MAP['gray'])
        layout.addWidget(self.line_bar)
        
    def update_status(self, duration_text, color_name="white"):
        self.lbl_time.set_text(duration_text)
        self.lbl_time.set_color(color_name)
        
        hex_color = COLOR_MAP.get(color_name, COLOR_MAP["white"])
        self.lbl_name.setStyleSheet(f"font-size: {ui_scale(16)}px; font-weight: bold; color: {hex_color}; border: none; background: transparent; padding: 0px;")
        
        bar_hex = hex_color
        if color_name == "white" or color_name == "gray":
            bar_hex = COLOR_MAP["gray"]
        self.line_bar.set_color_hex(bar_hex)
    
    def update_name(self, new_name):
        self.lbl_name.setText(new_name)

    def update_mini_mode(self, time_text, delta_text, color_name):
        # MiniSector 模式：时间在上方(Title位置)，Delta在下方(Time位置)
        self.lbl_name.setText(time_text)
        hex_color = COLOR_MAP.get(color_name, COLOR_MAP["white"])
        # 上方时间也变色
        self.lbl_name.setStyleSheet(f"font-size: {ui_scale(16)}px; font-weight: bold; color: {hex_color}; border: none; background: transparent; padding: 0px;")
        
        self.lbl_time.set_text(delta_text)
        self.lbl_time.set_color(color_name)
        
        bar_hex = hex_color
        if color_name == "white" or color_name == "gray":
            bar_hex = COLOR_MAP["gray"]
        self.line_bar.set_color_hex(bar_hex)

class SummaryHeader(QFrame):
    def __init__(self, title_text, width_config, margin_left, margin_right, parent=None):
        super().__init__(parent)
        self.setProperty("class", "status-block")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.max_delta_w = width_config.get('summary_delta_w', 60)

        self.lbl_title = QLabel(title_text, self)
        self.lbl_title.setStyleSheet(f"font-size: {ui_scale(14)}px; font-weight: normal; color: #888888; border: none; background: transparent;")
        self.lbl_title.adjustSize()

        self.lbl_time = F1Label("--", font_size=ui_scale(20), align=Qt.AlignmentFlag.AlignCenter, parent=self)
        self.lbl_time.set_color("gray")
        self.lbl_delta = F1Label("", font_size=ui_scale(14), align=Qt.AlignmentFlag.AlignRight, parent=self)

    def update_header(self, time_str, delta_str, color_name):
        self.lbl_time.set_text(time_str)
        self.lbl_delta.set_text(delta_str)
        self.lbl_time.set_color("white")
        self.lbl_delta.set_color(color_name)
        self.layout_manual()

    def reset(self):
        self.lbl_time.set_text("--")
        self.lbl_delta.set_text("")
        self.lbl_time.set_color("gray")
        self.lbl_delta.set_color("white")
        self.layout_manual()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_manual()

    def layout_manual(self):
        w = self.width()
        h = self.height()
        content_h = h 
        
        # 1. 标题 (左)
        t_w = self.lbl_title.sizeHint().width()
        t_h = self.lbl_title.sizeHint().height()
        self.lbl_title.setGeometry(self.margin_left, (content_h - t_h) // 2, t_w, t_h)
        
        # 2. 用时 (绝对居中)
        self.lbl_time.adjustSize()
        tm_w = self.lbl_time.width()
        tm_h = self.lbl_time.height()
        time_x = (w - tm_w) // 2
        time_y = (content_h - tm_h) // 2
        self.lbl_time.move(time_x, time_y)
        
        # 3. Delta (右侧 + 偏移)
        self.lbl_delta.adjustSize()
        d_w = self.lbl_delta.width()
        d_h = self.lbl_delta.height()
        extra_right_offset = 30 
        fixed_center_x = w - self.margin_right - extra_right_offset - (self.max_delta_w / 2)
        delta_x = int(fixed_center_x - (d_w / 2))
        delta_y = (content_h - d_h) // 2
        self.lbl_delta.move(delta_x, delta_y)

class TelemetryPanel(QFrame):
    def __init__(self, title, block_count, prefix="S", width_config=None, parent=None, 
                 layout_mode='FULL', use_profile_name=False, 
                 custom_right_margin=None):
        super().__init__(parent)
        self.prefix = prefix
        self.width_config = width_config 
        self.layout_mode = layout_mode
        self.block_count = block_count 
        self.title_text = title        
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        if width_config is None: width_config = {'time_large_w': 200, 'delta_large_w': 100, 'time_small_w': 100, 'delta_small_w': 60, 'block_text_w': 80}
        
        bg_color = f"rgba(0, 0, 0, {getattr(config, 'UI_BACKGROUND_ALPHA', 204)})"
        border_color = "rgba(255, 255, 255, 0.25)"
        
        self.setStyleSheet(f"TelemetryPanel {{ background-color: {bg_color}; border-radius: 8px; border: 1px solid {border_color}; }}")
        
        self.main_layout = QVBoxLayout(self)
        
        self.content_left_margin = 0
        self.content_right_margin = 0
        self.lbl_title = None
        self.lbl_record_alert = None 
        self.blocks = []
        self.summary_header = None 

        if layout_mode == 'SUMMARY':
            # [修改] Summary 模式高度调整：从 88 增加到 90，底部边距保持 6
            self.setFixedHeight(ui_scale(90))
            self.main_layout.setSpacing(ui_scale(0))
            self.main_layout.setContentsMargins(0, ui_scale(4), 0, ui_scale(6)) 
            self.content_left_margin = 15
            self.content_right_margin = 15
            
            self.summary_header = SummaryHeader(self.title_text, self.width_config, 
                                                self.content_left_margin, self.content_right_margin)
            self.summary_header.setFixedHeight(ui_scale(28))
            self.main_layout.addWidget(self.summary_header)
            
            self.blocks_layout = QHBoxLayout()
            self.blocks_layout.setSpacing(ui_scale(0))
            self.main_layout.addLayout(self.blocks_layout)
            self.rebuild_blocks(self.block_count)
            
        else:
            if layout_mode == 'COMPACT':
                self.main_layout.setSpacing(ui_scale(2))
                self.main_layout.setContentsMargins(0, ui_scale(5), 0, ui_scale(5)) 
                self.content_left_margin = ui_scale(10)
            elif layout_mode == 'NO_TITLE':
                self.main_layout.setSpacing(ui_scale(4))
                # [修改] Current Sector 底部边距改为 6
                self.main_layout.setContentsMargins(0, ui_scale(8), 0, ui_scale(6)) 
                self.content_left_margin = ui_scale(15)
            else: # FULL (Loop)
                self.main_layout.setSpacing(ui_scale(5))
                # [修改] Loop 面板底部边距改为 6
                self.main_layout.setContentsMargins(0, ui_scale(10), 0, ui_scale(6)) 
                self.content_left_margin = ui_scale(15)
                
            if custom_right_margin is not None:
                self.content_right_margin = custom_right_margin
            else:
                self.content_right_margin = self.content_left_margin

            if layout_mode != 'NO_TITLE':
                display_title = title
                title_class = "title-label"
                if use_profile_name:
                    user_name = getattr(config, 'USER_NAME', '')
                    if user_name:
                        display_title = user_name
                        title_class = "user-name-label"

                self.lbl_title = QLabel(display_title)
                self.lbl_title.setProperty("class", title_class)
                self.lbl_title.setStyleSheet(f"border: none; margin-left: {self.content_left_margin}px;")

                self.lbl_record_alert = QLabel("NEW RECORD")
                self.lbl_record_alert.setVisible(False)
                self.lbl_record_alert.setStyleSheet(f"""
                    color: #ffffff; 
                    font-weight: bold; 
                    font-size: {ui_scale(22)}px; 
                    border: none; 
                    margin-right: {self.content_left_margin}px;
                """)

            delta_font_size = ui_scale(32)
            if layout_mode == 'COMPACT':
                delta_font_size = ui_scale(20)
            
            self.lbl_delta = F1Label("", font_size=delta_font_size, align=Qt.AlignmentFlag.AlignCenter)
            target_delta_w = width_config['delta_large_w'] if layout_mode != 'COMPACT' else width_config['delta_small_w']
            self.lbl_delta.setFixedWidth(target_delta_w)

            time_font_size = ui_scale(48)
            if layout_mode == 'COMPACT':
                time_font_size = ui_scale(24)
            
            # [修改] 使用新的初始化方法
            self.lbl_main_time = F1Label("0.000", font_size=time_font_size, align=Qt.AlignmentFlag.AlignCenter)
            self.lbl_main_time.set_color("white")
            target_time_w = width_config['time_large_w'] if layout_mode != 'COMPACT' else width_config['time_small_w']
            self.lbl_main_time.setFixedWidth(target_time_w) 

            def add_with_margin(layout, widget, left_m=0, right_m=0):
                if left_m > 0: layout.addSpacing(ui_scale(left_m))
                layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
                if right_m > 0: layout.addSpacing(ui_scale(right_m))

            if layout_mode == 'COMPACT':
                h_layout = QHBoxLayout()
                h_layout.setContentsMargins(0, 0, 0, 0)
                add_with_margin(h_layout, self.lbl_title, left_m=self.content_left_margin)
                add_with_margin(h_layout, self.lbl_main_time)
                h_layout.addStretch()
                add_with_margin(h_layout, self.lbl_delta, right_m=self.content_right_margin)
                self.main_layout.addLayout(h_layout)
            elif layout_mode == 'NO_TITLE':
                h_time_row = QHBoxLayout()
                h_time_row.setContentsMargins(0, 0, 0, 0)
                add_with_margin(h_time_row, self.lbl_main_time, left_m=self.content_left_margin)
                h_time_row.addStretch() 
                add_with_margin(h_time_row, self.lbl_delta, right_m=self.content_right_margin)
                self.main_layout.addLayout(h_time_row)
            else: # FULL
                h_title_row = QHBoxLayout()
                h_title_row.setContentsMargins(0, 0, 0, 0)
                add_with_margin(h_title_row, self.lbl_title, left_m=self.content_left_margin)
                h_title_row.addStretch()
                if self.lbl_record_alert:
                    add_with_margin(h_title_row, self.lbl_record_alert, right_m=self.content_left_margin)
                self.main_layout.addLayout(h_title_row)
                
                h_time_row = QHBoxLayout()
                h_time_row.setContentsMargins(0, 0, 0, 0)
                add_with_margin(h_time_row, self.lbl_main_time, left_m=self.content_left_margin)
                h_time_row.addStretch()
                add_with_margin(h_time_row, self.lbl_delta, right_m=self.content_right_margin) 
                self.main_layout.addLayout(h_time_row)

            self.blocks_layout = QHBoxLayout()
            self.blocks_layout.setSpacing(ui_scale(0)) 
            self.blocks_layout.setContentsMargins(0, 0, 0, 0) 
            self.main_layout.addLayout(self.blocks_layout)
            
            if block_count > 0:
                self.rebuild_blocks(block_count)
            
        self.shine_overlay = ShineOverlay(self)
        self.shine_overlay.resize(self.size())
        self.shine_overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'shine_overlay'):
            self.shine_overlay.resize(self.size())
            self.shine_overlay.raise_()

    def rebuild_blocks(self, count):
        while self.blocks_layout.count():
            item = self.blocks_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
        self.blocks = []
        
        for i in range(count):
            blk = StatusBlock(f"{self.prefix}{i+1}", self.width_config)
            # Block 高度设置
            if self.layout_mode == 'SUMMARY':
                target_h = ui_scale(50)
            elif self.layout_mode == 'COMPACT':
                target_h = ui_scale(50)
            else:
                target_h = ui_scale(54)

            blk.setFixedHeight(target_h)
                
            blk.setFixedHeight(target_h)
            self.blocks.append(blk)
            self.blocks_layout.addWidget(blk)
        
        if hasattr(self, 'shine_overlay'):
            self.shine_overlay.raise_()
    
    # [新增] 专门的主计时器初始化方法
    def init_main_timer_display(self):
        """
        初始化主计时器显示：
        1. 内容重置为 0.000
        2. 颜色强制设为白色
        """
        if self.layout_mode != 'SUMMARY':
            self.lbl_main_time.set_text("0.000")
            self.lbl_main_time.set_color("white")
            
    def update_time(self, time_str):
        if self.layout_mode != 'SUMMARY':
            self.lbl_main_time.set_text(time_str)
            # [优化] 移除 set_color("white")，提高高频更新效率
            # 颜色由 init_main_timer_display 负责初始化
        
    def update_delta(self, delta_str, color_name="white"):
        if self.layout_mode != 'SUMMARY':
            self.lbl_delta.set_text(delta_str)
            self.lbl_delta.set_color(color_name)

    def update_block(self, index, time_str, color_name):
        if 0 <= index < len(self.blocks):
            self.blocks[index].update_status(time_str, color_name)
    
    def update_mini_sector(self, index, time_str, delta_str, color_name):
        if 0 <= index < len(self.blocks):
            self.blocks[index].update_mini_mode(time_str, delta_str, color_name)
    
    def update_summary_header(self, time_str, delta_str, color_name):
        if self.summary_header:
            self.summary_header.update_header(time_str, delta_str, color_name)

    def update_block_labels(self, start_number):
        if self.layout_mode != 'SUMMARY':
            for i, blk in enumerate(self.blocks):
                blk.update_name(f"{self.prefix}{start_number + i}")

    def update_summary_content(self, sector_time, sector_delta, sector_color, mini_data):
        if self.layout_mode == 'SUMMARY':
            self.update_summary_header(sector_time, sector_delta, sector_color)
            for j, (m_t, m_d, m_c) in enumerate(mini_data):
                if j < len(self.blocks):
                    self.blocks[j].update_mini_mode(m_t, m_d, m_c)

    def reset_content(self):
        # [修改] 使用专门的初始化方法，将主时间置为 0.000 (白色)
        if self.layout_mode != 'SUMMARY':
            self.init_main_timer_display()
            self.lbl_delta.set_text("")
            self.hide_new_record()

        for blk in self.blocks: 
            blk.update_status("--", "gray") 
            name_font_size = ui_scale(16)
            if self.layout_mode == 'SUMMARY':
                 blk.lbl_name.setStyleSheet("font-size: {name_font_size}px; font-weight: bold; color: #888888; border: none; background: transparent; padding: 0px;")

        if self.layout_mode == 'SUMMARY' and self.summary_header:
            self.summary_header.reset()

    def show_new_record(self, color_name):
        if self.layout_mode != 'SUMMARY' and self.lbl_record_alert:
            self.lbl_record_alert.setVisible(True)
            self.shine_overlay.start_shine()
        elif self.layout_mode == 'SUMMARY':
            self.shine_overlay.start_shine()

    def hide_new_record(self):
        if self.layout_mode != 'SUMMARY' and self.lbl_record_alert:
            self.lbl_record_alert.setVisible(False)
            
    def start_panel_shine(self):
        self.shine_overlay.start_shine()