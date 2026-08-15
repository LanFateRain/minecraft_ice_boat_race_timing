# config.py
import csv
import os

# 用户名 why_114514 Eyjafialla1018 Saliyu Lankis_OC
USER_NAME = "Lankis_OC"

# ==============================
# 历史记录与多用户存档配置
# ==============================

# 是否开启历史记录保存功能
# True: 每次完赛都会更新 json 文件，并更新“当前最佳”和“滑动窗口”
# False: 只读模式。不写入 json，内存中也不更新历史。
#        每一圈的刷紫/刷绿对比基准，始终固定为程序启动时加载的那份 json 数据。
ENABLE_HISTORY_SAVE = True

# 历史记录文件后缀名 (用于区分不同用户或场景)
# 例如: "" -> race_history.json
# 例如: "UserA" -> race_history_UserA.json
# 例如: "Practice" -> race_history_Practice.json
HISTORY_FILE_SUFFIX = "Lankis_OC"

# ==============================
# 显示器配置
# ==============================

# [OCR 采集专用] 游戏所在的显示器 ID
# mss库通常将"全屏组合"视为0，因此主显示器通常是 1
GAME_MONITOR_ID = 1

# [UI 显示专用] 窗口要放置的显示器 ID
# PyQt库不包含"全屏组合"，因此主显示器通常是 0
UI_MONITOR_ID = 0

# === OCR 和 FPS 配置 ===
# 第一次使用请至calibration.py进行校准，以确定BOX_X, BOX_Z, BOX_SPEED的值
# 校准完毕后记得运行ocr_engine.py进行字符训练
BOX_X = {'top': 160, 'left': 54, 'width': 115, 'height': 30}
BOX_Z = {'top': 160, 'left': 340, 'width': 100, 'height': 30}
BOX_SPEED = {'top': 246, 'left': 120, 'width': 98, 'height': 30}
THRESHOLD_VAL = 180
LIMIT_FPS = 30

# 坐标范围限制，请确定赛道的x与z最大可到达值，并放出一点余量，进行限制，避免误识别的异常坐标点污染数据
# 限制增添未完成，csv中有异常点，绘图中没有
X_LIMIT = (31700, 32900)
Z_LIMIT = (7000, 8400)

# ==============================
# 计时逻辑配置
# ==============================

# 连跑模式开关
# True  = 飞驰圈模式：过线后自动开始下一圈计时，无需停车
# False = 停站模式：过线后必须重新回到起点线，再次出发才开始计时
CONTINUOUS_LAPPING = False

# 小阶段与大阶段是否开启“近期最佳”滑动窗口模式
# True: 刷紫/刷绿的基准基于最近 N 圈的最佳成绩 (动态调整难度)
# False: 刷紫/刷绿的基准基于历史绝对最快成绩 (难度只会越来越高)
ENABLE_STAGE_ROLLING_WINDOW_BEST = False

# 小阶段与大阶段滑动窗口的大小 (即“最近 N 轮”)
# 仅在 ENABLE_STAGE_ROLLING_WINDOW_BEST = True 时生效
STAGE_ROLLING_WINDOW_SIZE = 10

# 总圈时间是否开启“近期最佳”滑动窗口模式
# True: 刷紫/刷绿的基准基于最近 N 圈的最佳成绩 (动态调整难度)
# False: 刷紫/刷绿的基准基于历史绝对最快成绩 (难度只会越来越高)
ENABLE_LOOP_ROLLING_WINDOW_BEST = False 

# 总圈时间滑动窗口的大小 (即“最近 N 轮”)
# 仅在 ENABLE_LOOP_ROLLING_WINDOW_BEST = True 时生效
LOOP_ROLLING_WINDOW_SIZE = 20

# ==============================
# UI相关配置
# ==============================

# 是否启动图形化界面
# True: 启动 PyQt6 UI，通过多线程运行游戏逻辑
# False: 纯控制台模式 (Headless)，占用资源更少
ENABLE_UI = True

# UI 窗口定位模式，可选："left", "mid", "right"。逻辑分别为，定位ui的左上角、中间上边的点、右上角。
UI_WINDOW_LOCATED_POSITION = "mid"


# UI 窗口缩放比例 (1 = 原始大小, 2 = 放大两倍, 0.5 = 缩小一半)
# 有bug，以下建议为mid模式测试所得
# 目前建议4k屏幕windows显示比例200%使用UI_ZOOM = 0.7，UI_WINDOW_X = 1250
# 2k与1k屏幕请调整windows显示比例为100%，使用mid模式，UI_ZOOM改为1
# 2k屏幕UI_WINDOW_X改为1280，1k屏幕UI_WINDOW_X改为960。
# UI_WINDOW_Y 根据需求自行调整
# 其他类型屏幕/其他类型显示比例/其他位置显示需求请自行尝试参数组合qwq
UI_ZOOM = 1

# UI 窗口在定位模式下的坐标 (像素)
UI_WINDOW_X = 1280
UI_WINDOW_Y = 50

# UI 背景的不透明度 (Alpha值)
# 范围: 0 (全透明) ~ 255 (全黑)
UI_BACKGROUND_ALPHA = 120

# UI字体文件名，必须存放在主目录下的 font 文件夹中
FONT_FILE_NAME = "Formula1-Display-Regular.ttf"

# 如果字体加载失败，回退使用的字体
FALLBACK_FONT_FAMILY = "'Consolas', 'Monospace', sans-serif"

