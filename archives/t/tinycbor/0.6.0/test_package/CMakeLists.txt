cmake_minimum_required(VERSION 3.15)
project(test_tinycbor C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(tinycbor REQUIRED CONFIG)

add_executable(test_tinycbor test_tinycbor.c)
target_link_libraries(test_tinycbor tinycbor::tinycbor)

enable_testing()
add_test(NAME test_tinycbor COMMAND test_tinycbor)