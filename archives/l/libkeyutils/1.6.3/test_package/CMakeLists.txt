cmake_minimum_required(VERSION 3.15)
project(test_keyutils C)

find_package(libkeyutils REQUIRED)

add_executable(test_keyutils test_keyutils.c)
target_link_libraries(test_keyutils libkeyutils::libkeyutils)