# UI 动画与冻结时间配置 (单位: 秒)
UI_MINI_SECTOR_FREEZE_TIME = 0.0   # Mini-Sector (小分段) 更新时，当前分段面板主时间的冻结时长
UI_SECTOR_FREEZE_TIME = 5.0        # Sector (大分段) 完成时，面板定格显示成绩的时长 (也是切换下一面板的延迟)
UI_FINISH_FREEZE_TIME = 3.0        # 完赛瞬间，全屏 UI 定格的时长 (动画阶段 T1)
UI_SUMMARY_DISPLAY_TIME = 10.0     # 完赛后，Summary 成绩单展示的时长 (动画阶段 T3)

# ------------------------ 若不知道其具体含义，以下内容请勿修改！ ------------------------

# ==============================
# 赛道相关配置
# ==============================

# === 起终点配置 ===
START_LINE = [ (32352.5, 7891.5), (32377.5, 7891.5) ]
FINISH_LINE = [ (32352.5, 7885.5), (32377.5, 7885.5) ]

# 起终点专用的固定触发半径
TRIGGER_DIST = 5.0
MIN_LAP_TIME = 60.0

# 是否开启起步方向强制校验
# True: 必须向指定方向离开起点圈才算触发；比赛中若回到起点线后方则判无效。
# False: 只要离开触发圈即视为出发（不判断方向）。
ENABLE_START_DIRECTION_CHECK = True

# 起点出发的正方向
# 选项: "+x" (X增大的方向), "-x" (X减小的方向), "+z" (Z增大的方向), "-z" (Z减小的方向)
# 注意: 请根据实际赛道坐标系设定
START_DIRECTION = "-z"

# 动态加载 Checkpoints (中间点)
CHECKPOINTS_CSV_FILE = "CHECKPOINTS.csv"

def load_checkpoints_from_csv(csv_path):
    """
    读取 Checkpoints 配置。
    CSV 格式: name, type, x1, z1, x2, z2, trigger_dist_val
    """
    loaded_checkpoints = []
    
    if not os.path.exists(csv_path):
        print(f"[Config] ⚠️ 找不到 {csv_path}，CHECKPOINTS 为空！")
        return []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # 检查必要字段
            required = ['name', 'type', 'x1', 'z1', 'x2', 'z2']
            if not all(field in reader.fieldnames for field in required):
                print(f"[Config] ❌ CSV 表头错误，必须包含: {required}")
                return []

            for row in reader:
                if not row['name']: continue

                try:
                    # 标准化类型名称 (转大写)
                    raw_type = row['type'].strip().upper()
                    
                    # 兼容旧命名，统一转换为新术语
                    if raw_type == 'MAJOR': raw_type = 'SECTOR'
                    if raw_type == 'MINOR': raw_type = 'MINISECTOR'

                    # 获取半径
                    trig_val = float(row.get('trigger_dist_val', 5.0))
                    
                    cp_data = {
                        "name": row['name'].strip(),
                        "type": raw_type, # 存储为 SECTOR 或 MINISECTOR
                        "line": [
                            (float(row['x1']), float(row['z1'])),
                            (float(row['x2']), float(row['z2']))
                        ],
                        "trigger_dist": trig_val,
                        
                        # === 新增：预计算辅助标记，方便 UI 调用 ===
                        # 所有的 SECTOR 线，本质上也是一条 MINISECTOR 线 (它结束了当前的 Mini-Sector)
                        "is_sector": (raw_type == 'SECTOR'),
                        "is_minisector": True # 无论是 MINISECTOR 还是 SECTOR，都是计时点
                    }
                    loaded_checkpoints.append(cp_data)
                except ValueError as e:
                    print(f"[Config] 跳过坏行: {e}")

        print(f"[Config] 已加载 {len(loaded_checkpoints)} 个检查点。")
        return loaded_checkpoints

    except Exception as e:
        print(f"[Config] 读取失败: {e}")
        return []

# 执行加载
CHECKPOINTS = load_checkpoints_from_csv(CHECKPOINTS_CSV_FILE)

# 根据 CHECKPOINTS 自动生成 SECTOR_CONFIG 列表 (例如 [5, 4, 6])
# 逻辑：遍历所有检查点，累加计数；遇到 is_sector=True 时结算当前段
SECTOR_CONFIG = []
_current_ms_count = 0

if CHECKPOINTS:
    for cp in CHECKPOINTS:
        _current_ms_count += 1
        # 如果是 Sector 点，或者是最后一个点（终点通常也是 Sector，但以防万一）
        if cp.get('is_sector', False):
            SECTOR_CONFIG.append(_current_ms_count)
            _current_ms_count = 0
            
    # 处理剩余的 MiniSectors (如果最后一段没有显式标记 is_sector)
    if _current_ms_count > 0:
        SECTOR_CONFIG.append(_current_ms_count)
else:
    # 如果没有加载到 CSV，给一个默认值防止 UI 崩溃
    SECTOR_CONFIG = [5, 5, 5]

print(f"[Config] 自动推导赛道结构: {SECTOR_CONFIG}")

# ==============================
# 其他配置
# ==============================

# 计时与阈值设置
TIME_DELAY_LIMIT_1 = 2.0
TIME_DELAY_LIMIT_2 = 3.0

SECTOR_TIME_DELAY_FACTOR = 0.4
LOOP_TIME_DELAY_FACTOR = 0.16

# 数据存储
HISTORY_FILE_PATH = "lap_history.json"
SAVE_DATA = True

# 车辆参数
MAX_SPEED = 72.0       
PLOT_MAX_SPEED = 50.0