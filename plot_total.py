# plot_total.py
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import config
import os

def format_duration(seconds):
    """将秒数格式化为 MM:SS.sss"""
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}"

def plot_track_data(csv_path):
    """
    读取 CSV 并生成轨迹分析图。
    该函数可以被外部模块直接调用。
    """
    # --- 1. 路径检查 ---
    if not os.path.exists(csv_path):
        print(f"[Plot] 错误: 找不到文件 {csv_path}")
        return

    print(f"[Plot] 正在处理数据: {csv_path} ...")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[Plot] 读取CSV失败: {e}")
        return

    # --- 2. 数据处理 ---
    try:
        # 检查必要列
        if 'x' not in df.columns or 'z' not in df.columns:
            print("[Plot] CSV缺少必要列: x 或 z")
            return

        # ==============================
        # 2.1 异常点过滤
        # ==============================
        x_min, x_max = config.X_LIMIT
        z_min, z_max = config.Z_LIMIT

        original_count = len(df)

        valid_mask = (
            df['x'].between(x_min, x_max) &
            df['z'].between(z_min, z_max)
        )

        df = df.loc[valid_mask].copy()

        filtered_count = original_count - len(df)

        print(
            f"[Plot] 异常点过滤: "
            f"原始 {original_count} 点, "
            f"排除 {filtered_count} 点, "
            f"保留 {len(df)} 点"
        )

        # 过滤之后没有足够的数据
        if len(df) < 2:
            print("[Plot] 错误: 过滤异常点后有效数据不足，无法绘图")
            return

        # ==============================
        # 2.2 获取有效轨迹数据
        # ==============================
        x = df['x'].to_numpy()
        z = df['z'].to_numpy()

        # ==============================
        # 2.3 获取速度
        # ==============================
        if 'speed' in df.columns:
            speed = df['speed'].to_numpy()

        elif 'velocity' in df.columns:
            speed = df['velocity'].to_numpy()

        else:
            # 如果没有速度列，通过位置差分计算
            dx = np.diff(x, prepend=x[0])
            dz = np.diff(z, prepend=z[0])

            speed = np.sqrt(dx**2 + dz**2) * 10
            # 这里的系数根据实际采样频率调整

    except KeyError as e:
        print(f"[Plot] CSV缺少必要列: {e}")
        return

    # --- 3. 计算统计信息 ---
    max_speed_val = speed.max()

    # ==============================
    # 计算轨迹总长度
    # ==============================
    dx = np.diff(x)
    dz = np.diff(z)

    segment_length = np.sqrt(dx**2 + dz**2)
    total_length = segment_length.sum()

    # ==============================
    # 计算总用时
    # ==============================
    duration_str = "N/A"
    total_seconds = None

    # 优先使用 time 列计算总耗时
    if 'time' in df.columns and len(df) > 1:
        total_seconds = df['time'].iloc[-1] - df['time'].iloc[0]

    # 如果没有 time，则尝试 timestamp
    elif 'timestamp' in df.columns and len(df) > 1:
        total_seconds = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]

    if total_seconds is not None:
        duration_str = format_duration(total_seconds)

    # ==============================
    # 计算平均速度
    # ==============================
    if total_seconds is not None and total_seconds > 0:
        avg_speed_val = total_length / total_seconds
    else:
        avg_speed_val = 0.0

    # --- 4. 颜色设置 (0-30-60-80-100 分布) ---
    nodes = [0.0, 0.3, 0.6, 0.8, 1.0]
    colors = ['red', 'yellow', '#00ff00', 'blue', 'purple']
    cmap_data = list(zip(nodes, colors))
    custom_cmap = mcolors.LinearSegmentedColormap.from_list("custom_speed_map", cmap_data)

    # --- 5. 绘图设置 ---
    fig, ax = plt.subplots(figsize=(20, 16), dpi=300)
    
    # s=5: 中等线宽
    scatter = ax.scatter(x, z, c=speed, cmap=custom_cmap, vmin=0, vmax=config.PLOT_MAX_SPEED, s=5, alpha=0.9, edgecolors='none')

    # --- 6. 坐标轴调整 ---
    ax.invert_yaxis()
    ax.set_aspect('equal')
    ax.set_xlabel('Position X', fontsize=14, color='black')
    ax.set_ylabel('Position Z (Inverted)', fontsize=14, color='black')
    
    # --- 7. 标题设置 (竖线已替换为空格) ---
    title_str = (
        # f'Track Analysis: {os.path.basename(csv_path)}\n'
        # f'Max Speed: {max_speed_val:.2f}    Total Time: {duration_str}'
        f'Track Analysis: {os.path.basename(csv_path)}\n'
        f'Max Speed: {max_speed_val:.2f}    '
        f'Avg Speed: {avg_speed_val:.2f}    '
        f'Total Length: {total_length:.2f}    '
        f'Total Time: {duration_str}'
    )
    ax.set_title(title_str, color='black', fontsize=20, pad=20)

    # --- 8. 色条设置 ---
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.025, pad=0.04)
    cbar.set_label('Speed (0-60)', rotation=270, labelpad=20, color='black', fontsize=12)
    cbar.ax.tick_params(colors='black', labelsize=10)
    
    ax.grid(True, linestyle='--', alpha=0.3, color='gray')

    # --- 9. 保存 ---
    output_filename = csv_path.replace('.csv', '_plot_analysis.png')
    plt.savefig(output_filename, bbox_inches='tight', facecolor='white')
    print(f"[Plot] 绘图完成！图片保存至: {output_filename}")
    
    # 释放内存，防止批量处理时内存溢出
    plt.close(fig) 

if __name__ == "__main__":
    # 测试代码
    data_folder = "record_data"
    file_name = "real_track_20260815_144556.csv"
    full_path = os.path.join(data_folder, file_name)
    plot_track_data(full_path)