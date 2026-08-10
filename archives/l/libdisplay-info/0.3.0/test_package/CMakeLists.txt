cmake_minimum_required(VERSION 3.15)
project(test_libdisplay-info C)

# Find the package via Conan-generated CMakeDeps
find_package(libdisplay-info REQUIRED)

add_executable(test_libdisplay-info test.c)
target_link_libraries(test_libdisplay-info libdisplay-info::libdisplay-info)

enable_testing()
add_test(NAME test_libdisplay-info COMMAND test_libdisplay-info)
