cmake_minimum_required(VERSION 3.15)
project(test_kauth CXX)

# KF6AuthConfig chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Auth REQUIRED)

add_executable(test_kauth test.cpp)
target_link_libraries(test_kauth KF6::AuthCore)

enable_testing()
add_test(NAME test_kauth COMMAND test_kauth)
