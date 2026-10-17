cmake_minimum_required(VERSION 3.15)
project(is_utf8_test LANGUAGES CXX)

# is_utf8 的公开 API 自 C++11 起提供，消费者测试取库自身标准
# （与已合并 fast_double_parser test_package 同口径；被测正确性与 profile cppstd 无关）。
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(is_utf8 CONFIG REQUIRED)

add_executable(is_utf8_test test.cpp)
target_link_libraries(is_utf8_test PRIVATE is_utf8::is_utf8)
