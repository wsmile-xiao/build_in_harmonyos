cmake_minimum_required(VERSION 3.15)
project(test_liberasurecode C)

# Find the package via Conan-generated CMakeDeps
find_package(liberasurecode REQUIRED)

add_executable(test_liberasurecode test.c)
target_link_libraries(test_liberasurecode liberasurecode::liberasurecode)

enable_testing()
add_test(NAME test_liberasurecode COMMAND test_liberasurecode)
