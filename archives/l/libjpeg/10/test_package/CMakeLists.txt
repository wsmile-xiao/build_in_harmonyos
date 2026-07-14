cmake_minimum_required(VERSION 3.15)
project(test_libjpeg C)

find_package(libjpeg REQUIRED)

add_executable(test_libjpeg test.c)
target_link_libraries(test_libjpeg libjpeg::libjpeg)
