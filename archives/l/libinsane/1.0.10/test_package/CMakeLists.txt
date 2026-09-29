cmake_minimum_required(VERSION 3.15)
project(test_libinsane C)

find_package(libinsane REQUIRED CONFIG)

add_executable(test_libinsane test_libinsane.c)
target_link_libraries(test_libinsane PRIVATE libinsane::libinsane)
