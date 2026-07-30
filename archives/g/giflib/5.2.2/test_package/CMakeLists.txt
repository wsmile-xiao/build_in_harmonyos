cmake_minimum_required(VERSION 3.15)
project(test_giflib C)

find_package(giflib REQUIRED CONFIG)

add_executable(test_giflib test.c)
target_link_libraries(test_giflib PRIVATE giflib::giflib)
