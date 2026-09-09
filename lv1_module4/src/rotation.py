from __future__ import annotations
import numpy as np

from .vectors import skew, det, dot, normalize, norm

__all__ = [
    "rot_x",
    "rot_y",
    "rot_z",
    "rodrigues",
    "gram_schmidt",
    "orthogonality_error",
    "is_rotation",
    "axis_angle_from_matrix",
    "quaternion_from_axis_angle"
]


def rot_x(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rodrigues(k, theta: float) -> np.ndarray:
    '''
    로드리게스 공식으로 임의 축(k) 회전 행렬을 만든다.
    R = I + sin(theta) * K + (1 - cos(theta)) * K @ K,  K = skew(normalize(k))
    k 는 함수 안에서 단위벡터로 정규화하므로 정규화되지 않은 축을 넣어도 결과는 같다.
    '''
    K = skew(normalize(k))
    return np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)


def gram_schmidt(A) -> np.ndarray:
    A = np.array(A, dtype=float, copy=True) # 직교화 하고자 하는 행렬
    n_cols = A.shape[1]
    Q = np.zeros_like(A) # 결과가 저장되는 단위행렬
    eps = 1e-10
    for j in range(n_cols):
        v = A[:, j].copy()
        for i in range(j):
            v -= dot(Q[:,i], v) * Q[:,i]
        nv = norm(v) # v 크기
        if nv < eps:
            raise ValueError(f"{j}번 열이 앞선 열들에 종속이므로 직교화 불가")
        Q[:,j] = v / nv
    return Q


def orthogonality_error(R) -> float:
    '''
    직교성 이탈 지표: || R^T R - I ||_F (프로베니우스 노름)
    '''
    R = np.asarray(R, dtype=float)
    E = R.T @ R - np.eye(R.shape[0])
    return float(np.sqrt(np.sum(E * E)))


def is_rotation(R, atol: float = 1e-8) -> bool:
    '''
    회전행렬 판정: 직교(R^T R = I)이고 det(R) = +1이면 True.
    det = -1이면 직교여도 반사가 섞인 것이라 회전 아님. 3x3이 아니면 False 출력
    '''
    R = np.asarray(R, dtype=float)
    if R.shape != (3, 3):
        return False
    orth_ok = orthogonality_error(R) < atol # 직교 행렬인가
    det_ok = abs(det(R)-1.0) < atol    # det(R)이 1에 가까운가
    return bool(orth_ok and det_ok)


def axis_angle_from_matrix(R, atol: float = 1e-8):
    '''
    회전행렬에서 회전축(axis)과 회전각(angle)을 복원
    각도는 trace(R) = 1 + 2*cos(theta)에서, 축은 반대칭 성분 R - R^T = 2*sin(theta)*[k]_x 에서 부호까지 구한다.
    theta=0(회전 없음), theta=pi(sin=0)는 반대칭 성분으로 부호를 못 구해 고유값 분해로 따로 처리한다.
    Returns: axis(단위 회전축, shape (3,)), angle(회전각 [rad], 0 <= angle <= pi)
    '''
    R = np.asarray(R, dtype=float)
    cos_theta = float(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))
    theta = float(np.arccos(cos_theta))

    if theta < atol:
        # 회전이 거의 없다 -> 축이 정의되지 않으므로 임의의 축(관용적으로 z)을 쓴다.
        return np.array([0.0, 0.0, 1.0]), 0.0

    if abs(theta - np.pi) < atol:
        # sin(theta) ~ 0 이라 R - R^T 로는 부호를 못 정한다.
        # 고유값 1 에 대응하는 고유벡터로 축을 구하고, 부호는 "최대 성분이 양수" 규약으로 고정한다.
        eigvals, eigvecs = np.linalg.eig(R)  # theta=pi 특수 케이스 전용 (검산이 아니라 축 복원 목적)
        idx = int(np.argmin(np.abs(eigvals-1.0)))
        axis = normalize(np.real(eigvecs[:, idx]))
        if axis[np.argmax(np.abs(axis))] < 0:
            axis = -axis
        return axis, theta

    # 일반적인 경우: 반대칭 성분 R - R^T = 2 sin(theta) [k]_x 에서 부호까지 고정된 축을 바로 얻는다.
    A = (R - R.T) / (2.0 * np.sin(theta))
    axis = normalize(np.array([A[2, 1], A[0, 2], A[1, 0]]))
    return axis, theta


def quaternion_from_axis_angle(axis, angle: float) -> np.ndarray:
    '''
    축-각을 단위 쿼터니언으로 변환: q = (k * sin(theta/2), cos(theta/2))
    반환 순서는 SciPy Rotation.as_quat()과 같은 (x, y, z, w).
    '''
    k = normalize(np.asarray(axis, dtype=float))
    half = angle / 2.0
    xyz = k * np.sin(half)
    w = np.cos(half)
    return np.array([xyz[0], xyz[1], xyz[2], w])
