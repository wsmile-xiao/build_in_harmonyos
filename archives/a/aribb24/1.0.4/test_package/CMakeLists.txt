cmake_minimum_required(VERSION 3.15)
project(aribb24_test LANGUAGES C)

find_package(aribb24 CONFIG REQUIRED)
add_executable(test_aribb24 test_aribb24.c)
target_link_libraries(test_aribb24 PRIVATE aribb24::aribb24)
