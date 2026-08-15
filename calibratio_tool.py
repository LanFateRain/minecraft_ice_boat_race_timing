# calibratio_tool.py

import cv2
import mss
import numpy as np
import time

# ================= 调试配置 =================
GAME_MONITOR_ID = 1  # 你的屏幕ID

# 初始坐标 (请根据你之前大概测量的数值填入)
# 目标：只框住数字！不要框住 'x:' 或 'm/s'
BOX_X = {'top': 160, 'left': 54, 'width': 115, 'height': 30}
BOX_Z = {'top': 160, 'left': 340, 'width': 100, 'height': 30}
BOX_SPEED = {'top': 246, 'left': 120, 'width': 98, 'height': 30}
THRESHOLD_VAL = 180
# ===========================================

def get_monitor_offset(sct, monitor_id):
    if monitor_id >= len(sct.monitors):
        raise ValueError("屏幕ID不存在")
    return sct.monitors[monitor_id]['left'], sct.monitors[monitor_id]['top']

def process_img(img, threshold):
    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    # 放大 3 倍 (对付小字体神器)
    height, width = gray.shape
    gray = cv2.resize(gray, (width * 3, height * 3), interpolation=cv2.INTER_LINEAR)
    # 二值化 (滑动条控制阈值)
    # 如果出来的字是【白底黑字】，这里用 THRESH_BINARY
    # 如果出来的字是【黑底白字】，这里用 THRESH_BINARY_INV
    # 我们的目标是让OCR看到：白底黑字 (像书本一样)
    _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY) 
    return thresh

def main():
    window_name = "Calibration" # 统一窗口名称，防止报错

    with mss.mss() as sct:
        try:
            off_x, off_y = get_monitor_offset(sct, GAME_MONITOR_ID)
        except Exception as e:
            print(f"错误: {e}")
            return

        # 定义绝对坐标函数
        def get_box(box):
            return {
                'top': int(off_y + box['top']), 
                'left': int(off_x + box['left']), 
                'width': int(box['width']), 
                'height': int(box['height'])
            }

        # 先创建窗口，再创建滑动条
        cv2.namedWindow(window_name)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
        cv2.createTrackbar("Threshold", window_name, THRESHOLD_VAL, 255, lambda x: None)

        print(">>> 正在启动校准视窗...")
        print(">>> 请去代码里修改 BOX_X, BOX_Z 的坐标，直到窗口里只显示纯数字。")
        print(">>> 拖动滑动条，让数字线条清晰且没有噪点。")
        print(">>> 按 'q' 退出")

        while True:
            # 1. 截取三个区域
            try:
                img_x = np.array(sct.grab(get_box(BOX_X)))
                img_z = np.array(sct.grab(get_box(BOX_Z)))
                img_s = np.array(sct.grab(get_box(BOX_SPEED)))
            except Exception as e:
                print(f"截屏失败: {e}")
                break

            # 2. 获取滑动条当前的阈值
            thresh_val = cv2.getTrackbarPos("Threshold", window_name)

            # 3. 处理图像
            p_x = process_img(img_x, thresh_val)
            p_z = process_img(img_z, thresh_val)
            p_s = process_img(img_s, thresh_val)

            # 4. 统一宽度以便拼接 (为了显示美观)
            max_w = max(p_x.shape[1], p_z.shape[1], p_s.shape[1])
            
            def pad_img(img, target_w):
                h, w = img.shape
                diff = target_w - w
                if diff > 0:
                    # 填充白色背景 (255)
                    return cv2.copyMakeBorder(img, 0, 0, 0, diff, cv2.BORDER_CONSTANT, value=255)
                return img

            # 垂直拼起来
            display_img = np.vstack([
                pad_img(p_x, max_w), 
                pad_img(p_z, max_w), 
                pad_img(p_s, max_w)
            ])

            cv2.imshow(window_name, display_img)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()