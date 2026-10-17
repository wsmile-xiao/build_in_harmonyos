cmake_minimum_required(VERSION 3.15)
project(test_kstatusnotifieritem CXX)

find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(KF6StatusNotifierItem REQUIRED)

add_executable(test_kstatusnotifieritem test.cpp)
target_link_libraries(test_kstatusnotifieritem KF6::StatusNotifierItem Qt6::Widgets)
