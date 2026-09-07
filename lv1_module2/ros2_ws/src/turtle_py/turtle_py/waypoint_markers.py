import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker


class WaypointMarkers(Node):
    """
    경유점(3개 이상)을 /waypoint_markers 토픽에
    visualization_msgs/Marker(POINTS, frame_id='world')로 주기 발행한다.
    RViz2 에서 Fixed Frame 을 world 로 두고 이 토픽을 Marker 로 추가하면 보인다.

    경유점은 'waypoints' 파라미터("x1,y1,x2,y2,..." 형태의 콤마 구분 문자열)로 받는다.
    (실수 배열(DOUBLE_ARRAY) 타입 파라미터는 커맨드라인에서 빈 배열('[]')을 넘기면
    원소 타입을 추론할 수 없어 ParameterUninitializedException 이 발생하는 rclpy의
    알려진 제약이 있어, 문자열로 받아 직접 파싱하는 방식을 사용한다.)
    빈 문자열이 들어오면 크래시 없이 경고 로그만 남기고 기본 경유점 4개로 대체한다.
    예: ros2 run turtle_py waypoint_markers --ros-args -p waypoints:='""'
    """

    DEFAULT_WAYPOINTS = '2.0,2.0,8.0,2.0,8.0,8.0,2.0,8.0'

    def __init__(self):
        super().__init__('waypoint_markers')

        self.declare_parameter('waypoints', self.DEFAULT_WAYPOINTS)
        raw = self.get_parameter('waypoints').value.strip()

        if not raw:
            self.get_logger().warn(
                'waypoints 파라미터가 비어 있습니다. 기본 경유점으로 대체합니다.'
            )
            raw = self.DEFAULT_WAYPOINTS

        try:
            flat = [float(v) for v in raw.split(',')]
        except ValueError:
            self.get_logger().error(
                f"waypoints 파라미터 형식이 잘못됐습니다: '{raw}'. 기본 경유점으로 대체합니다."
            )
            flat = [float(v) for v in self.DEFAULT_WAYPOINTS.split(',')]

        if len(flat) % 2 != 0:
            self.get_logger().error(
                f'waypoints 파라미터 길이가 홀수입니다 (길이: {len(flat)}). '
                '마지막 값을 무시합니다.'
            )
            flat = flat[:-1]

        self.waypoints = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]

        self.marker_pub = self.create_publisher(Marker, '/waypoint_markers', 10)
        self.timer = self.create_timer(1.0, self.publish_markers)

        self.get_logger().info(f'waypoint_markers 시작: 경유점 {len(self.waypoints)}개')

    def publish_markers(self):
        if not self.waypoints:
            self.get_logger().warn('waypoint 목록이 비어 있습니다')
            return

        marker = Marker()
        marker.header.frame_id = 'world'
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = 'waypoints'
        marker.id = 0
        marker.type = Marker.POINTS
        marker.action = Marker.ADD
        marker.scale.x = 0.3
        marker.scale.y = 0.3
        marker.color.a = 1.0
        marker.color.r = 1.0
        marker.color.g = 0.0
        marker.color.b = 0.0

        for x, y in self.waypoints:
            p = Point()
            p.x = x
            p.y = y
            p.z = 0.0
            marker.points.append(p)

        self.marker_pub.publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = WaypointMarkers()
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
