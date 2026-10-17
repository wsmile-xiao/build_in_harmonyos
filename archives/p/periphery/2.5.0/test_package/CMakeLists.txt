cmake_minimum_required(VERSION 3.15)
project(test_periphery C)

# Find the package via Conan-generated CMakeDeps
find_package(periphery REQUIRED)

add_executable(test_periphery test.c)
target_link_libraries(test_periphery periphery::periphery)

enable_testing()
add_test(NAME test_periphery COMMAND test_periphery)
