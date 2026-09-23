cmake_minimum_required(VERSION 3.15)
project(test_console_bridge CXX)

# Find the package via Conan-generated CMakeDeps
find_package(console_bridge REQUIRED CONFIG)

add_executable(test_console_bridge test.cpp)
target_link_libraries(test_console_bridge PRIVATE console_bridge::console_bridge)

enable_testing()
add_test(NAME test_console_bridge COMMAND test_console_bridge)
