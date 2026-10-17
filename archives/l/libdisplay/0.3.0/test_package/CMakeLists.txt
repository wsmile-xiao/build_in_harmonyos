cmake_minimum_required(VERSION 3.15)
project(test_libdisplay C)

# Find the package via Conan-generated CMakeDeps
find_package(libdisplay REQUIRED)

add_executable(test_libdisplay test.c)
target_link_libraries(test_libdisplay libdisplay::libdisplay)

enable_testing()
add_test(NAME test_libdisplay COMMAND test_libdisplay)
