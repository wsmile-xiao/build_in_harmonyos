cmake_minimum_required(VERSION 3.15)
project(test_cahute C)

# Find the package via Conan-generated CMakeDeps
find_package(cahute REQUIRED)

add_executable(test_cahute test.c)
target_link_libraries(test_cahute cahute::cahute)

enable_testing()
add_test(NAME test_cahute COMMAND test_cahute)
