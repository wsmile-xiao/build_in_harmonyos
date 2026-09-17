cmake_minimum_required(VERSION 3.15)
project(test_cmor C)

# Find the package via Conan-generated CMakeDeps
find_package(cmor REQUIRED)

add_executable(test_cmor test.c)
target_link_libraries(test_cmor cmor::cmor)

enable_testing()
add_test(NAME test_cmor COMMAND test_cmor)
