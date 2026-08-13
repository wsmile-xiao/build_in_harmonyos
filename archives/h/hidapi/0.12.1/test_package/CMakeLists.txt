cmake_minimum_required(VERSION 3.15)
project(test_hidapi C)

# Find the package via Conan-generated CMakeDeps
find_package(hidapi REQUIRED)

add_executable(test_hidapi test.c)
target_link_libraries(test_hidapi hidapi::hidapi)

enable_testing()
add_test(NAME test_hidapi COMMAND test_hidapi)
