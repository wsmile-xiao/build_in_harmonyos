cmake_minimum_required(VERSION 3.15)
project(test_kservice CXX)

# KF6ServiceConfig chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Xml)
find_package(KF6Service REQUIRED)

add_executable(test_kservice test.cpp)
target_link_libraries(test_kservice KF6::Service)

enable_testing()
add_test(NAME test_kservice COMMAND test_kservice)
