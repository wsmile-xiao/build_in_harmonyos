cmake_minimum_required(VERSION 3.15)
project(test_pcg-c C)

# Find the package via Conan-generated CMakeDeps
find_package(pcg-c REQUIRED)

add_executable(test_pcg-c test.c)
target_link_libraries(test_pcg-c pcg-c::pcg-c)

enable_testing()
add_test(NAME test_pcg-c COMMAND test_pcg-c)
