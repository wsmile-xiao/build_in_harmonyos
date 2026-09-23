cmake_minimum_required(VERSION 3.15)
project(test_libwapcaplet C)

# Find the package via Conan-generated CMakeDeps
find_package(LibWapcaplet REQUIRED)

add_executable(test_libwapcaplet test.c)
target_link_libraries(test_libwapcaplet LibWapcaplet::wapcaplet)

enable_testing()
add_test(NAME test_libwapcaplet COMMAND test_libwapcaplet)
