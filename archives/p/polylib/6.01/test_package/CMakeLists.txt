cmake_minimum_required(VERSION 3.15)
project(test_polylib C)

# Find the package via Conan-generated CMakeDeps
find_package(polylib REQUIRED)

add_executable(test_polylib test_polylib.c)
target_link_libraries(test_polylib polylib::polylib)

enable_testing()
add_test(NAME test_polylib COMMAND test_polylib)
