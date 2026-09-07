from __future__ import annotations
import numpy as np
"""
규칙
----
- `np.linalg` 는 노트북에서 **검산용으로만** 쓰고, 이 모듈 안에서는 쓰지 않는다.
  (`inverse_gauss_jordan` 이 던지는 `np.linalg.LinAlgError` 예외 타입만 예외)
- 각 함수의 docstring 에 적힌 계약(입력/출력/예외)을 그대로 지킨다.
  노트북의 검증 셀과 `tests/` 가 이 계약을 기준으로 채점된다.
- 구현을 마치면 `raise NotImplementedError(...)` 줄을 지운다.
"""

__all__=[
    "as_vector",
    "dot",
    "norm",
    "angle_between",
    "normalize",
    "project",
    "reject",
    "skew",
    "cross",
    "plane_normal",
    "row_echelon",
    "rank",
    "det",
    "gauss_eliminate",
    "inverse_gauss_jordan"
]

def as_vector(v) -> np.ndarray:
    '''
    입력(리스트/튜플/배열)을 1차원 float 배열로 변환
    '''
    arr = np.asarray(v, dtype=float)
    if arr.ndim!=1:
        raise ValueError(f"1차원 벡터를 입력하세요. 받은 shape:{arr.shape}")
    return arr

def dot(a, b) -> float:
    a, b = as_vector(a), as_vector(b)
    if len(a)!=len(b):
        raise ValueError(f"내적 시 두 벡터 길이가 일치해야 합니다. a의 길이:{len(a)}, b의 길이:{len(b)}")
    result = 0.0
    for i in range(len(a)):
        result += a[i]*b[i]
    return float(result)


def norm(v) -> float:
    v = as_vector(v)
    return float(np.sqrt(np.sum(v**2)))


def angle_between(a, b, degrees: bool = True, eps=1e-12) -> float:
    '''
    두 벡터 a, b의 사이각 theta
    '''
    if norm(a)*norm(b)<eps:
        raise ValueError("두 벡터의 크기의 곱이 1e-12이하입니다.")
    cos = dot(a,b)/(norm(a)*norm(b))
    cos = np.clip(cos, -1, 1)
    return float(np.degrees(np.arccos(cos)) if degrees else np.arccos(cos))


def normalize(v, eps: float = 1e-12) -> np.ndarray:
    # 크기가 0이면 raise error
    v = as_vector(v)
    n = norm(v)
    if n < eps:
        raise ValueError(f"벡터의 크기가 {eps}미만입니다.")
    return v/n


def project(a, b, eps: float = 1e-12) -> np.ndarray:
    a, b = as_vector(a), as_vector(b)
    dot_b = dot(b,b)
    if dot_b < eps:
        raise ValueError(f"벡터의 크기가 {eps}미만입니다.")
    return dot(a,b)/dot_b*b


def reject(a,b) -> np.ndarray:
    a = as_vector(a)
    return a-project(a,b)


def skew(v) -> np.ndarray:
    v = as_vector(v)
    if len(v)!=3:
        raise ValueError(f"벡터의 길이가 3이 아닙니다. 현재 벡터의 길이: {len(v)}")
    result = np.array([[0, -v[2], v[1]],
                       [v[2], 0, -v[0]],
                       [-v[1], v[0], 0]])
    return result

def cross(a, b) -> np.ndarray:
    '''
    외적을 반대칭행렬 곱으로 계산한다. a x b == skew(a) @ b
    '''
    b = as_vector(b)
    return skew(a) @ b


def plane_normal(P1, P2, P3):
    '''
    세 점 P1, P2, P3가 이루는 평면의 단위 법선벡터
    두 모서리 벡터(P2-P1, P3-P1)의 외적으로 구하며, 세 점이 일직선이면 외적이 영벡터가 되어 normalize 에서 ValueError 가 발생
    '''
    P1, P2, P3 = as_vector(P1), as_vector(P2), as_vector(P3)
    n = cross(P2 - P1, P3 - P1)
    return normalize(n)


