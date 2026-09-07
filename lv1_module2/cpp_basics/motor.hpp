// motor.hpp — Motor 클래스 선언
#pragma once
#include <string>
 
class Motor {
public:
    explicit Motor(std::string name);
 
    void Start();                    // 구동 시작
    void Stop();                     // 구동 정지 (속도도 0으로 리셋)
 
    void SetMaxSpeed(double max_rpm);  // 속도 상한 설정
    void SetSpeed(double rpm);         // 목표 속도 설정 (Stop 상태면 무시, 상한으로 clamp)
    double GetSpeed() const;
    bool IsRunning() const;
 
    void PrintStatus() const;
 
private:
    std::string name_;
    double speed_ = 0.0;
    double max_speed_ = 1000.0;   // 기본 상한 [rpm]
    bool running_ = false;
};
 