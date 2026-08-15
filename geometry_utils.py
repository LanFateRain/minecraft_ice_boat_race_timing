# geometry_utils.py

import math
import numpy as np

def point_to_line_segment_distance(point, shape_config):
    """
    计算点到几何形状（点或线段）的最短距离 (X-Z 平面)。
    
    Args:
        point: 车辆当前坐标 (x, y, z) 或 (x, z)
        shape_config: 配置文件中的形状数据
                      - 单点: (x, y, z)
                      - 线段: [ (x1, z1), (x2, z2) ] 或 [ (x1, y1, z1), (x2, y2, z2) ]
                      
    Returns:
        float: 最短欧几里得距离
    """
    # 1. 统一处理输入点为 (x, z)
    px = point[0]
    pz = point[2] if len(point) == 3 else point[1]

    # 2. 检查配置类型
    # 如果不是列表，或者列表长度小于2，视为单点
    if not isinstance(shape_config, list) or len(shape_config) < 2:
        # 处理单点情况
        target = shape_config[0] if isinstance(shape_config, list) else shape_config
        tx = target[0]
        tz = target[2] if len(target) == 3 else target[1]
        return math.sqrt((px - tx)**2 + (pz - tz)**2)

    # 3. 处理线段情况 [Start, End]
    p_start = shape_config[0]
    p_end = shape_config[1]

    # 提取 X, Z 坐标
    # 自动兼容 (x,z) 或 (x,y,z) 格式
    x1, z1 = p_start[0], (p_start[2] if len(p_start) == 3 else p_start[1])
    x2, z2 = p_end[0], (p_end[2] if len(p_end) == 3 else p_end[1])

    # 使用 Numpy 进行向量计算
    P = np.array([px, pz])
    A = np.array([x1, z1])
    B = np.array([x2, z2])

    AB = B - A
    AP = P - A

    len_sq = np.sum(AB**2)

    # 如果线段两端重合 (长度为0)，退化为点到点距离
    if len_sq == 0:
        return np.sqrt(np.sum((P - A)**2))

    # 计算投影比例 t
    t = np.dot(AP, AB) / len_sq

    # 限制 t 在 [0, 1] 之间 (确保投影在线段范围内)
    t = max(0, min(1, t))

    # 计算最近点 Q
    Q = A + t * AB

    # 返回 P 到 Q 的距离
    return np.sqrt(np.sum((P - Q)**2))