def row_echelon(A, pivoting:bool=True):
    '''
    행렬 A를 부분 피벗팅 가우스 소거로 행 사다리꼴 U로 축약
    
    Parameters
    ----------
        A: array_like, shape (n_rows, n_cols)
        pivoting: bool, optional
            True이면 부분 피벗팅 수행, False이면 피벗팅 수행하지 않음

    Returns
    -------
        U: np.ndarray, shape (n_rows, n_cols)
            피벗 아래가 전부 0인 행 사다리꼴 행렬
        pivot_cols: list of int
            피벗 열의 인덱스, len(pivot_cols) = rank(A)
        swaps: int
            서로 다른 행을 교환한 횟수, determinant 계산 시 부호 결정에 필요
            det(A) = (-1)**swaps * prod(pivot elements)
    '''

    U = np.array(A, dtype=float, copy=True)
    if U.ndim!=2:
        raise ValueError(f"2차원 행렬을 입력하세요. 받은 shape:{U.shape}")
    rows, cols = U.shape
    pivot_row = 0
    pivot_cols = []
    swaps = 0 # 서로 다른 행을 교환한 횟수 -> determinant 계산 시 필요 (부호 결정)

    # columns를 순회하는 이유: 각 열을 순회하며 각각의 피벗을 찾기 위함
    for col in range(cols):
        if pivot_row >= rows:
            break

        # 고정된 열에 대해 확정되지 않은 행 중에서 절댓값이 가장 큰 피벗을 찾음
        if pivoting:
            max_row = np.argmax(np.abs(U[pivot_row:rows, col])) + pivot_row
        else:
            max_row = pivot_row

        # 행렬 크기(scale)에 비례하는 허용오차 -> 원소 값이 크거나 작아도 0 판정이 안정적
        tol = max(rows, cols) * np.finfo(float).eps * max(1.0, np.max(np.abs(U)))
        if np.abs(U[max_row, col]) < tol:
            continue # 값이 0에 가까우면 피벗이 없으므로 다음 열로 넘어감

        # 만약 max_row와 pivot_row가 다르면 행을 교환
        # 같은 경우: pivot_row가 이미 절댓값이 가장 큰 피벗을 가지고 있으므로 교환할 필요 없음 -> pass
        if max_row != pivot_row:
            U[[max_row, pivot_row]] = U[[pivot_row, max_row]]
            swaps += 1

        for r in range(pivot_row + 1, rows):
            # factor: 피벗 행을 이용하여 현재 행을 제거하기 위한 계수
            factor = U[r, col] / U[pivot_row, col]
            U[r, col:] -= factor * U[pivot_row, col:]

        pivot_cols.append(col)
        pivot_row += 1

    return U, pivot_cols, swaps


def rank(A) -> int:
    _, pivot_cols, _ = row_echelon(A)
    return len(pivot_cols)



def det(A) -> float:
    A = np.asarray(A, dtype=float)
    if A.ndim!=2:
        raise ValueError(f"2차원 행렬을 입력하세요. 받은 shape:{A.shape}")
    n = A.shape[0]
    if n != A.shape[1]:
        raise ValueError(f"정방행렬이 아닙니다. shape:{A.shape}")
    U, pivot_cols, swaps = row_echelon(A)
    if len(pivot_cols) < n: # 피벗이 n개보다 적으면 특이행렬 -> det는 정확히 0
        return 0.0
    det = (-1)**swaps * np.prod(np.diag(U)) # 행 교환을 하면 det의 부호가 바뀜
    return float(det)



def gauss_eliminate(A, b, pivoting:bool=True, verbose:bool=False):
    A = np.array(A, dtype=float, copy=True)
    b = np.array(b, dtype=float, copy=True).reshape(-1)
    n = A.shape[0]
    if A.ndim != 2 or A.shape[1] != n:
        raise ValueError(f"정사각 행렬이 필요합니다. 받은 shape={A.shape}")
    if b.shape[0] != n:
        raise ValueError(f"b 의 크기가 A 와 맞지 않습니다. A={A.shape}, b={b.shape}")

    Ab = np.hstack([A, b.reshape(-1, 1)])
    steps = [Ab.copy()]
    if verbose:
        print("초기 첨가행렬 [A|b]:\n", Ab)

    for col in range(n):
        if pivoting:
            piv_row = col + int(np.argmax(np.abs(Ab[col:, col])))
        else:
            piv_row = col

        if Ab[piv_row, col] == 0.0:
            raise ZeroDivisionError(f"열 {col} 에 0 이 아닌 피벗이 없습니다. 해가 유일하지 않습니다.")

        if piv_row != col:
            Ab[[col, piv_row]] = Ab[[piv_row, col]]
            steps.append(Ab.copy())
            if verbose:
                print(f"행 교환 (행 {col} <-> 행 {piv_row}):\n", Ab)

        for r in range(col + 1, n):
            factor = Ab[r, col] / Ab[col, col]
            if factor != 0.0:
                Ab[r, col:] -= factor * Ab[col, col:]
        steps.append(Ab.copy())
        if verbose:
            print(f"열 {col} 소거 후:\n", Ab)

    x = np.zeros(n)
    for i in range(n - 1, -1, -1):
        x[i] = (Ab[i, -1] - Ab[i, i + 1:n] @ x[i + 1:n]) / Ab[i, i]
    return x, steps


def inverse_gauss_jordan(A) -> np.ndarray:
    """가우스-조던 소거로 역행렬을 구한다. [A|I] -> [I|A^-1].

    정사각이 아니면 ValueError, 특이행렬이면 np.linalg.LinAlgError.
    (`np.linalg.inv` 를 부르지 말고 소거로 직접 구한다)
    """
    A = np.asarray(A, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"정사각 행렬이 필요합니다. 받은 shape={A.shape}")
    n = A.shape[0]
    M = np.hstack([A.copy(), np.eye(n)])
    tol = n * np.finfo(float).eps * max(1.0, np.max(np.abs(A)))

    for col in range(n):
        piv_row = col + int(np.argmax(np.abs(M[col:, col])))
        if abs(M[piv_row, col]) < tol:
            raise np.linalg.LinAlgError("특이행렬이라 역행렬이 존재하지 않습니다.")
        if piv_row != col:
            M[[col, piv_row]] = M[[piv_row, col]]
        M[col, :] = M[col, :] / M[col, col]
        for r in range(n):
            if r != col and M[r, col] != 0.0:
                M[r, :] -= M[r, col] * M[col, :]
    return M[:, n:]