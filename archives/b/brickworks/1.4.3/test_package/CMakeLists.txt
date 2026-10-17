cmake_minimum_required(VERSION 3.15)
project(test_brickworks C)

# Find the package via Conan-generated CMakeDeps
find_package(brickworks REQUIRED)

add_executable(test_brickworks test.c)
target_link_libraries(test_brickworks brickworks::brickworks)

enable_testing()
add_test(NAME test_brickworks COMMAND test_brickworks)
