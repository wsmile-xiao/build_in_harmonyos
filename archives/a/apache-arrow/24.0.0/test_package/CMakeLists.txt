cmake_minimum_required(VERSION 3.16)
project(test_arrow CXX)

# Arrow 24.0.0 头文件使用 C++20 特性 (std::span, std::bit_width, std::popcount)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Arrow REQUIRED)

add_executable(test_arrow test_arrow.cpp)
target_link_libraries(test_arrow PRIVATE Arrow::arrow)
