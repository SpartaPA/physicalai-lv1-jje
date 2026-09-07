
// main.cpp — Motor 사용 main 함수
#include "motor.hpp"
 
int main() {
    Motor wheel_motor("wheel_motor");
 
    wheel_motor.SetSpeed(120.0);   // 아직 Start() 안 함 → 무시돼야 함
    wheel_motor.PrintStatus();
 
    wheel_motor.SetMaxSpeed(200.0);
    wheel_motor.Start();
    wheel_motor.SetSpeed(120.0);
    wheel_motor.PrintStatus();
 
    wheel_motor.SetSpeed(300.0);   // 상한(200) 넘음 → clamp돼야 함
    wheel_motor.PrintStatus();
 
    wheel_motor.Stop();            // 속도도 0으로 리셋돼야 함
    wheel_motor.PrintStatus();
 
    return 0;
}
