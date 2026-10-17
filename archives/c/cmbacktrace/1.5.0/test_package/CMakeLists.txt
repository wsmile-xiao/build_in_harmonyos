cmake_minimum_required(VERSION 3.15)
project(test_cmbacktrace C)

# Find the package via Conan-generated CMakeDeps
find_package(cmbacktrace REQUIRED)

add_executable(test_cmbacktrace test.c)
target_link_libraries(test_cmbacktrace cmbacktrace::cmbacktrace)

enable_testing()
add_test(NAME test_cmbacktrace COMMAND test_cmbacktrace)
