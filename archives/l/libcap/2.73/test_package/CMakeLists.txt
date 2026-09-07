cmake_minimum_required(VERSION 3.15)
project(test_libcap C)

# Find the package via Conan-generated CMakeDeps
find_package(libcap REQUIRED)

add_executable(test_libcap test.c)
target_link_libraries(test_libcap libcap::libcap)

enable_testing()
add_test(NAME test_libcap COMMAND test_libcap)
