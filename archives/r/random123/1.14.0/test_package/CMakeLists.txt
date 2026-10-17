cmake_minimum_required(VERSION 3.15)
project(test_random123 C)

# Find the package via Conan-generated CMakeDeps
find_package(random123 REQUIRED)

add_executable(test_random123 test.c)
target_link_libraries(test_random123 random123::random123)

enable_testing()
add_test(NAME test_random123 COMMAND test_random123)
