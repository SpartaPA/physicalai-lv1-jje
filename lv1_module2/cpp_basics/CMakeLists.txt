cmake_minimum_required(VERSION 3.22)
project(cpp_basics CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_compile_options(-Wall)

add_executable(motor_app main.cpp motor.cpp)