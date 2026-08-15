# data_save.py
import csv
import os
import datetime

# 尝试导入绘图模块，如果失败则仅记录数据不绘图
try:
    import plot_total
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False

class DataRecorder:
    def __init__(self, output_folder="record_data"):
        self.output_folder = output_folder
        self.file_handle = None
        self.csv_writer = None
        self.current_filepath = None
        self.is_recording = False
        
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def start_new_session(self, header):
        """开始新的记录"""
        # 安全检查：防止上一轮意外没关文件（虽然 detach 机制通常保证了这一点）
        if self.file_handle:
            try:
                self.file_handle.close()
            except: 
                pass

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"real_track_{timestamp}.csv"
        self.current_filepath = os.path.join(self.output_folder, filename)
        
        # buffering=1 启用行缓冲，虽然系统层仍有缓冲，但这有助于减少应用层内存占用
        self.file_handle = open(self.current_filepath, 'w', newline='', buffering=1)
        self.csv_writer = csv.writer(self.file_handle)
        self.csv_writer.writerow(header)
        self.is_recording = True
        print(f"[Record] 开始记录: {filename}")

    def log_step(self, data_row):
        """记录一步数据"""
        if self.is_recording and self.csv_writer:
            self.csv_writer.writerow(data_row)

    def detach_current_session(self):
        """
        [核心异步机制]
        剥离当前会话的控制权，将其移交给后台线程处理。
        返回 (文件句柄, 文件路径)，并将 Recorder 内部状态重置为空闲。
        这样主线程可以立刻开始下一场记录，而不需要等待文件关闭和绘图。
        """
        handle = self.file_handle
        path = self.current_filepath
        
        # 立即切断 Recorder 与该文件的联系，重置状态
        self.file_handle = None
        self.csv_writer = None
        self.current_filepath = None
        self.is_recording = False
        
        return handle, path

    def discard_recording(self):
        """
        废弃当前记录（用于无效圈）。
        直接关闭并删除文件。
        """
        if self.file_handle:
            try:
                self.file_handle.close()
            except:
                pass
            self.file_handle = None
        
        self.is_recording = False
        self.csv_writer = None

        # 物理删除文件
        if self.current_filepath and os.path.exists(self.current_filepath):
            try:
                os.remove(self.current_filepath)
                print(f"[Record] ⚠️ 记录已废弃并删除: {os.path.basename(self.current_filepath)}")
            except OSError as e:
                print(f"[Record] 删除文件失败: {e}")
        
        self.current_filepath = None