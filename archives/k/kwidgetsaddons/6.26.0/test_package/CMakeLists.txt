cmake_minimum_required(VERSION 3.15)
project(test_kwidgetsaddons CXX)

# KF6WidgetsAddonsTargets.cmake references Qt6::Widgets targets, so load
# Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(KF6WidgetsAddons REQUIRED)

add_executable(test_kwidgetsaddons test.cpp)
target_link_libraries(test_kwidgetsaddons KF6::WidgetsAddons)

enable_testing()
add_test(NAME test_kwidgetsaddons COMMAND test_kwidgetsaddons)
