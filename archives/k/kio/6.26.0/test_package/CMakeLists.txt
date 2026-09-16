cmake_minimum_required(VERSION 3.16)
project(test_kio CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KF6KIOConfig.cmake chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network Xml Concurrent Test)
find_package(KF6KIO REQUIRED)

add_executable(test_kio test.cpp)
target_link_libraries(test_kio KF6::KIOCore)

enable_testing()
add_test(NAME test_kio COMMAND test_kio)
