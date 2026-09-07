// stop_distance.cpp - 로봇의 제동(정지) 거리 계산
// 물리: 바퀴와 바닥 사이 마찰이 유일한 제동력이라고 보면
//   
//  감속도 a = mu * g   (mu: 마찰계수, g: 중력가속도)
//  운동에너지 (1/2)m v^2 이 마찰일 (mu m g d) 로 모두 소모되어 정지하므로
//  d = v^2 / (2 * mu * g)
//
// 빌드: g++ -Wall -std=c++17 stop_distance.cpp -o stop_distance
// 실행: ./stop_distance <속도[m/s]> <마찰계수>
// 인자를 안 주면 값을 직접 입력받음

# include <iostream>
# include <limits>
# include <string>
# include <stdexcept>

// namespace: 이 프로그램에서만 쓰이는 상수와 함수들을 감싸는 익명 네임스페이스 (다른 파일에서 접근 불가)
namespace {
    // 중력가속도 상수 [m/s^2]
    // constexpr: 컴파일 할 때부터 이미 확정된 값
    constexpr double kGravity = 9.81;

    // 문자열을 double(숫자)로 변환, 변환 실패 시 std::invalid_argument 예외를 던짐
    // &: 반복하지 않고 참조만 전달, 타입은 std::string, 전달 방식은 참조, const는 제약
    double ParseOrThrow(const std::string& label, const std::string& text) {
        try {
            size_t consumed = 0; // 변환에 사용된 문자열 길이
            double value = std::stod(text, &consumed); // value: 변환된 숫자, stod: 's'tring 'to' 'd'ouble, &는 주소 연산자
            if (consumed != text.size()) {
                throw std::invalid_argument("trailing characters");
            }
            return value;
        } catch (const std::exception&) { // 예외 발생 시, label과 text를 포함한 메시지와 함께 std::invalid_argument 예외를 던짐
            throw std::invalid_argument(label + " must be a valid number, but got: " + text);
        }
    }

    // 함수명 앞에 있는 double: 반환 타입 
    // 유효한 숫자를 입력받을 때까지 반복적으로 프롬프트를 출력하고, 입력된 값을 double로 변환하여 반환
    double ReadFromStdin(const std::string& prompt){
        double value = 0.0;
        while (true) {
            std::cout << prompt;
            if (std::cin >> value) {
                return value;
            }
            std::cin.clear(); // 입력 실패 상태를 초기화
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); // 입력 버퍼를 비움
            std::cout << "Invalid input. Please enter a number.";
        }
    }
}

int main(int argc, char* argv[]) {
    double speed = 0.0; // 속도 [m/s]
    double friction = 0.0; // 마찰계수

    if (argc >= 3) {
        try {
            speed = ParseOrThrow("Speed", argv[1]);
            friction = ParseOrThrow("Friction coefficient", argv[2]);
        } catch (const std::invalid_argument& e) {
            std::cerr << "Error: " << e.what() << "\n";
            std::cerr << "Usage: " << argv[0] << " <speed[m/s]> <friction coefficient>\n";
            return 1;
        }
        
    } else {
        std::cout << "Missing arguments — reading from stdin instead.\n";
        speed = ReadFromStdin("Enter speed (m/s): ");
        friction = ReadFromStdin("Enter friction coefficient: ");
    }

    if (friction <= 0.0) {
        std::cerr << "Error: Friction coefficient must be positive. (Got: " << friction << ")\n";
        return 1;
    }
    if (speed < 0.0) {
        std::cerr << "Error: Speed cannot be negative. (Got: " << speed << ")\n";
        return 1;
    }
    
    const double distance = (speed * speed) / (2 * friction * kGravity);
    std::cout << "Speed: " << speed << " m/s, Friction coefficient: " << friction << "\n";
    std::cout << "Stopping distance: " << distance << " m\n";

    return 0;
}
