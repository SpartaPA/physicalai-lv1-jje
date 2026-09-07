#!/usr/bin/env python3
"""rotate_absolute_client — 문제 5: turtlesim 내장 액션 RotateAbsolute 클라이언트.

액션 정의 (ros2 interface show turtlesim/action/RotateAbsolute)
  float32 theta      ← goal     : 목표 절대 각도 [rad]
  ---
  float32 delta      ← result   : 실제로 회전한 양
  ---
  float32 remaining  ← feedback : 남은 각도

사용법
  ros2 run turtle_py rotate_absolute_client --ros-args -p theta:=3.0
  ros2 run turtle_py rotate_absolute_client --ros-args -p theta:=3.0 -p cancel_after:=1.0
      → 1.0초 뒤 cancel_goal_async() 를 보내고, 그 시점의 /turtle1/pose theta 를 기록한다.
        (파라미터로 받는 이유: --ros-args 뒤에 오는 인자는 ROS2 파라미터 규칙을 따르는 편이
        launch 파일/다른 노드와 조합하기 쉽다. argparse 로 직접 받아도 동작은 동일하다.)

액션 클라이언트의 3단계 (모두 Future 기반 비동기)
  1. send_goal_async(goal, feedback_callback=...)  → Future[ClientGoalHandle]  (수락/거절)
  2. goal_handle.get_result_async()                → Future[result + status]   (완료)
  3. goal_handle.cancel_goal_async()               → Future[CancelGoal.Response]

[주의] 콜백 안에서 rclpy.shutdown() 을 직접 부르지 않는다.
  콜백은 executor 가 실행 중이므로, 그 안에서 컨텍스트를 내리면 executor 가 정리 중 예외를
  내거나 "context already shutdown" 이 발생한다. 콜백은 self.done 플래그만 세우고,
  main() 의 spin_once 루프가 그 플래그를 보고 빠져나온 뒤 정상 순서(destroy_node → shutdown)로
  종료한다.
"""

import math

import rclpy
from action_msgs.msg import GoalStatus
from action_msgs.srv import CancelGoal
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                        ReliabilityPolicy)
from turtlesim.action import RotateAbsolute
from turtlesim.msg import Pose

STATUS_NAME = {
    GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
    GoalStatus.STATUS_CANCELED: 'CANCELED',
    GoalStatus.STATUS_ABORTED: 'ABORTED',
}


class RotateAbsoluteClient(Node):

    def __init__(self):
        super().__init__('rotate_absolute_client')

        self.declare_parameter('theta', math.pi / 2)          # 목표 절대 각도 [rad]
        self.declare_parameter('cancel_after', -1.0)           # 초. 음수면 취소하지 않음
        self._target = float(self.get_parameter('theta').value)
        cancel_after = float(self.get_parameter('cancel_after').value)
        self._cancel_after = cancel_after if cancel_after >= 0.0 else None

        self._client = ActionClient(self, RotateAbsolute, '/turtle1/rotate_absolute')

        # 취소 시점의 각도를 기록하기 위해 /turtle1/pose 도 구독한다.
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                          reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.VOLATILE)
        self._pose_sub = self.create_subscription(Pose, '/turtle1/pose', self._on_pose, qos)
        self._latest_theta = None

        self._goal_handle = None
        self._cancel_timer = None
        self.done = False   # main 루프 종료 플래그 (콜백은 이것만 세운다)

    def _on_pose(self, msg: Pose):
        self._latest_theta = msg.theta

    def send_goal(self):
        if not self._client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('액션 서버 /turtle1/rotate_absolute 가 없습니다 (turtlesim 실행 중?)')
            self.done = True
            return
        goal = RotateAbsolute.Goal()
        goal.theta = float(self._target)
        self.get_logger().info(
            f'goal 전송: theta = {goal.theta:.3f} rad (현재 theta = {self._latest_theta})')
        send_future = self._client.send_goal_async(goal, feedback_callback=self._on_feedback)
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('goal 이 거절되었습니다')
            self.done = True
            return
        self.get_logger().info('goal 수락됨 — 피드백 대기')
        self._goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_result)

        if self._cancel_after is not None:
            self._cancel_timer = self.create_timer(self._cancel_after, self._on_cancel_timer)

    def _on_feedback(self, feedback_msg):
        remaining = feedback_msg.feedback.remaining
        # turtlesim 은 매 주기(약 62.5 Hz) 피드백을 보내므로 0.25초에 한 번만 로그를 찍는다.
        self.get_logger().info(f'피드백: remaining = {remaining:+.3f} rad', throttle_duration_sec=0.25)

    def _on_cancel_timer(self):
        self._cancel_timer.cancel()               # 한 번만 실행되도록
        theta_at_cancel = self._latest_theta       # 취소 "요청 시점" 의 각도 기록
        self.get_logger().warn(f'취소 요청 전송 (요청 시점 theta = {theta_at_cancel:.3f} rad)')
        cancel_future = self._goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(lambda f: self._on_cancel_response(f, theta_at_cancel))

    def _on_cancel_response(self, future, theta_at_cancel):
        resp = future.result()
        if resp.return_code == CancelGoal.Response.ERROR_NONE and len(resp.goals_canceling) > 0:
            self.get_logger().warn(
                f'취소 수락됨 (서버가 중단 처리 중). 취소 시점 theta = {theta_at_cancel:.3f} rad')
        else:
            self.get_logger().error(
                f'취소 거절: return_code={resp.return_code} (이미 끝난 goal 이면 ERROR_GOAL_TERMINATED=3)')

    def _on_result(self, future):
        wrapped = future.result()
        status = wrapped.status
        result = wrapped.result
        name = STATUS_NAME.get(status, str(status))
        self.get_logger().info(
            f'결과 수신: status={name}, delta={result.delta:+.3f} rad, 현재 theta = {self._latest_theta}')
        self.done = True


def main(args=None):
    rclpy.init(args=args)
    node = RotateAbsoluteClient()
    try:
        node.send_goal()
        # spin() 대신 spin_once 루프: done 플래그가 서면 빠져나와 정상 종료한다.
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        node.get_logger().info('Ctrl+C — 중단합니다')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
