cmake_minimum_required(VERSION 3.15)
project(test_gb C)

# Find the package via Conan-generated CMakeDeps
find_package(gb REQUIRED)

add_executable(test_gb test.c)
target_link_libraries(test_gb gb::gb)

enable_testing()
add_test(NAME test_gb COMMAND test_gb)
