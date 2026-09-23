cmake_minimum_required(VERSION 3.15)
project(test_libmicrohttpd C)

# Find the package via Conan-generated CMakeDeps
find_package(libmicrohttpd REQUIRED)

add_executable(test_libmicrohttpd test.c)
target_link_libraries(test_libmicrohttpd libmicrohttpd::libmicrohttpd)

enable_testing()
add_test(NAME test_libmicrohttpd COMMAND test_libmicrohttpd)
