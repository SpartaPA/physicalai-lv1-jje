// sensors_demo.cpp — 문제 2 데모: 다형성, 소멸 시점, 가상 소멸자, STL(unordered_map/count_if)
#include "sensor.hpp"
#include "lidar.hpp"
#include "imu.hpp"

#include <algorithm>
#include <iostream>
#include <memory>
#include <unordered_map>
#include <vector>

namespace {

struct Record {
    std::string sensor_name;
    double value;
    double distance_to_goal;  // 목표점까지 거리(가정한 시나리오 값)
};

// 1. 다형성 루프 — vector<unique_ptr<Sensor>> 에 담아 read() 를 가상함수 호출로 실행
void PolymorphicReadLoop() {
    std::cout << "=== 1. 다형성 루프 출력 ===\n";
    std::vector<std::unique_ptr<Sensor>> sensors;
    sensors.push_back(std::make_unique<Lidar>());
    sensors.push_back(std::make_unique<Imu>());

    for (int i = 0; i < 3; ++i) {
        for (const auto& s : sensors) {
            std::cout << "  " << s->name() << ".read() = " << s->read() << "\n";
        }
    }
    std::cout << "-- (vector 소멸 시작) --\n";
    // sensors 가 이 함수를 벗어나며 소멸 → 각 unique_ptr 이 Sensor* 를 delete
    // -> 가상 소멸자 덕분에 Lidar/Imu 의 소멸자까지 정상 호출됨 (아래 소멸 로그로 확인)
}

// 2. 가상 소멸자 확인용 — Sensor* 로 명시적으로 delete 해서 어떤 소멸자가 불리는지 관찰
void VirtualDestructorCheck() {
    std::cout << "=== 2. Sensor* 로 delete했을 때 호출되는 소멸자 ===\n";
    Sensor* s = new Lidar();
    std::cout << "  delete 호출 전\n";
    delete s;
    std::cout << "  delete 호출 후\n";
    // virtual 이 있으면: "~Lidar()" 다음 "~Sensor(lidar)" 둘 다 출력됨
    // sensor.hpp 의 virtual 을 지우고 다시 빌드하면: "~Sensor(lidar)" 만 출력됨 (Lidar 소멸자 누락)
}

// 3. 스택 객체 vs 힙 객체의 소멸 시점
void StackVsHeapDestructionTiming() {
    std::cout << "=== 3. 스택 객체와 힙 객체의 소멸 시점 ===\n";

    std::cout << "  [스택] 블록 진입 전\n";
    {
        Lidar stack_lidar;  // 지역 변수 (스택)
        std::cout << "  [스택] 블록 안, read() = " << stack_lidar.read() << "\n";
        std::cout << "  [스택] 블록을 벗어나기 직전\n";
    }  // 여기서 stack_lidar 소멸 (스코프 종료 시점)
    std::cout << "  [스택] 블록을 벗어난 직후 (위에서 소멸자가 이미 호출됐어야 함)\n";

    std::cout << "  [힙] make_unique 생성 전\n";
    auto heap_imu = std::make_unique<Imu>();  // 힙 객체
    std::cout << "  [힙] read() = " << heap_imu->read() << "\n";
    std::cout << "  [힙] reset() 호출 전 (아직 살아있음)\n";
    heap_imu.reset();  // 명시적으로 해제 -> 이 시점에 소멸
    std::cout << "  [힙] reset() 호출 후 (위에서 소멸자가 이미 호출됐어야 함)\n";
}

// 4. unordered_map(센서 이름 -> 최근값) + vector<Record>(측정 로그) + count_if
void MapAndCountIfDemo() {
    std::cout << "=== 4. unordered_map / count_if ===\n";

    Lidar lidar;
    Imu imu;

    std::unordered_map<std::string, double> latest;         // 센서 이름 -> 최근 측정값
    std::vector<Record> log;                                 // 측정 로그

    // 목표점까지 거리가 점점 줄어드는 상황을 가정 (3.0 에서 0.3씩 감소, 0 밑으로는 내려가지 않음)
    for (int i = 0; i < 11; ++i) {
        double lidar_value = lidar.read();
        double imu_value = imu.read();
        double raw_distance = 3.0 - 0.3 * i;
        double distance_to_goal = std::max(0.0, raw_distance);  // 거리는 0보다 작을 수 없음

        latest[lidar.name()] = lidar_value;
        latest[imu.name()] = imu_value;

        log.push_back({lidar.name(), lidar_value, distance_to_goal});
        log.push_back({imu.name(), imu_value, distance_to_goal});
    }

    std::cout << "  최근값(lidar) = " << latest["lidar"] << "\n";
    std::cout << "  최근값(imu)   = " << latest["imu"] << "\n";

    int close_count = static_cast<int>(std::count_if(
        log.begin(), log.end(),
        [](const Record& r) { return r.distance_to_goal <= 0.35; }));

    std::cout << "  목표점까지 거리 0.35 이내 기록 개수 = " << close_count << "개\n";
}

}  // namespace

int main() {
    PolymorphicReadLoop();
    std::cout << "\n";
    VirtualDestructorCheck();
    std::cout << "\n";
    StackVsHeapDestructionTiming();
    std::cout << "\n";
    MapAndCountIfDemo();
    return 0;
}