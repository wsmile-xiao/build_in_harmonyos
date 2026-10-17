cmake_minimum_required(VERSION 3.15)
project(test_das-watchdog C)

# Find the package via Conan-generated CMakeDeps
find_package(das-watchdog REQUIRED)

add_executable(test_das-watchdog test.c)
target_link_libraries(test_das-watchdog das-watchdog::das-watchdog)

enable_testing()
add_test(NAME test_das-watchdog COMMAND test_das-watchdog)
