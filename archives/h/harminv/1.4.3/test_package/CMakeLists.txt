cmake_minimum_required(VERSION 3.15)
project(test_harminv C)

# Find the package via Conan-generated CMakeDeps
find_package(harminv REQUIRED)

add_executable(test_harminv test.c)
target_link_libraries(test_harminv harminv::harminv)

enable_testing()
add_test(NAME test_harminv COMMAND test_harminv)
