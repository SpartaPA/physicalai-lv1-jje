// imu.hpp — Imu 센서
#pragma once
#include "sensor.hpp"

class Imu : public Sensor {
public:
    Imu();
    ~Imu() override;

    double read() override;

private:
    int tick_;
};