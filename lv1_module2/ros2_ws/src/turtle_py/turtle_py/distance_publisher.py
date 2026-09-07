import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from turtlesim.msg import Pose

from turtle_py.utils import calc_distance


class DistancePublisher(Node):
    """
    /turtle1/pose 를 구독해 최신 위치만 저장하고,
    독립된 10Hz 타이머에서 원점(0,0)까지의 거리를 계산해 /turtle_distance 로 발행한다.

    구독 콜백과 발행(타이머)을 분리해두는 이유:
    turtlesim_node 가 죽어도 이 노드는 마지막으로 받은 pose 값으로 계속 발행을 이어간다.
    -> ros2 topic hz /turtle_distance 만으로는 상류 데이터가 살아있는지 알 수 없다.
       (문제 10 진단 시나리오와 연결됨)
    """

    def __init__(self):
        super().__init__('distance_publisher')

        self.declare_parameter('publish_rate', 10.0)
        publish_rate = self.get_parameter('publish_rate').value
        if publish_rate <= 0:
            self.get_logger().warn(
                f'publish_rate 는 0보다 커야 합니다 (입력값: {publish_rate}). '
                f'기본값 10.0 Hz 로 대체합니다.'
            )
            publish_rate = 10.0
        self.publish_rate = publish_rate

        self.latest_pose = None

        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.pose_callback, 10
        )
        self.distance_pub = self.create_publisher(Float32, '/turtle_distance', 10)

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            f'distance_publisher 시작: publish_rate={self.publish_rate} Hz'
        )

    def pose_callback(self, msg: Pose):
        # 콜백에서는 최신 pose 저장만 하고, 실제 발행은 timer_callback 에서 수행한다.
        self.latest_pose = msg

    def timer_callback(self):
        if self.latest_pose is None:
            # 아직 /turtle1/pose 를 한 번도 받지 못했으면 발행하지 않는다.
            return

        distance = calc_distance(self.latest_pose.x, self.latest_pose.y, 0.0, 0.0)

        msg = Float32()
        msg.data = distance
        self.distance_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DistancePublisher()
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
