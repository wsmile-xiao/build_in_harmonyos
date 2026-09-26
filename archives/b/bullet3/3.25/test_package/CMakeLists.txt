cmake_minimum_required(VERSION 3.15)
project(test_bullet CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(bullet3 REQUIRED)

# 被测包内含 pthread 后端（LinearMath btThreadSupportPosix / btThreads）。
# OHOS musl 把 pthread 并入 libc，此处显式声明以保持跨平台链接正确。
find_package(Threads REQUIRED)

add_executable(test_bullet test.cpp)
target_link_libraries(test_bullet bullet3::bullet3 Threads::Threads)

enable_testing()
add_test(NAME test_bullet COMMAND test_bullet)
