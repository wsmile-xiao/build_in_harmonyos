cmake_minimum_required(VERSION 3.15)
project(test_libinput C)

find_package(libinput REQUIRED)

add_executable(test_libinput test_libinput.c)
target_link_libraries(test_libinput PRIVATE libinput::libinput)
