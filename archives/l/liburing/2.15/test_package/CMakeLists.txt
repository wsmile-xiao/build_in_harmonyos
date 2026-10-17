cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via Conan-generated CMakeDeps
find_package(liburing REQUIRED CONFIG)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE liburing::liburing)

enable_testing()
add_test(NAME test_package COMMAND test_package)
