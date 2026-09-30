cmake_minimum_required(VERSION 3.15)
project(test_xcb-util-keysyms C)

# Find the package via Conan-generated CMakeDeps
find_package(xcb-util-keysyms REQUIRED)

add_executable(test_xcb-util-keysyms test.c)
target_link_libraries(test_xcb-util-keysyms xcb-util-keysyms::xcb-util-keysyms)

enable_testing()
add_test(NAME test_xcb-util-keysyms COMMAND test_xcb-util-keysyms)
