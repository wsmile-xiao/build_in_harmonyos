cmake_minimum_required(VERSION 3.15)
project(test_abpoa C)

# Find the package via Conan-generated CMakeDeps
find_package(abpoa REQUIRED)

add_executable(test_abpoa test.c)
target_link_libraries(test_abpoa abpoa::abpoa)

enable_testing()
add_test(NAME test_abpoa COMMAND test_abpoa)
