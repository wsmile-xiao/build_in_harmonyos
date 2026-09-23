cmake_minimum_required(VERSION 3.15)
project(test_libfreexl C)

find_package(libfreexl REQUIRED CONFIG)

add_executable(test_libfreexl test_libfreexl.c)
target_link_libraries(test_libfreexl PRIVATE libfreexl::libfreexl)
