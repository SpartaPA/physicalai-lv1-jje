// clamp.cpp
#include <iostream>

template<typename T>
T clamp(T v, T lo, T hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

int main() {
    double speed = clamp<double>(3.7, 0.0, 2.0);   // double 속도값 클램프
    int pixel = clamp<int>(300, 0, 255);           // int 픽셀값 클램프
    std::cout << "clamped speed = " << speed << "\n";
    std::cout << "clamped pixel = " << pixel << "\n";
}