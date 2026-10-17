cmake_minimum_required(VERSION 3.15)
project(test_libitl_gobject C)

# Find the package via Conan-generated CMakeDeps.
find_package(libitl-gobject REQUIRED)

add_executable(test_libitl_gobject test.c)
target_link_libraries(test_libitl_gobject libitl-gobject::libitl-gobject)

enable_testing()
add_test(NAME test_libitl_gobject COMMAND test_libitl_gobject)
