**注：以下内容为AI根据代码内容生成，辅以简单的人工修改**

# Minecraft Ice Boat Race Timing

> MineCraft冰船竞速自动化计时与可视化工具
> MineCraft iceboat racing automation timing and visualization tool

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-red.svg)](https://opencv.org/)

## 项目简介

`minecraft_ice_boat_race_timing` 是一款专为《我的世界》冰船竞速设计的**自动化计时工具**。通过 OCR 实时识别游戏画面中的坐标与速度数据，提供专业的赛道分段计时、成绩记录与轨迹分析功能。

**适用场景**：服务器竞速训练、个人成绩记录、赛道调试与优化。

---

## 主要特性

### 核心功能
- **OCR 坐标识别**：基于模板匹配的轻量级 OCR，无需 Tesseract，支持自定义字符训练
- **三级计时体系**：
  - **Mini-Sector**（小分段）：每个检查点间的精细计时
  - **Sector**（大分段）：由多个 Mini-Sector 组成的阶段计时
  - **Loop**（总圈）：完整一圈的总用时
- **智能状态机**：`IDLE → READY → RACING` 三态管理，自动检测起终点触发
- **方向校验**：支持正向/反向检测，防止误触发

### 可视化反馈
- **颜色编码**（刷紫/刷绿/黄/红）：
  - 🟪 **Purple**：显著快于基准（刷紫）
  - 🟩 **Green**：快于基准（刷绿）
  - 🟨 **Yellow**：接近基准
  - 🟥 **Red**：明显慢于基准
- **实时计时面板**：总圈时间、当前 Sector 时间、Mini-Sector 分块显示
- **完赛动画序列**：成绩定格 → 展开 Summary → 淡出恢复

### 数据管理
- **JSON 历史记录**：持久化存储个人最佳成绩（Best Lap）与历史记录
- **滑动窗口动态基准**：可配置最近 N 圈作为比较基准，动态调整难度
- **CSV 轨迹记录**：保存每圈的坐标与速度数据
- **轨迹可视化**：自动生成带速度热力图的赛道轨迹分析图
- **异步保存**：完赛数据后台写入，不阻塞主线程

### 高度可配置
- 支持多显示器（游戏采集与 UI 显示可分离）
- 可调的 OCR 截取框与二值化阈值
- 可配置的赛道检查点（CSV 导入）
- 连续圈模式 / 单圈模式切换

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| GUI 框架 | PyQt6 |
| 图像处理 | OpenCV |
| 屏幕截取 | MSS |
| 数据分析 | NumPy, Pandas |
| 数据可视化 | Matplotlib |
| 数据持久化 | JSON, CSV |

---

## 项目结构

```
minecraft_ice_boat_race_timing/
├── main.py                     # 程序入口（PyQt6 + 多线程）
├── config.py                   # 全局配置文件（所有可调参数）
├── race_logic.py               # 核心计时逻辑（状态机 + 历史管理）
├── race_controller.py          # 控制器（连接 OCR → Logic）
├── ocr_engine.py               # OCR 引擎（模板匹配，支持训练模式）
├── calibration_tool.py         # 校准工具（调整截取框 + 阈值）
├── ui_main.py                  # PyQt6 主窗口（计时面板 + 动画）
├── ui_core.py                  # UI 核心组件（自定义控件）
├── data_save.py                # CSV 轨迹记录器（异步分离）
├── geometry_utils.py           # 几何计算工具（点到线段距离）
├── plot_total.py               # 轨迹可视化（生成分析图）
├── CHECKPOINTS.csv             # 赛道检查点配置文件
├── requirements.txt            # Python 依赖列表
├── font/
│   └── Formula1-Display-Regular.ttf  # F1 风格字体（可选）
├── record_data/                # 运行时生成的轨迹 CSV（自动创建）
└── lap_history_*.json          # 历史成绩记录（自动生成）
```

---

## 快速开始

### 1. 环境准备

请下载并安装 git 和 python 3.12/3.13 的最新版本，建议安装vscode或其他IDE，然后执行以下内容

```bash
# 克隆项目
git clone https://github.com/yourusername/minecraft_ice_boat_race_timing.git
cd minecraft_ice_boat_race_timing

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置赛道

**针对ict冰船群已做适配，将对每次冰船竞赛进行适配，可以跳过本节，其他类型赛道/其他检查点需求请按照下述内容进行检查点编辑**

编辑 `CHECKPOINTS.csv`，按以下格式定义赛道检查点：

```csv
name,type,x1,z1,x2,z2,trigger_dist_val
MS1,MINISECTOR,32557,7715,32583,7688,7
S1,SECTOR,32171,7260,32203,7245,7
...
```

- **name**：检查点名称
- **type**：`MINISECTOR`（小分段）或 `SECTOR`（大分段，同时也是 Mini-Sector 的结束点）
- **x1,z1,x2,z2**：线段端点坐标（X-Z 平面）
- **trigger_dist_val**：触发半径（距离检测线多远时触发）

> 赛道最后一个检查点必须为 `SECTOR` 类型，作为终点。

### 3. 校准 OCR

校准的目的是确定游戏画面中 **X 坐标、Z 坐标、速度** 三个数字区域的精确截取位置，以及最佳二值化阈值。

#### 3.0 坐标来源

由于偷懒，本项目没有直接对接minecraft，而是通过OCR方式识别游戏界面中的坐标值，目前推荐使用MiniHUD的坐标值进行OCR识别，并确保你的游戏字体不是多变的，推荐使用原版字体。

使用MiniHUD，建议进入MiniHUD配置界面，依次设置：

全部 - 字体缩放 - 你觉得舒服的缩放值，最好是正常的数
全部 - 文本背景 - 选择黑色（HEX值为 #A0000000 - #FF000000）
全部 - 文本颜色 - 选择白色（HEX值为 #FFFFFFFF）
通用 - 字体背景 - 否
通用 - 文本背景 - 是
通用 - 速度单位 - m/s
HUD信息行 - 坐标显示 - 是
HUD信息行 - 移动速度 - 是

#### 3.1 获取屏幕坐标

你需要先知道 **X 坐标、Z 坐标、速度** 三个数字在游戏窗口中的像素位置。推荐使用以下方法之一：

- **Windows 截图工具**（Win + Shift + S）→ 新建截图后，工具栏会显示鼠标指针的像素坐标。
- **第三方像素测量工具**（如 [Screen Ruler](https://sourceforge.net/projects/screenruler/) 或在线工具 [ginifab pixel ruler](https://www.ginifab.com/feeds/pixels/)）。
- **游戏内截图**，用图像编辑器查看坐标。

**操作步骤**：
1. 将游戏窗口置于前台，并进入冰船赛道。
2. 截图包含 **X 数值**（形如 `X: 32154.5`）、**Z 数值**（形如 `Z: 7891.5`）、**速度数值**（形如 `45.6`）的区域。
3. 用工具测量这三个数字区域左上角的像素坐标（相对于游戏窗口，而非屏幕），以及区域的宽度和高度。 
4. 将这些值填入 `config.py` 的 `BOX_X`、`BOX_Z`、`BOX_SPEED` 字典中（分别对应 `top`, `left`, `width`, `height`）。

#### 3.2 运行校准工具进行微调

```bash
python calibration_tool.py
```

工具会显示三个截取区域的二值化图像（纵向排列），并提供一个阈值滑动条。

- **目的**：确保每个区域**只显示纯数字**（没有额外的 `X:` 或 `m/s` 文本），且数字线条清晰、无噪点。
- 拖动 **Threshold** 滑动条，观察图像变化，直到数字笔画完整、背景干净。
- 如果区域包含多余内容，请返回 `config.py` 调整对应的 `BOX_*` 坐标，**重新运行校准工具**，直到满意。
- 记录下你满意的 **Threshold** 滑动条数值，在 `config.py` 中修改 `THRESHOLD_VAL`。

- 校准完成后，按 **`q`** 退出。

### 4. 训练 OCR

**本项目使用自研模板匹配 OCR，首次使用时 `font_templates.pkl` 不存在，必须通过训练模式建立字符模板。** 如果不训练，所有字符将被识别为 `?`，导致无法正常计时。

#### 4.1 进入训练模式

运行以下命令：

```bash
python ocr_engine.py
```

程序会启动实时采集，并显示当前识别结果（包括原始字符串）。当遇到一个**程序无法识别的字符**（即不在现有模板库中）时，会弹出一个窗口，显示该字符的二值化图像，并要求您输入对应的字符。

#### 4.2 交互标注方式

- 弹出的窗口标题为 **“OCR Trainer”**，显示一个放大的字符图像（如数字 `8` 或小数点 `.`）。
- 请在键盘上**按下该字符对应的按键**（例如数字键 `0`~`9`，或句点键 `.`，或负号键 `-`）。
- 程序会记录该字符并保存到 `font_templates.pkl`，然后继续运行。
- 如果你不确定字符是什么，或窗口显示的是噪点，可以按 **`Enter` 或 `Space`** 跳过此字符（但会标记为空，下次遇到同样字符会再次弹出）。

> **建议**：在训练模式下，先将游戏画面停留在能看到清晰数字的位置（如静止在起点），坐上冰船，让程序依次弹出所有可能的字符（数字 0-9，小数点，负号），一一输入。然后尝试轻点 w 开始移动，应该会立马跳出一些新的数，继续输入，到基本不跳出新内容后，尝试跑一圈，确认不会有新的内容出现。记得对于奇怪的内容，按 **`Enter` 或 `Space`** 跳过此字符。

- 训练过程中，终端会实时打印识别的原始字符串和转换后的数值，帮助你确认识别是否正确。
- 到终端按 **`Ctrl+C`** 终止训练。

#### 4.3 完成训练

训练完成后，`font_templates.pkl` 文件将保存在项目根目录。之后将 `ocr_engine.py` 中 `DigitOCR` 的 `training_mode` 参数设为 `False`（或直接运行 `main.py`，因为它默认使用只读模式），即进入竞赛模式，不再弹窗。

### 5. 配置文件

所有可调参数集中在 `config.py` 中，请根据你的实际环境仔细调整。

#### 5.1 必须修改的配置项

- `USER_NAME`：你的用户名，用于区分历史文件。
- `HISTORY_FILE_SUFFIX`：参考的用户历史记录，个人使用也是写你的用户名。
- `BOX_X`, `BOX_Z`, `BOX_SPEED`：从校准步骤得到的截取区域坐标。
- `THRESHOLD_VAL`：校准中确定的二值化阈值。

#### 5.2 UI 位置调整

计时窗口默认会出现在指定显示器的特定位置，你可以通过以下配置微调：

| 配置项 | 说明 |
|--------|------|
| `UI_WINDOW_LOCATED_POSITION` | 窗口定位模式，可选 `"left"`, `"mid"`, `"right"`，分别对应窗口左上角、顶部中间、右上角对齐到配置坐标 |
| `UI_WINDOW_X` | 水平偏移量（像素），在定位模式基础上额外偏移 |
| `UI_WINDOW_Y` | 垂直偏移量（像素） |
| `UI_ZOOM` | UI 整体缩放比例（1=原始大小，0.5=缩小一半，2=放大两倍） |

> 不同屏幕分辨率、缩放比例下，UI 位置可能需要调整。`config.py` 中已附带了部分常见配置的参考注释，请仔细阅读。

#### 5.3 重要提醒

`config.py` 中包含大量参数，每个参数都有详细的注释说明其作用。**在遇到任何异常或调整需求时，请首先仔细阅读 `config.py` 中相应配置项的注释，它们往往能解答你的疑问。**

### 6. 启动程序

```bash
python main.py
```

---

## 使用说明

### 基本操作流程

1. **就位**：将游戏角色移动至起点线附近（进入 `TRIGGER_DIST` 范围内），状态变为 `READY`
2. **出发**：向正确的方向离开起点线，计时自动开始（状态变为 `RACING`）
3. **比赛**：依次通过所有检查点，UI 实时更新计时数据
4. **完赛**：通过最后一个检查点（终点线），自动结算成绩并触发完赛动画

### 计时面板说明

| 面板 | 内容 |
|------|------|
| **LAP TIME** | 总圈时间 + 当前 Sector 的 Delta 值 + 各 Sector 分块成绩 |
| **CURRENT SECTOR** | 当前 Sector 已用时间 + 各 Mini-Sector 分块成绩 |
| **Summary**（完赛时） | 各 Sector 总成绩 + 内部 Mini-Sector 明细 |

### 颜色含义

- 🟪 **紫色**：刷新最佳成绩（刷紫）
- 🟩 **绿色**：优于当前基准（刷绿）
- 🟨 **黄色**：接近基准
- 🟥 **红色**：明显落后

### 按键操作

- `Ctrl+C`：安全退出（程序会清理未完成的 CSV 记录）

---

## 配置详解

### 核心配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ENABLE_HISTORY_SAVE` | 是否保存历史记录 | `True` |
| `ENABLE_UI` | 是否启用图形界面 | `True` |
| `CONTINUOUS_LAPPING` | 连续圈模式（过线自动开始下一圈） | `False` |
| `ENABLE_START_DIRECTION_CHECK` | 是否启用起步方向校验 | `True` |
| `START_DIRECTION` | 起步方向（`+x` / `-x` / `+z` / `-z`） | `"-z"` |
| `ENABLE_STAGE_ROLLING_WINDOW_BEST` | Sector 与 Mini-Sector 是否使用滑动窗口基准 | `True` |
| `ENABLE_LOOP_ROLLING_WINDOW_BEST` | 总圈是否使用滑动窗口基准 | `True` |
| `STAGE_ROLLING_WINDOW_SIZE` | Sector 滑动窗口大小 | `10` |
| `LOOP_ROLLING_WINDOW_SIZE` | 总圈滑动窗口大小 | `20` |
| `UI_ZOOM` | UI 缩放比例 | `1` |
| `UI_BACKGROUND_ALPHA` | UI 背景透明度（0~255） | `120` |

### OCR 相关

| 配置项 | 说明 |
|--------|------|
| `BOX_X` / `BOX_Z` / `BOX_SPEED` | OCR 截取框坐标（需通过校准工具调试） |
| `THRESHOLD_VAL` | 二值化阈值（0~255） |
| `LIMIT_FPS` | OCR 采集帧率上限 |

### 赛道相关

| 配置项 | 说明 |
|--------|------|
| `START_LINE` | 起点线坐标 `[(x1,z1), (x2,z2)]` |
| `FINISH_LINE` | 终点线坐标（通常与起点不同，或由最后一个检查点充当） |
| `TRIGGER_DIST` | 起终点触发半径 |
| `MIN_LAP_TIME` | 有效圈最短时间（防误触） |
| `CHECKPOINTS_CSV_FILE` | 检查点 CSV 文件路径 |
| `SECTOR_CONFIG` | 自动由检查点推导，无需手动配置 |

---

## 数据输出

### 历史记录（JSON）

文件名：`race_history_[USER_NAME].json`

```json
{
  "best_lap": {
    "total_time": 95.234,
    "formatted_total_time": "1:35.234",
    "segments": [...],
    "sectors": [...],
    "delta": "+0.000",
    "color": "yellow",
    "rolling_queue": [...]
  },
  "history": [...]
}
```

### 轨迹记录（CSV）

路径：`record_data/real_track_YYYYMMDD_HHMMSS.csv`

```csv
time,x,y,z,speed
1700000000.123,32352.5,0.0,7891.5,45.6
...
```

### 轨迹分析图

自动生成：`record_data/real_track_*_plot_analysis.png`

- 速度颜色映射（红→黄→绿→蓝→紫）
- 统计信息：最大速度、平均速度、总长度、总用时
