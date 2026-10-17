cmake_minimum_required(VERSION 3.15)
project(test_libzbar C)

# Find the package via Conan-generated CMakeDeps
find_package(libzbar REQUIRED)

add_executable(test_libzbar test.c)
target_link_libraries(test_libzbar libzbar::libzbar)

enable_testing()
add_test(NAME test_libzbar COMMAND test_libzbar)
