cmake_minimum_required(VERSION 3.15)
project(test_lm_sensors C)

# Find the package via Conan-generated CMakeDeps
find_package(lm-sensors REQUIRED)

add_executable(test_lm_sensors test.c)
target_link_libraries(test_lm_sensors lm-sensors::lm-sensors)

enable_testing()
add_test(NAME test_lm_sensors COMMAND test_lm_sensors)
