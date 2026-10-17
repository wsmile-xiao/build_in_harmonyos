cmake_minimum_required(VERSION 3.15)
project(test_kwindowsystem CXX)

find_package(KF6WindowSystem REQUIRED)

add_executable(test_kwindowsystem test.cpp)
target_link_libraries(test_kwindowsystem KF6::WindowSystem)

enable_testing()
add_test(NAME test_kwindowsystem COMMAND test_kwindowsystem)
