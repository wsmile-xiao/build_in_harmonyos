cmake_minimum_required(VERSION 3.15)
project(test_libhubbub C)

# Find the package via Conan-generated CMakeDeps
find_package(LibHubbub REQUIRED)

add_executable(test_libhubbub test.c)
target_link_libraries(test_libhubbub LibHubbub::hubbub)

enable_testing()
add_test(NAME test_libhubbub COMMAND test_libhubbub)
