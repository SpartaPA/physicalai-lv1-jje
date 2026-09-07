import math

def calc_distance(x1, y1, x2, y2):
    """두 점 사이의 유클리드 거리."""
    return math.hypot(x2 - x1, y2 - y1)


def angle_to_goal(x, y, theta, gx, gy):
    """목표를 향한 필요 회전각을 -pi ~ pi 로 정규화해 반환한다."""
    target = math.atan2(gy - y, gx - x)
    return math.atan2(math.sin(target - theta), math.cos(target - theta))


def is_waypoint_reached(x, y, gx, gy, tolerance):
    """허용 오차(tolerance) 이내로 목표에 도달했는지 판정한다."""
    if tolerance < 0:
        raise ValueError('tolerance must be >= 0')
    return calc_distance(x, y, gx, gy) <= tolerance
