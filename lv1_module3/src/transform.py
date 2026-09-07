from __future__ import annotations
import numpy as np

from .vectors import inverse_gauss_jordan

__all__ = [
    "make_T",
    "inv_T",
    "inv_T_batch",
    "to_homogeneous",
    "transform_point",
    "transform_direction",
    "transform_points",
    "least_squares_normal_equation",
    "rmse",
]


def make_T(R, t) -> np.ndarray:
    '''
    회전 R(3x3)과 병진 t(3,)로 4x4 동차변환 T = [[R, t], [0, 1]] 을 만든다.
    R 이 3x3 이 아니면 ValueError.
    '''
    R = np.asarray(R, dtype=float)
    if R.shape != (3, 3):
        raise ValueError(f"R 은 3x3 이어야 합니다. 받은 shape={R.shape}")
    t = np.asarray(t, dtype=float).reshape(3)
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def inv_T(T) -> np.ndarray:
    '''
    동차변환의 역변환을 일반 역행렬 함수 없이 공식으로 구한다.
    T^-1 = [[R^T, -R^T t], [0, 1]] (R 이 직교이므로 R^-1 = R^T). 4x4 가 아니면 ValueError.
    '''
    T = np.asarray(T, dtype=float)
    if T.shape != (4, 4):
        raise ValueError(f"4x4 동차변환이 필요합니다. 받은 shape={T.shape}")
    R = T[:3, :3]
    t = T[:3, 3]
    Ti = np.eye(4)
    Ti[:3, :3] = R.T
    Ti[:3, 3] = -R.T @ t
    return Ti


def inv_T_batch(Ts) -> np.ndarray:
    '''
    (N, 4, 4) 동차변환 묶음을 반복문 없이 한 번에 역변환한다 (inv_T 공식을 배치 축으로 확장).
    '''
    Ts = np.asarray(Ts, dtype=float)
    R = Ts[:, :3, :3]
    t = Ts[:, :3, 3]
    Rt = np.swapaxes(R, 1, 2)
    t_new = -np.einsum("nij,nj->ni", Rt, t)

    out = np.zeros_like(Ts)
    out[:, :3, :3] = Rt
    out[:, :3, 3] = t_new
    out[:, 3, 3] = 1.0
    return out


def to_homogeneous(P, w: float = 1.0) -> np.ndarray:
    '''(3,) 또는 (N,3) 좌표에 마지막 성분 w 를 붙인다. w=1 이면 점, w=0 이면 방향.'''
    P = np.asarray(P, dtype=float)
    if P.ndim == 1:
        return np.append(P, w)
    w_col = np.full((P.shape[0], 1), w)
    return np.hstack([P, w_col])


def transform_point(T, p) -> np.ndarray:
    '''점 변환 (w=1): 회전과 병진이 모두 적용된다. 반환은 (3,).'''
    T = np.asarray(T, dtype=float)
    ph = to_homogeneous(np.asarray(p, dtype=float), 1.0)
    return (T @ ph)[:3]


def transform_direction(T, v) -> np.ndarray:
    '''방향 변환 (w=0): 회전만 적용되고 병진은 무시된다. 반환은 (3,).'''
    T = np.asarray(T, dtype=float)
    vh = to_homogeneous(np.asarray(v, dtype=float), 0.0)
    return (T @ vh)[:3]


def transform_points(T, P, w: float = 1.0) -> np.ndarray:
    '''(N,3) 점군을 반복문 없이 한 번에 변환한다. (3,) 입력도 받는다.'''
    T = np.asarray(T, dtype=float)
    P = np.asarray(P, dtype=float)
    single = (P.ndim == 1)
    P2 = P.reshape(1, -1) if single else P
    Ph = to_homogeneous(P2, w)          # (N, 4)
    out = (Ph @ T.T)[:, :3]             # (N, 3)
    return out[0] if single else out


def least_squares_normal_equation(A, b):
    '''
    정규방정식 (A^T A) x = A^T b 를 직접 세워 최소자승해를 구한다 ((A^T A)의 역행렬은 inverse_gauss_jordan 으로).
    Returns: x(최소자승해), residual(b - A x)
    '''
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    AtA = A.T @ A
    Atb = A.T @ b
    x = inverse_gauss_jordan(AtA) @ Atb
    residual = b - A @ x
    return x, residual


def rmse(residual) -> float:
    '''잔차의 RMSE = sqrt(mean(r^2)).'''
    residual = np.asarray(residual, dtype=float)
    return float(np.sqrt(np.mean(residual ** 2)))
