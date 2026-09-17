cmake_minimum_required(VERSION 3.15)
project(test_glu C)

find_package(glu CONFIG REQUIRED)

add_executable(test_glu test_glu.c)
target_link_libraries(test_glu PRIVATE glu::glu)
