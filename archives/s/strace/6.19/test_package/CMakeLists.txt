cmake_minimum_required(VERSION 3.15)
project(test_strace C)

# Find the package via Conan-generated CMakeDeps
find_package(strace REQUIRED)

add_executable(test_strace test.c)
target_link_libraries(test_strace strace::strace)

enable_testing()
add_test(NAME test_strace COMMAND test_strace)
