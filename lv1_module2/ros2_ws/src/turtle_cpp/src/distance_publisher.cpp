#include <chrono>
#include <cmath>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32.hpp"
#include "turtlesim/msg/pose.hpp"

using namespace std::chrono_literals;

// 문제 3의 rclpy distance_publisher 와 동일한 설계:
// 구독 콜백은 최신 pose 저장만 하고, 발행은 독립된 타이머 콜백(10Hz)에서 수행한다.
class DistancePublisher : public rclcpp::Node
{
public:
  DistancePublisher()
  : Node("distance_publisher"), has_pose_(false)
  {
    pose_sub_ = this->create_subscription<turtlesim::msg::Pose>(
      "/turtle1/pose", 10,
      std::bind(&DistancePublisher::pose_callback, this, std::placeholders::_1));

    distance_pub_ = this->create_publisher<std_msgs::msg::Float32>("/turtle_distance", 10);

    // 10Hz = 100ms 주기
    timer_ = this->create_wall_timer(
      100ms, std::bind(&DistancePublisher::timer_callback, this));

    RCLCPP_INFO(this->get_logger(), "distance_publisher 시작: publish_rate=10.0 Hz");
  }

private:
  void pose_callback(const turtlesim::msg::Pose::SharedPtr msg)
  {
    latest_pose_ = *msg;
    has_pose_ = true;
  }

  void timer_callback()
  {
    if (!has_pose_) {
      // 아직 /turtle1/pose 를 한 번도 받지 못했으면 발행하지 않는다.
      return;
    }

    auto msg = std_msgs::msg::Float32();
    msg.data = static_cast<float>(std::hypot(latest_pose_.x, latest_pose_.y));
    distance_pub_->publish(msg);
  }

  rclcpp::Subscription<turtlesim::msg::Pose>::SharedPtr pose_sub_;
  rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr distance_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  turtlesim::msg::Pose latest_pose_;
  bool has_pose_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<DistancePublisher>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
