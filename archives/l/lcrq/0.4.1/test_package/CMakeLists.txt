cmake_minimum_required(VERSION 3.15)
project(test_lcrq C)

# Find the package via Conan-generated CMakeDeps
find_package(lcrq REQUIRED)

add_executable(test_lcrq test.c)
target_link_libraries(test_lcrq lcrq::lcrq)

enable_testing()
add_test(NAME test_lcrq COMMAND test_lcrq)
