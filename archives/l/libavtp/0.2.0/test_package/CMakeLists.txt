cmake_minimum_required(VERSION 3.15)
project(test_libavtp LANGUAGES C)

find_package(libavtp CONFIG REQUIRED)

add_executable(test_libavtp test_libavtp.c)
target_link_libraries(test_libavtp PRIVATE libavtp::avtp)
