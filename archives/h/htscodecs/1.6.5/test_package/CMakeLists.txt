cmake_minimum_required(VERSION 3.15)
project(test_htscodecs C)

# Find the package via Conan-generated CMakeDeps
find_package(htscodecs REQUIRED)

add_executable(test_htscodecs test.c)
target_link_libraries(test_htscodecs htscodecs::htscodecs)

enable_testing()
add_test(NAME test_htscodecs COMMAND test_htscodecs)
