cmake_minimum_required(VERSION 3.15)
project(test_libdynamic C)

# Find the package via Conan-generated CMakeDeps
find_package(libdynamic REQUIRED)

add_executable(test_libdynamic test.c)
target_link_libraries(test_libdynamic libdynamic::libdynamic)

enable_testing()
add_test(NAME test_libdynamic COMMAND test_libdynamic)
