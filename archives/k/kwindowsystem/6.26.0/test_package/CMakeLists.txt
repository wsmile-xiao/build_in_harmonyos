cmake_minimum_required(VERSION 3.15)
project(test_kwindowsystem CXX)

# KF6WindowSystemTargets.cmake references Qt6::Gui targets, so load Qt6
# first.
find_package(Qt6 REQUIRED COMPONENTS Gui)
find_package(KF6WindowSystem REQUIRED)

add_executable(test_kwindowsystem test.cpp)
target_link_libraries(test_kwindowsystem KF6::WindowSystem)

enable_testing()
add_test(NAME test_kwindowsystem COMMAND test_kwindowsystem)
