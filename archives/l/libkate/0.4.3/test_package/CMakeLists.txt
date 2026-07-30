cmake_minimum_required(VERSION 3.15)
project(test_libkate LANGUAGES C)

find_package(kate CONFIG REQUIRED)

add_executable(test_libkate test_libkate.c)
target_link_libraries(test_libkate PRIVATE kate::kate)
