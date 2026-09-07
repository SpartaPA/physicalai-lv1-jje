// lidar.hpp — Lidar 센서 (Sensor 상속)
#pragma once
#include "sensor.hpp"

class Lidar : public Sensor {
public:
    Lidar();
    ~Lidar() override;

    double read() override;

private:
    int tick_;
};