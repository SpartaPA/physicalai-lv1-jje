// sensor.hpp
#pragma once
#include <iostream>
#include <string>

class Sensor {
public:
    explicit Sensor(std::string name) : name_(std::move(name)) {}

    // 순수 가상 함수 - 센서 값을 읽는 인터페이스, 각 센서 클래스에서 구현해야 함
    virtual double read() = 0;
    // 가상 소멸자 — 센서 객체가 삭제될 때 올바른 소멸자 호출을 보장
    virtual ~Sensor() { std::cout << "  ~Sensor(" << name_ << ")\n"; }
    
    const std::string& name() const { return name_; }

protected:
    std::string name_;
};