import math

import pytest

from turtle_py.utils import angle_to_goal, calc_distance, is_waypoint_reached


def test_calc_distance_normal():
    assert calc_distance(0, 0, 3, 4) == pytest.approx(5.0)


def test_calc_distance_zero():
    assert calc_distance(1, 1, 1, 1) == 0.0


def test_angle_to_goal_normalized_range():
    # 목표가 뒤쪽에 있어 큰 각도가 나와도 -pi ~ pi 범위 안이어야 한다.
    result = angle_to_goal(0, 0, 0, -1, -1)
    assert -math.pi <= result <= math.pi


def test_angle_to_goal_zero_when_facing_goal():
    assert angle_to_goal(0, 0, 0, 1, 0) == pytest.approx(0.0)


def test_is_waypoint_reached_boundary():
    # 경계값: 허용 오차와 거리가 정확히 같으면 True, 살짝 넘으면 False
    assert is_waypoint_reached(0, 0, 0.5, 0, 0.5) is True
    assert is_waypoint_reached(0, 0, 0.51, 0, 0.5) is False


def test_is_waypoint_reached_invalid_tolerance():
    with pytest.raises(ValueError):
        is_waypoint_reached(0, 0, 0, 0, -1)
