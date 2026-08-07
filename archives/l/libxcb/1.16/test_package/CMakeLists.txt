cmake_minimum_required(VERSION 3.15)
project(test_libxcb C)

find_package(libxcb REQUIRED CONFIG)

add_executable(test_libxcb test.c)
target_link_libraries(test_libxcb PRIVATE libxcb::xcb)

enable_testing()
add_test(NAME test_libxcb COMMAND test_libxcb)
