cmake_minimum_required(VERSION 3.15)
project(test_libcuefile C)

# Find the package via Conan-generated CMakeDeps
find_package(libcuefile REQUIRED)

add_executable(test_libcuefile test.c)
target_link_libraries(test_libcuefile libcuefile::libcuefile)

enable_testing()
add_test(NAME test_libcuefile COMMAND test_libcuefile)
