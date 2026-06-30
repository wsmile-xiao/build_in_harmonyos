cmake_minimum_required(VERSION 3.15)
project(test_wgetpaste C)

# Find the package via Conan-generated CMakeDeps
find_package(wgetpaste REQUIRED)

add_executable(test_wgetpaste test.c)
target_link_libraries(test_wgetpaste wgetpaste::wgetpaste)

enable_testing()
add_test(NAME test_wgetpaste COMMAND test_wgetpaste)
