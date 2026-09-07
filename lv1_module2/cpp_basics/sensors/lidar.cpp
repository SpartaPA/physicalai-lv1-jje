// lidar.cpp — Lidar 구현
#include "lidar.hpp"
#include <iostream>

Lidar::Lidar() : Sensor("lidar"), tick_(0) {}

Lidar::~Lidar() { std::cout << "  ~Lidar()\n"; }

double Lidar::read() {
    // 호출할 때마다 값이 조금씩 증가 (가상의 거리 측정값)
    return 0.05 * static_cast<double>(tick_++);
}