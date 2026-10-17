cmake_minimum_required(VERSION 3.15)
project(test_libhv C)

# Find the package via Conan-generated CMakeDeps
find_package(libhv REQUIRED)

add_executable(test_libhv test.c)
target_link_libraries(test_libhv libhv::libhv)

enable_testing()
add_test(NAME test_libhv COMMAND test_libhv)
