cmake_minimum_required(VERSION 3.15)
project(test_nspr C)

# Find the package via Conan-generated CMakeDeps
find_package(nspr REQUIRED)

add_executable(test_nspr test.c)
target_link_libraries(test_nspr nspr::nspr)

enable_testing()
add_test(NAME test_nspr COMMAND test_nspr)