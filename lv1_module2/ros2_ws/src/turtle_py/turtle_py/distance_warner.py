import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class DistanceWarner(Node):
    """
    /turtle_distance 를 구독해 warn_distance 파라미터를 초과하면 경고 로그를 남긴다.
    노드 이름은 채점 규격상 반드시 'distance_warner' 를 사용한다.
    """

    def __init__(self):
        super().__init__('distance_warner')

        self.declare_parameter('warn_distance', 2.5)
        self.warn_distance = self.get_parameter('warn_distance').value

        self.sub = self.create_subscription(
            Float32, '/turtle_distance', self.distance_callback, 10
        )

        self.get_logger().info(
            f'distance_warner 시작: warn_distance={self.warn_distance} m'
        )

    def distance_callback(self, msg: Float32):
        if msg.data > self.warn_distance:
            self.get_logger().warn(
                f'거북이가 원점에서 {msg.data:.2f} m 떨어짐 '
                f'(경고 기준 {self.warn_distance:.2f} m 초과)'
            )


def main(args=None):
    rclpy.init(args=args)
    node = DistanceWarner()
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
