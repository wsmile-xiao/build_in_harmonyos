cmake_minimum_required(VERSION 3.15)
project(test_avahi C)

find_package(avahi REQUIRED CONFIG)

add_executable(test_avahi test.c)
target_link_libraries(test_avahi avahi::avahi)
