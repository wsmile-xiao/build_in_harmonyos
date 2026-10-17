cmake_minimum_required(VERSION 3.15)
project(test_libcrc C)

# Find the package via Conan-generated CMakeDeps
find_package(libcrc REQUIRED)

add_executable(test_libcrc test.c)
target_link_libraries(test_libcrc libcrc::libcrc)

enable_testing()
add_test(NAME test_libcrc COMMAND test_libcrc)
