# C++23（SET(CMAKE_CXX_STANDARD 23)）需 CMake >= 3.20（P3 审查修复：3.15 -> 3.20）
cmake_minimum_required(VERSION 3.20)
project(test_libfex CXX)

# 消费者以 C++23 编译（公共头使用 std::expected 等 C++23 特性；clang-15 下
# CMake 自动映射为 -std=c++2b；libfex 的 cxxflags 亦已注入，这里显式声明一致）
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(libfex REQUIRED)

add_executable(test_libfex test.cpp)
target_link_libraries(test_libfex PRIVATE libfex::libfex)

enable_testing()
add_test(NAME test_libfex COMMAND test_libfex)
