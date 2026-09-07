#!/usr/bin/env python3
"""qos_subscriber — 문제 7: QoS 를 파라미터로 조립하는 실험용 구독자.

파라미터
  topic          : 구독할 토픽 (기본 turtle_distance). /waypoints 실험은 topic:=waypoints msg_type:=WaypointList
  msg_type       : Float32 | WaypointList
  reliability    : reliable | best_effort
  durability     : volatile | transient_local
  history_depth  : 정수 (기본 10). 누락 실험은 1
  callback_delay : 초 (기본 0.0). 콜백 안에서 일부러 time.sleep 하는 시간 → "처리가 발행보다 느린" 상황 재현

실험 예
  # (1) 비호환 재현: 발행자 best_effort(qos_sensor_publisher) + 이 구독자 reliable(기본)
  ros2 run turtle_py qos_subscriber
  # (2) 고치기: 구독자를 best_effort 로
  ros2 run turtle_py qos_subscriber --ros-args -p reliability:=best_effort
  # (3) depth=1 + 콜백 지연 0.5s: 10Hz 발행 중 초당 2개만 처리되고 나머지는 큐에서 밀려 사라짐
  ros2 run turtle_py qos_subscriber --ros-args -p history_depth:=1 -p callback_delay:=0.5
  # (4) 늦게 뜬 구독자가 /waypoints 를 받는가 (transient_local)
  ros2 run turtle_py qos_subscriber --ros-args -p topic:=waypoints -p msg_type:=WaypointList -p durability:=transient_local

진단 방법: ros2 topic info -v <토픽>
  출력의 Publishers: / Subscriptions: 항목마다 QoS profile 이 붙어 나온다.
  "구독자 수는 1인데 메시지가 안 온다"면 거의 항상 QoS 비호환이다.

호환 규칙 (요청-제공 모델: 구독자가 "요청", 발행자가 "제공". 제공이 요청보다 같거나 강해야 연결)
  Reliability : 발행 RELIABLE   + 구독 RELIABLE     → OK
                발행 RELIABLE   + 구독 BEST_EFFORT  → OK  (구독자가 덜 요구)
                발행 BEST_EFFORT+ 구독 BEST_EFFORT  → OK
                발행 BEST_EFFORT+ 구독 RELIABLE     → 연결 안 됨 ← 문제 7 재현 대상
  Durability  : 발행 TRANSIENT_LOCAL + 구독 VOLATILE         → OK (늦게 뜬 구독자는 과거 메시지 못 받음)
                발행 TRANSIENT_LOCAL + 구독 TRANSIENT_LOCAL  → OK (과거 메시지 받음)
                발행 VOLATILE        + 구독 TRANSIENT_LOCAL  → 연결 안 됨
  History/depth 는 호환성에 영향이 없고, 양쪽 각자의 큐 크기만 정한다.
"""

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                        ReliabilityPolicy)
from std_msgs.msg import Float32

try:
    # Humble: rclpy.qos_event (Iron 이후 rclpy.event_handler 로 이동)
    from rclpy.qos_event import SubscriptionEventCallbacks
except ImportError:      # pragma: no cover
    SubscriptionEventCallbacks = None


class QosSubscriber(Node):

    def __init__(self):
        super().__init__('qos_subscriber')

        self.declare_parameter('topic', 'turtle_distance')
        self.declare_parameter('msg_type', 'Float32')
        self.declare_parameter('reliability', 'reliable')
        self.declare_parameter('durability', 'volatile')
        self.declare_parameter('history_depth', 10)
        self.declare_parameter('callback_delay', 0.0)

        topic = self.get_parameter('topic').value
        msg_type = self.get_parameter('msg_type').value
        reliability_str = self.get_parameter('reliability').value
        durability_str = self.get_parameter('durability').value
        depth = self.get_parameter('history_depth').value
        self._delay = self.get_parameter('callback_delay').value

        reliability = {
            'reliable': ReliabilityPolicy.RELIABLE,
            'best_effort': ReliabilityPolicy.BEST_EFFORT,
        }.get(reliability_str)
        durability = {
            'volatile': DurabilityPolicy.VOLATILE,
            'transient_local': DurabilityPolicy.TRANSIENT_LOCAL,
        }.get(durability_str)
        if reliability is None or durability is None or depth < 1:
            raise ValueError(
                'reliability=reliable|best_effort, durability=volatile|transient_local, '
                f'history_depth>=1 이어야 합니다 (받은 값: {reliability_str}, {durability_str}, {depth})')

        if msg_type == 'Float32':
            msg_cls = Float32
        elif msg_type == 'WaypointList':
            from turtle_interfaces.msg import WaypointList   # 문제 6 인터페이스
            msg_cls = WaypointList
        else:
            raise ValueError(f'msg_type 은 Float32 또는 WaypointList: {msg_type}')

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=depth,
            reliability=reliability,
            durability=durability,
        )

        # 일부 RMW 는 incompatible_qos 이벤트를 지원하지 않아 생성 자체가 예외를 낼 수 있으므로,
        # 실패하면 이벤트 없이 다시 만든다.
        self._sub = None
        if SubscriptionEventCallbacks is not None:
            try:
                events = SubscriptionEventCallbacks(incompatible_qos=self._on_incompatible_qos)
                self._sub = self.create_subscription(msg_cls, topic, self._on_msg, qos,
                                                      event_callbacks=events)
            except Exception as e:   # noqa: BLE001 — UnsupportedEventTypeError 등
                self.get_logger().warn(f'incompatible_qos 이벤트 미지원 ({e}) — 이벤트 없이 구독합니다')
        if self._sub is None:
            self._sub = self.create_subscription(msg_cls, topic, self._on_msg, qos)

        self._count_total = 0
        self._count_window = 0
        self._stats_timer = self.create_timer(2.0, self._on_stats)

        self.get_logger().info(
            f'qos_subscriber 시작: topic={topic} type={msg_type} '
            f'reliability={reliability_str} durability={durability_str} depth={depth} '
            f'callback_delay={self._delay}s')

    def _on_msg(self, msg):
        self._count_total += 1
        self._count_window += 1
        if hasattr(msg, 'waypoints'):
            labels = [wp.label for wp in msg.waypoints]
            self.get_logger().info(
                f'#{self._count_total} WaypointList: {len(msg.waypoints)}개 {labels} '
                f'frame_id={msg.header.frame_id}')
        else:
            self.get_logger().info(f'#{self._count_total} 수신: {msg.data:.3f}')

        if self._delay > 0.0:
            # 일부러 콜백을 붙잡는다. SingleThreadedExecutor 라 이 동안 다른 콜백이 못 돈다.
            # 발행자는 계속 10Hz 로 쏘고, 우리 쪽 큐(depth)에 쌓이다가 depth 를 넘는 순간
            # 가장 오래된 것부터 버려진다(KEEP_LAST). depth=1 이면 항상 최신 1개만 남는다.
            time.sleep(self._delay)

    def _on_stats(self):
        self.get_logger().info(
            f'[통계] 지난 2초 처리 {self._count_window}개 (누적 {self._count_total}개)'
            + ('' if self._count_window else ' — 0개라면 QoS 비호환이나 발행자 부재를 의심'))
        self._count_window = 0

    def _on_incompatible_qos(self, event):
        self.get_logger().error(
            f'QoS 비호환 이벤트! total_count={event.total_count}, last_policy_kind={event.last_policy_kind} '
            '→ `ros2 topic info -v` 로 발행자/구독자 QoS 를 비교하세요')


def main(args=None):
    rclpy.init(args=args)
    node = QosSubscriber()
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
