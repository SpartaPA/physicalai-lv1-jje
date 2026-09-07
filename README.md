# physicalai-lv1-jje

정조은 Level 1 과제 저장소입니다.

---

## 목차
- [physicalai-lv1-jje](#physicalai-lv1-jje)
  - [목차](#목차)
  - [모듈별 과제](#모듈별-과제)
  - [디렉토리 구조](#디렉토리-구조)
  - [실행/개발 환경](#실행개발-환경)

---

## 모듈별 과제

| 모듈 | 주제 | Report |
| --- | --- | --- |
| Module 1 | 배달 로봇 온보딩 — 연산 분담/실시간성 설계, Linux 장치·서비스 관리(systemd, udev, SSH) | [lv1_module1/report.md](./lv1_module1/report.md) |
| Module 2 | turtlesim ROS2 패키지 — C++ 빌드 체계(g++ → CMake), rclpy/rclcpp 노드 구현 | [lv1_module2/report.md](./lv1_module2/report.md) |
| Module 3 | 좌표 변환과 수학 라이브러리 — 벡터/회전행렬 구현 및 좌표계 체인 검증 | [lv1_module3/report.md](./lv1_module3/report.md) |

---

## 디렉토리 구조

```
physicalai-lv1-jje/
├── lv1_module1/
│   ├── images/
│   ├── rules/
│   │   └── 99-robot-sensor.rules
│   └── report.md
├── lv1_module2/
│   ├── bags/
│   │   └── q10_bag/
│   ├── cpp_basics/
│   │   ├── sensors/
│   │   ├── CMakeLists.txt
│   │   ├── main.cpp
│   │   ├── motor.cpp
│   │   ├── motor.hpp
│   │   └── stop_distance.cpp
│   ├── ros2_ws/
│   │   └── src/
│   │       ├── turtle_cpp/
│   │       ├── turtle_examples/
│   │       ├── turtle_interfaces/
│   │       └── turtle_py/
│   ├── screenshots/
│   └── report.md
├── lv1_module3/
│   ├── images/
│   ├── notebooks/
│   │   ├── 01_vectors.ipynb
│   │   ├── 02_rotation.ipynb
│   │   ├── 03_reorthogonalize.ipynb
│   │   ├── 04_linear_system.ipynb
│   │   ├── 05_transform.ipynb
│   │   └── 06_chain.ipynb
│   ├── src/
│   │   ├── coordinate_chain.py
│   │   ├── rotation.py
│   │   ├── transform.py
│   │   └── vectors.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_rotation.py
│   │   └── test_transform.py
│   ├── report.md
│   └── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## 실행/개발 환경

- OS: Ubuntu 22.04.5 LTS (kernel 6.8.0-138-generic)
- Module 2: C++17 (g++ / CMake), ROS 2 (colcon build)
- Module 3: Python — `pip install -r lv1_module3/requirements.txt` (numpy, matplotlib, scipy, pytest, jupyterlab)
