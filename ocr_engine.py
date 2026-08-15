# ocr_engine.py
import cv2
import mss
import numpy as np
import os
import hashlib
import pickle
import config  # 导入配置

class DigitOCR:
    def __init__(self, training_mode=False, templates_file="font_templates.pkl"):
        """
        初始化 OCR 引擎
        :param training_mode: bool, True=遇到新字符弹出窗口学习并保存; False=只读模式,遇到未知字符返回'?'
        :param templates_file: str, 模板文件路径
        """
        self.sct = mss.mss()
        self.monitor_offset = self.sct.monitors[config.GAME_MONITOR_ID]
        self.regions = [
            self._to_abs(config.BOX_X),
            self._to_abs(config.BOX_Z),
            self._to_abs(config.BOX_SPEED)
        ]
        self.templates_file = templates_file
        self.templates = {}
        self.training_mode = training_mode  # <--- 使用传入的参数，默认为 False
        
        self.load_templates()
        
        if self.training_mode:
            print("⚠️ [OCR] 警告: 当前为训练模式，新字符将会写入模板文件！")
        else:
            print("[OCR] 当前为只读竞赛模式")

    def _to_abs(self, region):
        return {
            'top': int(self.monitor_offset['top'] + region['top']),
            'left': int(self.monitor_offset['left'] + region['left']),
            'width': int(region['width']),
            'height': int(region['height'])
        }

    def load_templates(self):
        if os.path.exists(self.templates_file):
            with open(self.templates_file, "rb") as f:
                self.templates = pickle.load(f)
            print(f"[OCR] 已加载 {len(self.templates)} 个字符模板")
        else:
            print("[OCR] 未找到模板文件")

    def save_templates(self):
        with open(self.templates_file, "wb") as f:
            pickle.dump(self.templates, f)
        print(f"[OCR] 模板库已保存，当前共 {len(self.templates)} 个字符")

    def get_image_hash(self, img_roi):
        h, w = img_roi.shape[:2]
        shape_tag = 'W' if w > h * 1.2 else 'S'
        resized = cv2.resize(img_roi, (20, 30), interpolation=cv2.INTER_NEAREST)
        img_hash = hashlib.md5(resized.tobytes()).hexdigest()
        return f"{shape_tag}_{img_hash}"

    def identify_char(self, char_img):
        h_key = self.get_image_hash(char_img)
        
        # 1. 尝试直接匹配
        if h_key in self.templates: 
            return self.templates[h_key]
        
        # 2. 如果不是训练模式，直接放弃，不阻塞
        if not self.training_mode:
            return "?"
        
        # 3. 训练模式逻辑：弹出窗口人工确认
        bordered = cv2.copyMakeBorder(char_img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=0)
        display_img = cv2.resize(bordered, (200, 200), interpolation=cv2.INTER_NEAREST)
        h, w = char_img.shape[:2]
        cv2.putText(display_img, f"Raw: {w}x{h}", (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150), 2)
        
        cv2.imshow("OCR Trainer", display_img)
        cv2.moveWindow("OCR Trainer", 600, 400)
        
        print(f"\n>>> [新字符] 尺寸: {w}x{h} | 请输入字符 (点=., 负号=-, 回车跳过): ")
        while True:
            key = cv2.waitKey(0)
            if key != -1: break
        cv2.destroyWindow("OCR Trainer")
        
        # 处理按键
        if key in [13, 32]: # Enter/Space 跳过
            self.templates[h_key] = "" # 标记为空，防止重复弹窗
            return ""
        
        try:
            char_input = chr(key & 0xFF)
            print(f">>> 学习: [{char_input}]")
            self.templates[h_key] = char_input
            self.save_templates() # 立即保存
            return char_input
        except:
            return ""

    def read_region(self, region_idx):
        """读取指定区域的数值字符串 (idx: 0=X, 1=Z, 2=Speed)"""
        img = np.array(self.sct.grab(self.regions[region_idx]))
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        _, thresh = cv2.threshold(gray, config.THRESHOLD_VAL, 255, cv2.THRESH_BINARY)
        
        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts: return ""
        
        cnts = sorted(cnts, key=lambda c: cv2.boundingRect(c)[0])
        res = ""
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w * h < 2: continue
            roi = thresh[y:y+h, x:x+w]
            res += self.identify_char(roi)
        return res

    def safe_float(self, raw_str):
        if not raw_str: return 0.0
        clean = "".join([c for c in raw_str if c in "0123456789-."])
        try: return float(clean)
        except: return 0.0

# === 独立测试块 ===
if __name__ == "__main__":
    print("--- 正在运行 OCR 训练/调试模式 ---")
    
    # 显式开启训练模式：允许弹出窗口并写入文件
    ocr = DigitOCR(training_mode=True) 
    
    import time
    try:
        while True:
            t0 = time.time()
            # 读取所有数据
            raw_x = ocr.read_region(0)
            raw_z = ocr.read_region(1)
            raw_s = ocr.read_region(2)
            
            # 数值转换
            val_x = ocr.safe_float(raw_x)
            val_z = ocr.safe_float(raw_z)
            val_s = ocr.safe_float(raw_s)
            
            fps = 1/(time.time()-t0)
            print(f"\rFPS: {fps:.1f} | X: {val_x} | Z: {val_z} | S: {val_s} (Raw: {raw_x} {raw_z} {raw_s})", end="")
            
            # 在独立运行时，稍微加一点延时降低 CPU 占用
            # cv2.waitKey(1) 
            
    except KeyboardInterrupt:
        print("\n测试结束")