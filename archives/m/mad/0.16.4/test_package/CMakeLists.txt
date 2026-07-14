cmake_minimum_required(VERSION 3.5)
project(test_mad C)

# Find the package via Conan-generated CMakeDeps
find_package(mad REQUIRED)

add_executable(test_mad test.c)
target_link_libraries(test_mad mad::mad)

enable_testing()
add_test(NAME test_mad COMMAND test_mad)
