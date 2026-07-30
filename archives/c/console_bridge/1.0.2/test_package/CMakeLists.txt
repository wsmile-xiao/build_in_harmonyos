cmake_minimum_required(VERSION 3.15)
project(test_console_bridge CXX)

find_package(console_bridge REQUIRED)

add_executable(test_console_bridge test.cpp)
target_link_libraries(test_console_bridge console_bridge::console_bridge)

enable_testing()
add_test(NAME test_console_bridge COMMAND test_console_bridge)
