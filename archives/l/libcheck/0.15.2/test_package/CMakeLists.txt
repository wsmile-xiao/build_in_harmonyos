cmake_minimum_required(VERSION 3.15)
project(test_libcheck C)

# Find the package via Conan-generated CMakeDeps
find_package(libcheck REQUIRED)

add_executable(test_libcheck test.c)
target_link_libraries(test_libcheck libcheck::libcheck)

enable_testing()
add_test(NAME test_libcheck COMMAND test_libcheck)
