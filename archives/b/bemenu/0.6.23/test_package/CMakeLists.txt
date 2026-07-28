cmake_minimum_required(VERSION 3.15)
project(test_bemenu C)

# Find the package via Conan-generated CMakeDeps
find_package(bemenu REQUIRED)

add_executable(test_bemenu test.c)
target_link_libraries(test_bemenu bemenu::bemenu)

enable_testing()
add_test(NAME test_bemenu COMMAND test_bemenu)
