cmake_minimum_required(VERSION 3.16)
project(test_kwidgetsaddons5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# KF5WidgetsAddonsTargets.cmake references Qt5::Widgets targets, so load the
# aggregated Qt5 config (CMakeDeps) first.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Widgets)
find_package(KF5WidgetsAddons 5.116.0 REQUIRED)

add_executable(test_kwidgetsaddons5 test.cpp)
target_link_libraries(test_kwidgetsaddons5 PRIVATE Qt5::Widgets KF5::WidgetsAddons)

enable_testing()
add_test(NAME test_kwidgetsaddons5 COMMAND test_kwidgetsaddons5)
