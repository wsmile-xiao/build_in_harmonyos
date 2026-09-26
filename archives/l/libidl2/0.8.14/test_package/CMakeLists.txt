cmake_minimum_required(VERSION 3.15)
project(test_libidl2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libidl2 REQUIRED)

add_executable(test_libidl2 test.c)
target_link_libraries(test_libidl2 libidl2::libidl2)

enable_testing()
add_test(NAME test_libidl2 COMMAND test_libidl2)
