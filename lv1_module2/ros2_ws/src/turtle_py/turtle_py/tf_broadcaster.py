import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from turtlesim.msg import Pose


class TurtleTfBroadcaster(Node):
    """
    /turtle1/pose 를 구독해 world -> turtle1 변환을 계속 발행한다.
    2D 라 z축 회전(yaw=theta)만 있으므로 쿼터니언을 직접 계산한다
    (tf_transformations 같은 추가 패키지 설치 불필요).
    """

    def __init__(self):
        super().__init__('turtle_tf_broadcaster')
        self.br = TransformBroadcaster(self)
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
        self.get_logger().info('turtle_tf_broadcaster 시작: world -> turtle1')

    def on_pose(self, msg: Pose):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = 'turtle1'
        t.transform.translation.x = float(msg.x)
        t.transform.translation.y = float(msg.y)
        t.transform.translation.z = 0.0
        t.transform.rotation.z = math.sin(msg.theta / 2.0)
        t.transform.rotation.w = math.cos(msg.theta / 2.0)
        self.br.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = TurtleTfBroadcaster()
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
