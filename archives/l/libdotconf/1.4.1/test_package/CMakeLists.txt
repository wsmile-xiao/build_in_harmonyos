cmake_minimum_required(VERSION 3.15)
project(test_libdotconf C)

find_package(libdotconf REQUIRED CONFIG)

add_executable(test_libdotconf test_libdotconf.c)
target_link_libraries(test_libdotconf PRIVATE libdotconf::libdotconf)
