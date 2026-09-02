cmake_minimum_required(VERSION 3.15)
project(test_libstatgrab C)

# Find the package via Conan-generated CMakeDeps
find_package(libstatgrab REQUIRED)

add_executable(test_libstatgrab test.c)
target_link_libraries(test_libstatgrab libstatgrab::libstatgrab)

enable_testing()
add_test(NAME test_libstatgrab COMMAND test_libstatgrab)
