cmake_minimum_required(VERSION 3.15)
project(test_libuhttpd C)

# Find the package via Conan-generated CMakeDeps
find_package(libuhttpd REQUIRED)

add_executable(test_libuhttpd test.c)
target_link_libraries(test_libuhttpd PRIVATE libuhttpd::libuhttpd)

enable_testing()
add_test(NAME test_libuhttpd COMMAND test_libuhttpd)
