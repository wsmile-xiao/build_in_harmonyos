cmake_minimum_required(VERSION 3.20)
project(test_directxmath CXX)

find_package(directxmath CONFIG REQUIRED)

add_executable(test_directxmath test.cpp)
target_link_libraries(test_directxmath PRIVATE Microsoft::DirectXMath)

# DirectXMath 头文件使用 C++11 特性
set_property(TARGET test_directxmath PROPERTY CXX_STANDARD 11)
set_property(TARGET test_directxmath PROPERTY CXX_STANDARD_REQUIRED ON)