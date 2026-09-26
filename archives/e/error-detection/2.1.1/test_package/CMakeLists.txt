cmake_minimum_required(VERSION 3.15)
project(test_error_detection C)

# Find the package via Conan-generated CMakeDeps
find_package(error-detection REQUIRED)

add_executable(test_error_detection test.c)
target_link_libraries(test_error_detection error-detection::error-detection)

enable_testing()
add_test(NAME test_error_detection COMMAND test_error_detection)
