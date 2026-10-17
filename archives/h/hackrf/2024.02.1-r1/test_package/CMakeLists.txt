cmake_minimum_required(VERSION 3.15)
project(test_hackrf C)

# Find the package via Conan-generated CMakeDeps
find_package(hackrf REQUIRED)

add_executable(test_hackrf test.c)
target_link_libraries(test_hackrf hackrf::hackrf)

enable_testing()
add_test(NAME test_hackrf COMMAND test_hackrf)
