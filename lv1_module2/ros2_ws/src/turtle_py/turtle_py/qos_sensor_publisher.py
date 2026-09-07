#!/usr/bin/env python3
"""qos_sensor_publisher — 문제 7: /turtle_distance 를 Best-Effort 로 발행하는 실험용 발행자.

목적: "발행자 Best-Effort + 구독자 Reliable = 연결 안 됨" 을 직접 재현한다.

  터미널 1: ros2 run turtlesim turtlesim_node
  터미널 2: ros2 run turtle_py qos_sensor_publisher                      # 기본 best_effort
  터미널 3: ros2 run turtle_cpp distance_subscriber                      # Reliable 구독자 → 아무것도 안 옴
  터미널 4: ros2 topic info -v /turtle_distance                          # 양쪽 QoS 비교
  고치기  : 터미널 2 를 `--ros-args -p reliability:=reliable` 로 다시 띄우거나,
           qos_subscriber.py 를 `--ros-args -p reliability:=best_effort` 로 띄운다.

주의: distance_publisher(Reliable) 와 이 노드를 동시에 같은 토픽에 띄우지 않는다.
      구독자가 Reliable 쪽에 붙어버려 "연결 안 됨"이 재현되지 않는다.

QoS 는 발행자 생성 시점에 고정된다. 실행 중 파라미터를 바꿔도 QoS 는 바뀌지 않으므로
reliability 파라미터는 read_only 로 선언한다. 바꾸려면 노드를 다시 띄워야 한다.
"""

import math

import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                        ReliabilityPolicy, qos_profile_sensor_data)
from std_msgs.msg import Float32
from turtlesim.msg import Pose


class QosSensorPublisher(Node):

    def __init__(self):
        super().__init__('qos_sensor_publisher')

        self.declare_parameter(
            'reliability', 'best_effort',
            ParameterDescriptor(description='best_effort | reliable (생성 시 고정)', read_only=True))
        self.declare_parameter('publish_rate', 10.0)
        reliability_str = self.get_parameter('reliability').value
        rate = self.get_parameter('publish_rate').value

        if reliability_str == 'best_effort':
            # rclpy 가 제공하는 센서용 프리셋:
            #   reliability=BEST_EFFORT, durability=VOLATILE, history=KEEP_LAST, depth=5
            pub_qos = qos_profile_sensor_data
        elif reliability_str == 'reliable':
            pub_qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                                  reliability=ReliabilityPolicy.RELIABLE,
                                  durability=DurabilityPolicy.VOLATILE)
        else:
            raise ValueError(
                f'reliability 파라미터는 best_effort 또는 reliable 이어야 합니다: {reliability_str}')

        self._latest_pose = None
        sub_qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                              reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.VOLATILE)
        self._pose_sub = self.create_subscription(Pose, '/turtle1/pose', self._on_pose, sub_qos)
        self._pub = self.create_publisher(Float32, '/turtle_distance', pub_qos)
        self._timer = self.create_timer(1.0 / rate, self._on_timer)

        self.get_logger().info(
            f'qos_sensor_publisher 시작: /turtle_distance reliability={reliability_str}, '
            f'{rate} Hz. `ros2 topic info -v /turtle_distance` 로 확인하세요')

    def _on_pose(self, msg: Pose):
        self._latest_pose = msg

    def _on_timer(self):
        if self._latest_pose is None:
            return
        msg = Float32()
        msg.data = math.hypot(self._latest_pose.x, self._latest_pose.y)
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = QosSensorPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        node.get_logger().info('Ctrl+C — 정상 종료합니다')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
