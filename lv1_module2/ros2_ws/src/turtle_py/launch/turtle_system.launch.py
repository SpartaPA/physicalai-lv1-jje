"""turtle_system.launch.py — 문제 9: 다중 노드 기동 + 파라미터 주입 + 네임스페이스.

기동하는 노드 (ros2 node list 에 네 개가 보여야 한다)
  /turtlesim                turtlesim_node
  /distance_publisher       문제 3의 상태(원점 거리) 발행자
  /distance_warner          문제 3의 경고 구독자
  /polygon_action_server    문제 6의 DrawPolygon 액션 서버

launch 인자
  spawn_second:=true   /spawn 으로 turtle2 를 만들고, 네임스페이스 turtle2 로 두 번째 발행자를 하나 더 띄운다.
  params_file:=<경로>  기본은 share/turtle_py/config/params.yaml

실행
  ros2 launch turtle_py turtle_system.launch.py
  ros2 launch turtle_py turtle_system.launch.py spawn_second:=true

파라미터 주입 방법: config/params.yaml 을 parameters=[params_file] 로 넘긴다.
  YAML 은 share/ 에 "설치된" 파일을 읽는다. colcon build --symlink-install 이면 src/ 의 YAML 이
  심볼릭 링크로 연결돼 있어 수정이 재빌드 없이 바로 반영된다.

네임스페이스와 토픽 이름 — 왜 절대 이름('/turtle1/pose')을 쓰면 네임스페이스가 안 먹는가
  ROS2 는 코드에 적힌 이름을 다음 규칙으로 "완전한 이름(FQN)"으로 바꾼다.
    상대 이름 'pose'          → <namespace>/pose          예) ns=turtle2 → /turtle2/pose
    절대 이름 '/turtle1/pose' → /turtle1/pose             (namespace 무시!)
  즉 '/' 로 시작하는 이름은 이미 완전한 이름이라 launch 의 namespace= 가 손댈 곳이 없다.
  이 프로젝트의 distance_publisher.py 는 '/turtle1/pose' 와 '/turtle_distance' 를 절대 이름으로
  쓰므로, namespace='turtle2' 만 주면 아무 것도 안 바뀐다. 그래서 remappings 로 강제로 바꾼다.
    ('/turtle1/pose', '/turtle2/pose')      turtle2 의 pose 를 구독하도록
    ('/turtle_distance', '/turtle2/turtle_distance')  발행 토픽에 네임스페이스를 붙여줌
  (참고: turtle2 의 pose 는 /spawn 이 만든 실제 토픽 이름이 /turtle2/pose 이므로 이렇게 remap 한다.)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('turtle_py')
    default_params = os.path.join(pkg_share, 'config', 'params.yaml')

    spawn_second_arg = DeclareLaunchArgument(
        'spawn_second', default_value='false',
        description='true 면 turtle2 를 spawn 하고 네임스페이스 turtle2 로 발행자를 하나 더 띄움')
    params_file_arg = DeclareLaunchArgument(
        'params_file', default_value=default_params,
        description='노드 파라미터 YAML 경로')

    spawn_second = LaunchConfiguration('spawn_second')
    params_file = LaunchConfiguration('params_file')

    turtlesim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim',
        output='screen',
    )

    distance_publisher = Node(
        package='turtle_py',
        executable='distance_publisher',
        name='distance_publisher',
        parameters=[params_file],
        output='screen',
    )
    distance_warner = Node(
        package='turtle_py',
        executable='distance_warner',
        name='distance_warner',
        parameters=[params_file],
        output='screen',
    )
    polygon_action_server = Node(
        package='turtle_py',
        executable='polygon_action_server',
        name='polygon_action_server',
        parameters=[params_file],
        output='screen',
    )

    # ---------- spawn_second ----------
    # turtlesim 이 뜨고 서비스가 준비될 시간을 주려고 2초 뒤에 /spawn 을 호출한다.
    spawn_turtle2 = TimerAction(
        period=2.0,
        actions=[ExecuteProcess(
            cmd=['ros2', 'service', 'call', '/spawn', 'turtlesim/srv/Spawn',
                 "{x: 2.0, y: 2.0, theta: 0.0, name: 'turtle2'}"],
            output='screen',
        )],
        condition=IfCondition(spawn_second),
    )
    second_publisher = Node(
        package='turtle_py',
        executable='distance_publisher',
        name='distance_publisher',        # 이름은 같아도 네임스페이스가 달라 /turtle2/distance_publisher 가 됨
        namespace='turtle2',
        remappings=[
            ('/turtle1/pose', '/turtle2/pose'),
            ('/turtle_distance', '/turtle2/turtle_distance'),
        ],
        parameters=[params_file],
        output='screen',
        condition=IfCondition(spawn_second),
    )

    return LaunchDescription([
        spawn_second_arg,
        params_file_arg,
        LogInfo(msg=['params_file = ', params_file]),
        turtlesim,
        distance_publisher,
        distance_warner,
        polygon_action_server,
        spawn_turtle2,
        second_publisher,
    ])
