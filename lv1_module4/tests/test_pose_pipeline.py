"""문제 2 — PosePipeline 검증 (pytest).

지시문이 요구하는 "2개 이상" 을 아래 두 테스트로 채운다.

  1. camera_to_base 가 모듈 ③ 체인(행렬 곱)과 같은 결과를 주는가  -> test_camera_to_base_matches_chain
  2. base 로 갔다가 camera 로 되돌리면 원래 점군이 나오는가       -> test_roundtrip_restores_points

작성 요령
--------
- 비교는 `np.allclose` (기본 허용오차) 로 한다.
- 난수는 반드시 시드를 고정한다 (fixture `rng`).
- 관절 각도 0 에서 파이프라인이 default_chain 과 같은지, 각도를 바꾸면 결과가 달라지는지 등
  테스트를 더 붙이면 좋다 (아래 권장 예시).

실행: 프로젝트 루트에서  pytest tests/test_pose_pipeline.py -v
"""

import numpy as np
import pytest

from src.coordinate_chain import default_chain
from src.pose_pipeline import PosePipeline
from src.transform import make_T, transform_points
from src.rotation import rot_x, rot_y, rot_z


@pytest.fixture
def rng():
    """난수는 반드시 시드를 고정한다."""
    return np.random.default_rng(42)


@pytest.fixture
def pipeline():
    """모듈 ③ default_chain 과 같은 값으로 만든 파이프라인."""
    chain = default_chain()
    return PosePipeline(chain.get("base", "link"), chain.get("link", "camera"))


# --- 1. camera_to_base == 체인/행렬 곱 --------------------------------------

def test_camera_to_base_matches_chain(pipeline, rng):
    P_cam = rng.normal(0.0, 0.2, (50, 3))
    chain = default_chain()
    T_base_camera = chain.get("base", "link") @ chain.get("link", "camera")

    P_pipe = pipeline.camera_to_base(P_cam)
    P_chain = chain.transform("base", "camera", P_cam)
    P_matrix = transform_points(T_base_camera, P_cam)

    assert np.allclose(P_pipe, P_chain)
    assert np.allclose(P_pipe, P_matrix)


# --- 2. 왕복 검증 -------------------------------------------------------------

def test_roundtrip_restores_points(pipeline, rng):
    P_single = rng.normal(0.0, 0.2, 3)
    P_cloud = rng.normal(0.0, 0.2, (30, 3))

    for P_cam in (P_single, P_cloud):
        P_base = pipeline.camera_to_base(P_cam)
        P_back = pipeline.base_to_camera(P_base)
        assert np.allclose(P_back, P_cam)


# --- 추가 테스트 (권장) -------------------------------------------------------

def test_joint_angle_zero_is_nominal(pipeline):
    """set_joint_angle(0) 이면 T_base_link 가 생성자에 준 값 그대로."""
    chain = default_chain()
    pipeline.set_joint_angle(0.0)
    assert np.allclose(pipeline.T_base_link, chain.get("base", "link"))


def test_joint_angle_changes_result(pipeline, rng):
    """관절 각도를 바꾸면 같은 관측이 base 에서 다른 위치로 간다."""
    P_cam = rng.normal(0.0, 0.2, (20, 3))
    pipeline.set_joint_angle(0.0)
    P0 = pipeline.camera_to_base(P_cam)
    pipeline.set_joint_angle(np.deg2rad(30.0))
    P30 = pipeline.camera_to_base(P_cam)
    pipeline.set_joint_angle(0.0)
    assert not np.allclose(P0, P30)


def test_distance_is_preserved(pipeline, rng):
    """강체 변환은 두 점 사이 거리를 보존한다."""
    P_cam = rng.normal(0.0, 0.2, (10, 3))
    P_base = pipeline.camera_to_base(P_cam)
    d_cam = np.linalg.norm(P_cam[1:] - P_cam[:-1], axis=1)
    d_base = np.linalg.norm(P_base[1:] - P_base[:-1], axis=1)
    assert np.allclose(d_cam, d_base)


def test_rejects_wrong_shape():
    """(3,3) 을 넣으면 ValueError."""
    with pytest.raises(ValueError):
        PosePipeline(np.eye(3), np.eye(4))
