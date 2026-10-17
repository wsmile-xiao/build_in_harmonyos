cmake_minimum_required(VERSION 3.15)
project(test_cobs-c C)

# Find the package via Conan-generated CMakeDeps
find_package(cobs-c REQUIRED)

add_executable(test_cobs-c test.c)
target_link_libraries(test_cobs-c cobs-c::cobs-c)

enable_testing()
add_test(NAME test_cobs-c COMMAND test_cobs-c)
