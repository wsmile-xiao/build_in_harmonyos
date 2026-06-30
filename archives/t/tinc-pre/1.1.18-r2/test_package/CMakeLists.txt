cmake_minimum_required(VERSION 3.15)
project(test_tinc-pre C)

# Find the package via Conan-generated CMakeDeps
find_package(tinc-pre REQUIRED)

add_executable(test_tinc-pre test.c)
target_link_libraries(test_tinc-pre tinc-pre::tinc-pre)

enable_testing()
add_test(NAME test_tinc-pre COMMAND test_tinc-pre)
