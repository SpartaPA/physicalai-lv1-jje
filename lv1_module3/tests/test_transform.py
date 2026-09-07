"""문제 5 — 동차변환 inv_T 검증 (pytest). [학생 작성용 템플릿]

지시문이 요구하는 것은 `inv_T` 검증이지만,
점/방향 구분과 벡터화, 최소자승까지 함께 검증해 두면 이후 문제에서 안전하다.

실행: 프로젝트 루트에서  pytest -v
"""

import numpy as np
import pytest

from src.rotation import rot_x, rot_y, rot_z
from src.transform import (
    inv_T,
    least_squares_normal_equation,
    make_T,
    transform_direction,
    transform_point,
    transform_points,
)


@pytest.fixture
def T():
    """테스트에 쓸 대표 동차변환 하나."""
    R = rot_z(0.9) @ rot_y(-0.35) @ rot_x(1.3)
    return make_T(R, [0.35, -0.15, 0.55])


def test_inv_T_gives_identity(T):
    Ti = inv_T(T)
    assert np.allclose(Ti @ T, np.eye(4))
    assert np.allclose(T @ Ti, np.eye(4))


def test_inv_T_matches_generic_inverse(T):
    assert np.allclose(inv_T(T), np.linalg.inv(T))          # 검산용


def test_point_and_direction_differ(T):
    v = np.array([1.0, 0.0, 0.0])
    p_out = transform_point(T, v)
    d_out = transform_direction(T, v)
    assert not np.allclose(p_out, d_out)
    assert np.allclose(p_out - d_out, T[:3, 3])
    assert np.isclose(np.linalg.norm(d_out), np.linalg.norm(v))


def test_transform_points_is_vectorized(T):
    rng = np.random.default_rng(42)
    P = rng.standard_normal((25, 3))
    batch = transform_points(T, P)
    looped = np.array([transform_point(T, p) for p in P])
    assert np.allclose(batch, looped)


def test_roundtrip_through_inverse(T):
    rng = np.random.default_rng(42)
    P = rng.standard_normal((25, 3))
    P_out = transform_points(T, P)
    P_back = transform_points(inv_T(T), P_out)
    assert np.allclose(P_back, P)


def test_least_squares_matches_lstsq():
    rng = np.random.default_rng(42)
    A = rng.standard_normal((50, 5))
    x_true = rng.standard_normal(5)
    b = A @ x_true + 1e-3 * rng.standard_normal(50)

    x_hat, residual = least_squares_normal_equation(A, b)
    x_ref = np.linalg.lstsq(A, b, rcond=None)[0]        # 비교 대상

    assert np.allclose(x_hat, x_ref)
    assert np.allclose(residual, b - A @ x_hat)
    assert np.allclose(A.T @ residual, 0.0, atol=1e-8)
