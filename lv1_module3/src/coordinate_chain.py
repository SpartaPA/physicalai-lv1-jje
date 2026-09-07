from __future__ import annotations
import numpy as np

from .rotation import axis_angle_from_matrix, rot_x, rot_y, rot_z
from .transform import inv_T, make_T, transform_points

__all__ = ["CoordinateChain",
           "default_chain",
           "camera_point_to_base",
           "base_point_to_camera"]


class CoordinateChain:
    '''부모 -> 자식 동차변환을 이름으로 등록하고, 임의의 두 프레임 사이 변환을 만든다 (TF2 의 축소판).'''

    def __init__(self, root: str = "base"):
        self.root = root
        self._parent: dict[str, str] = {}                 # child -> parent
        self._T: dict[tuple[str, str], np.ndarray] = {}   # (parent, child) -> T

    def add(self, parent: str, child: str, T) -> "CoordinateChain":
        '''parent 기준 child 프레임의 자세 T(parent<-child)를 등록한다. 체이닝을 위해 self 를 반환. 4x4 가 아니면 ValueError.'''
        T = np.asarray(T, dtype=float)
        if T.shape != (4, 4):
            raise ValueError(f"4x4 동차변환이 필요합니다. 받은 shape={T.shape}")
        self._parent[child] = parent
        self._T[(parent, child)] = T
        return self

    def get(self, parent: str, child: str) -> np.ndarray:
        '''등록해 둔 T(parent <- child) 를 그대로 돌려준다.'''
        return self._T[(parent, child)]

    def frames(self) -> list[str]:
        '''등록된 프레임 이름 목록 (root 포함).'''
        return [self.root] + list(self._parent.keys())

    def _path_to_root(self, frame: str) -> list[str]:
        '''frame 에서 root 까지의 경로 [frame, ..., root] 를 만든다. root 에 연결되어 있지 않으면 KeyError.'''
        path = [frame]
        cur = frame
        while cur != self.root:
            if cur not in self._parent:
                raise KeyError(f"'{frame}' 이 root('{self.root}') 에 연결되어 있지 않습니다.")
            cur = self._parent[cur]
            path.append(cur)
        return path

    def T_from_root(self, frame: str) -> np.ndarray:
        '''root 기준 frame 의 자세 T(root <- frame). 경로를 따라가며 등록된 변환을 순서대로 곱한다.'''
        if frame == self.root:
            return np.eye(4)
        path = self._path_to_root(frame)          # [frame, ..., root]
        chain = path[::-1]                          # [root, ..., frame] 로 뒤집어서 root부터 곱해나감
        T = np.eye(4)
        for parent, child in zip(chain[:-1], chain[1:]):
            # T(root<-child) = T(root<-parent) @ T(parent<-child): 왼쪽부터 누적해서 곱해야 상쇄되어 최종적으로 T(root<-frame) 하나로 합쳐짐
            T = T @ self._T[(parent, child)]
        return T

    def T(self, target: str, source: str) -> np.ndarray:
        '''source 좌표를 target 좌표로 바꾸는 변환. T(target<-source) = inv(T(root<-target)) @ T(root<-source).'''
        T_root_target = self.T_from_root(target)   # T(root<-target)
        T_root_source = self.T_from_root(source)   # T(root<-source)
        # inv_T(T(root<-target)) = T(target<-root) 이므로, T(target<-root) @ T(root<-source) 로 root 가 상쇄되어 T(target<-source) 가 된다.
        return inv_T(T_root_target) @ T_root_source

    def transform(self, target: str, source: str, P, w: float = 1.0) -> np.ndarray:
        '''source 프레임의 점(w=1) 또는 방향(w=0)을 target 프레임으로 변환한다. (3,)/(N,3) 모두 지원, 반복문 없음.'''
        T_ts = self.T(target, source)
        return transform_points(T_ts, np.asarray(P, dtype=float), w=w)

    def axis_angle(self, target: str, source: str):
        '''T(target <- source) 의 회전 부분에서 회전축과 회전각을 복원한다.'''
        T_ts = self.T(target, source)
        return axis_angle_from_matrix(T_ts[:3, :3])


def default_chain() -> CoordinateChain:
    '''
    과제 기본 체인(base -> link -> camera)을 만든다.
    base->link: z축 22.5도 회전 후 (0.35, 0.05, 0.45) m 이동
    link->camera: y축 -22.5도, x축 67.5도 회전(rot_y @ rot_x) 후 (0.12, 0.04, 0.18) m 이동
    '''
    T_base_link = make_T(rot_z(np.deg2rad(22.5)), [0.35, 0.05, 0.45])
    # rot_y @ rot_x: 오른쪽(rot_x)이 먼저 적용되고 그 결과에 왼쪽(rot_y)이 적용된다 (행렬곱 오른쪽부터 적용)
    T_link_camera = make_T(rot_y(np.deg2rad(-22.5)) @ rot_x(np.deg2rad(67.5)), [0.12, 0.04, 0.18])
    return CoordinateChain("base").add("base", "link", T_base_link).add("link", "camera", T_link_camera)


def camera_point_to_base(p_cam, chain: CoordinateChain | None = None) -> np.ndarray:
    '''카메라 기준 좌표 -> base 기준 좌표. (3,)/(N,3) 모두 지원. chain 이 None 이면 default_chain() 을 쓴다.'''
    if chain is None:
        chain = default_chain()
    return chain.transform("base", "camera", p_cam, w=1.0)


def base_point_to_camera(p_base, chain: CoordinateChain | None = None) -> np.ndarray:
    '''base 기준 좌표 -> 카메라 기준 좌표 (왕복 검증용).'''
    if chain is None:
        chain = default_chain()
    return chain.transform("camera", "base", p_base, w=1.0)
