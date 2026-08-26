cmake_minimum_required(VERSION 3.16)
project(test_atk C)

find_package(atk REQUIRED CONFIG)

add_executable(test_atk test_atk.c)
target_link_libraries(test_atk PRIVATE atk::atk)
