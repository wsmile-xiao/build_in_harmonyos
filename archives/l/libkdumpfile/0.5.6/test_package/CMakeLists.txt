cmake_minimum_required(VERSION 3.15)
project(test_libkdumpfile C)

# Find the package via Conan-generated CMakeDeps
find_package(libkdumpfile REQUIRED)

add_executable(test_libkdumpfile test.c)
target_link_libraries(test_libkdumpfile libkdumpfile::libkdumpfile)

enable_testing()
add_test(NAME test_libkdumpfile COMMAND test_libkdumpfile)
