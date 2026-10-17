cmake_minimum_required(VERSION 3.15)
project(test_microlog C)

# Find the package via Conan-generated CMakeDeps
find_package(microlog REQUIRED)

add_executable(test_microlog test.c)
target_link_libraries(test_microlog microlog::microlog)

enable_testing()
add_test(NAME test_microlog COMMAND test_microlog)
