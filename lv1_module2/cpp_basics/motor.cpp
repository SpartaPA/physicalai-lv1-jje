// motor.cpp — Motor 클래스 구현
#include "motor.hpp"
#include <algorithm>
#include <iostream>

Motor::Motor(std::string name) : name_(std::move(name)) {}

void Motor::Start() { running_ = true; }

void Motor::Stop() {
    running_ = false;
    speed_ = 0.0;
}

void Motor::SetMaxSpeed(double max_rpm) { max_speed_ = max_rpm; }

void Motor::SetSpeed(double rpm) {
    if (!running_) {
        std::cout << "[" << name_ << "] Stop() 상태라 속도 설정을 무시함\n";
        return;
    }
    speed_ = std::clamp(rpm, 0.0, max_speed_);
}

double Motor::GetSpeed() const { return speed_; }

bool Motor::IsRunning() const { return running_; }

void Motor::PrintStatus() const {
    std::cout << "[" << name_ << "] running=" << (running_ ? "true" : "false")
               << ", speed=" << speed_ << " rpm (max=" << max_speed_ << ")\n";
}