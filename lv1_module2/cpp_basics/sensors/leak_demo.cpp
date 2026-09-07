// leak_demo.cpp — 누수 재현과 검출 (#ifdef FIXED 로 new/make_unique 전환)
#include <iostream>
#include <memory>
#include <string>

class Sensor {
public:
    explicit Sensor(std::string name) : name_(std::move(name)) {}
    virtual double read() = 0;
    virtual ~Sensor() { std::cout << "  ~Sensor(" << name_ << ")\n"; }
protected:
    std::string name_;
};

class Lidar : public Sensor {
public:
    Lidar() : Sensor("lidar"), tick_(0) {}
    ~Lidar() override { std::cout << "  ~Lidar()\n"; }
    double read() override { return 0.05 * static_cast<double>(tick_++); }
private:
    int tick_;
};

int main() {
#ifdef FIXED
    std::cout << "[수정판] make_unique 사용 — 스코프 끝에서 자동 해제\n";
    for (int i = 0; i < 3; ++i) {
        auto s = std::make_unique<Lidar>();
        s->read();
    }  // 매 반복마다 자동 소멸 — 누수 없음
#else
    std::cout << "[누수판] new 만 하고 delete 안 함\n";
    for (int i = 0; i < 3; ++i) {
        Sensor* s = new Lidar();  // 힙 할당
        s->read();
        // delete s;  <-- 일부러 생략: 누수
    }
#endif
    std::cout << "루프 종료\n";
}