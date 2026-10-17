cmake_minimum_required(VERSION 3.15)
project(test_judy C)

# Find the package via Conan-generated CMakeDeps
find_package(judy REQUIRED)

add_executable(test_judy test.c)
target_link_libraries(test_judy judy::judy)

enable_testing()
add_test(NAME test_judy COMMAND test_judy)
