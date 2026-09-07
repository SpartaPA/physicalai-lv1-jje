// imu.cpp — Imu 구현
#include "imu.hpp"
#include <iostream>

Imu::Imu() : Sensor("imu"), tick_(0) {}

Imu::~Imu() { std::cout << "  ~Imu()\n"; }

double Imu::read() {
    // 호출할 때마다 값이 조금씩 증가 (가상의 각속도 측정값)
    return 0.01 * static_cast<double>(tick_++);
}