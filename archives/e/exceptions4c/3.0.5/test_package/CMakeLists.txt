cmake_minimum_required(VERSION 3.15)
project(test_exceptions4c C)

# Find the package via Conan-generated CMakeDeps
find_package(exceptions4c REQUIRED)

add_executable(test_exceptions4c test.c)
target_link_libraries(test_exceptions4c exceptions4c::exceptions4c)

enable_testing()
add_test(NAME test_exceptions4c COMMAND test_exceptions4c)
