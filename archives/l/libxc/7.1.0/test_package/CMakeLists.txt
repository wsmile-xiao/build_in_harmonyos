cmake_minimum_required(VERSION 3.15)
project(test_libxc C)

find_package(Libxc REQUIRED CONFIG)

add_executable(test_libxc test_libxc.c)
target_link_libraries(test_libxc Libxc::xc)

enable_testing()
add_test(NAME test_libxc COMMAND test_libxc)
