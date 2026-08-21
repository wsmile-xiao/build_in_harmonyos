cmake_minimum_required(VERSION 3.15)
project(test_audaspace C)

# Find the package via Conan-generated CMakeDeps
find_package(audaspace REQUIRED)

add_executable(test_audaspace test.c)
target_link_libraries(test_audaspace audaspace::audaspace)

enable_testing()
add_test(NAME test_audaspace COMMAND test_audaspace)
