import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_srvs.srv import SetBool, Trigger
from turtlesim.msg import Pose
from turtlesim.srv import TeleportAbsolute

LINEAR_SPEED = 1.0          # m/s, 전진 속도(고정)
ANGULAR_SPEED = math.pi / 4  # rad/s, 회전 속도(고정) -> 90도 회전에 2초 소요


class SquareDriver(Node):
    """
    /turtle1/cmd_vel 에 Twist 를 발행해 정사각형 궤적으로 4회(전진 -> 제자리 90도 회전) 반복한다.
    한 변의 길이는 side_length 파라미터로 조절하며,
    전진 시간 = side_length / LINEAR_SPEED 로 계산한다.
    타이머 기반 상태 머신으로 구현해 스핀을 막지 않는다(time.sleep 미사용).

    [문제 5] 이 노드(문제 3의 주행 노드)에 자체 서비스 서버를 추가한다.
      /enable_driving  std_srvs/srv/SetBool   data=false 면 cmd_vel 발행을 즉시 멈춤(일시정지)
                                              data=true  면 멈췄던 지점부터 다시 진행
      /save_home       std_srvs/srv/Trigger   현재 /turtle1/pose 를 "홈" 으로 저장
      /go_home         std_srvs/srv/Trigger   저장한 홈으로 순간이동(비동기 — 콜백 안에서 동기 대기 금지)
    """

    def __init__(self):
        super().__init__('square_driver')

        self.declare_parameter('side_length', 2.0)
        side_length = self.get_parameter('side_length').value
        if side_length <= 0:
            self.get_logger().error(
                f'side_length 는 0보다 커야 합니다 (입력값: {side_length}). '
                f'기본값 2.0 으로 대체합니다.'
            )
            side_length = 2.0
        self.side_length = side_length

        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        self.forward_duration = self.side_length / LINEAR_SPEED
        self.turn_duration = (math.pi / 2) / ANGULAR_SPEED

        self.state = 'FORWARD'
        self.state_start_time = self.get_clock().now()
        self.completed_sides = 0
        self.total_sides = 4
        self.done = False

        # ---- 문제 5: 주행 on/off ----
        self.declare_parameter('start_enabled', True)
        self._enabled = bool(self.get_parameter('start_enabled').value)
        self._pause_started = None   # 일시정지를 시작한 시각 (엘랩스 타임 보정용)

        # ---- 문제 5: 홈 저장/복귀 ----
        self._latest_pose = None
        self._home = None            # (x, y, theta) — save_home 이 채움
        self._pose_sub = self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 10)
        self._teleport_cli = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')

        self._enable_srv = self.create_service(SetBool, '/enable_driving', self._on_enable_driving)
        self._save_srv = self.create_service(Trigger, '/save_home', self._on_save_home)
        self._go_home_srv = self.create_service(Trigger, '/go_home', self._on_go_home)

        self.timer = self.create_timer(0.01, self.control_loop)

        self.get_logger().info(
            f'square_driver 시작: side_length={self.side_length:.2f} m, '
            f'forward_duration={self.forward_duration:.2f}s, '
            f'turn_duration={self.turn_duration:.2f}s, start_enabled={self._enabled}'
        )

    def control_loop(self):
        if self.done:
            return

        # ---- 문제 5: 꺼져 있으면 정지 상태만 유지하고 상태 머신은 진행시키지 않는다 ----
        if not self._enabled:
            self.cmd_pub.publish(Twist())  # 0 속도 = 정지
            return

        now = self.get_clock().now()
        elapsed = (now - self.state_start_time).nanoseconds / 1e9
        twist = Twist()

        if self.state == 'FORWARD':
            if elapsed < self.forward_duration:
                twist.linear.x = LINEAR_SPEED
            else:
                self.state = 'TURN'
                self.state_start_time = now
                twist.linear.x = 0.0

        elif self.state == 'TURN':
            if elapsed < self.turn_duration:
                twist.angular.z = ANGULAR_SPEED
            else:
                self.completed_sides += 1
                if self.completed_sides >= self.total_sides:
                    self.done = True
                    self.cmd_pub.publish(Twist())  # 정지
                    self.get_logger().info('square_driver: 정사각형 주행 완료')
                    return
                self.state = 'FORWARD'
                self.state_start_time = now
                twist.angular.z = 0.0

        self.cmd_pub.publish(twist)

    # ------------------------------------------------------------ 문제 5 콜백
    def _on_pose(self, msg: Pose):
        self._latest_pose = msg

    def _on_enable_driving(self, request: SetBool.Request, response: SetBool.Response):
        now = self.get_clock().now()
        if request.data and not self._enabled:
            # 다시 켤 때: 일시정지된 동안 흐른 시간만큼 state_start_time 을 뒤로 밀어
            # elapsed 계산이 정지 구간을 포함하지 않도록 보정한다.
            if self._pause_started is not None:
                paused_for = now - self._pause_started
                self.state_start_time = self.state_start_time + paused_for
                self._pause_started = None
        elif not request.data and self._enabled:
            self._pause_started = now
            self.cmd_pub.publish(Twist())  # 끄는 즉시 한 번 더 정지 명령

        self._enabled = request.data
        response.success = True
        response.message = f'driving {"enabled" if self._enabled else "disabled"}'
        self.get_logger().info(f'/enable_driving ← data={request.data} → {response.message}')
        return response

    def _on_save_home(self, request: Trigger.Request, response: Trigger.Response):
        if self._latest_pose is None:
            response.success = False
            response.message = '아직 /turtle1/pose 를 받지 못해 홈을 저장할 수 없습니다'
        else:
            p = self._latest_pose
            self._home = (p.x, p.y, p.theta)
            response.success = True
            response.message = f'home saved: x={p.x:.2f} y={p.y:.2f} theta={p.theta:.2f}'
        self.get_logger().info(f'/save_home → {response.message}')
        return response

    def _on_go_home(self, request: Trigger.Request, response: Trigger.Response):
        """올바른 비동기 패턴: 요청만 보내고 즉시 응답, 실제 결과는 done 콜백에서 처리한다.

        [문제 5 답안 템플릿] 만약 여기서 spin_until_future_complete(self, future) 나
        self._teleport_cli.call(req) 처럼 "동기로" 응답을 기다리면 데드락이 난다.
        이유(executor 관점, 3줄):
          1) 지금 이 콜백은 executor 의 유일한 실행 손(SingleThreadedExecutor) 안에서 돌고 있다.
          2) teleport_absolute 의 응답도 같은 executor 가 처리해야 완료된다.
          3) 그 손은 이 콜백이 끝나길 기다리고, 이 콜백은 응답이 오길 기다리므로 서로 물려 멈춘다.
        그래서 call_async() 로 요청만 보내고 add_done_callback 으로 "응답이 오면 할 일"만 등록한 뒤
        서비스 콜백은 바로 return 한다.
        """
        if self._home is None:
            response.success = False
            response.message = '저장된 홈이 없습니다. 먼저 /save_home 을 호출하세요'
            return response
        if not self._teleport_cli.service_is_ready():
            response.success = False
            response.message = '/turtle1/teleport_absolute 서버가 없습니다 (turtlesim 실행 중?)'
            return response

        req = TeleportAbsolute.Request()
        req.x, req.y, req.theta = self._home
        future = self._teleport_cli.call_async(req)        # 여기서 블록되지 않음
        future.add_done_callback(self._on_teleport_done)   # 응답 도착 시 executor 가 나중에 호출

        response.success = True
        response.message = f'teleport 요청 전송: ({req.x:.2f}, {req.y:.2f}, {req.theta:.2f}) — 결과는 로그 참조'
        self.get_logger().info(f'/go_home → {response.message}')
        return response

    def _on_teleport_done(self, future):
        if future.exception() is not None:
            self.get_logger().error(f'teleport 실패: {future.exception()}')
        else:
            self.get_logger().info('teleport 완료 — 홈으로 이동했습니다')


def main(args=None):
    rclpy.init(args=args)
    node = SquareDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
