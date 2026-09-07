import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'turtle_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='조은',
    maintainer_email='jje5976@gmail.com',
    description='turtlesim distance publisher/subscriber, square driver, '
                 'service/action clients-servers, custom-interface waypoints, QoS demos',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'distance_publisher = turtle_py.distance_publisher:main',
            'distance_warner = turtle_py.distance_warner:main',
            'square_driver = turtle_py.square_driver:main',
            'tf_broadcaster = turtle_py.tf_broadcaster:main',
            'waypoint_markers = turtle_py.waypoint_markers:main',
            # 문제 5
            'builtin_service_client = turtle_py.builtin_service_client:main',
            'rotate_absolute_client = turtle_py.rotate_absolute_client:main',
            # 문제 6
            'polygon_action_server = turtle_py.polygon_action_server:main',
            'waypoint_publisher = turtle_py.waypoint_publisher:main',
            # 문제 7
            'qos_sensor_publisher = turtle_py.qos_sensor_publisher:main',
            'qos_subscriber = turtle_py.qos_subscriber:main'
        ]
    }
)
