cmake_minimum_required(VERSION 3.25)
project(test_arrow CXX)

# Arrow 25.0.0 头文件使用 C++20 特性（std::span、std::bit_width、std::popcount），
# 且上游 SetupCxxFlags.cmake:173-180 对低于 20 的标准直接 FATAL_ERROR。
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Arrow REQUIRED)

add_executable(test_arrow test_arrow.cpp)
target_link_libraries(test_arrow PRIVATE Arrow::arrow)
