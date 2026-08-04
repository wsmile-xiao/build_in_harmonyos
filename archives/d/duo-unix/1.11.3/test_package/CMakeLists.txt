cmake_minimum_required(VERSION 3.15)
project(test_duo C)

find_package(duo-unix REQUIRED CONFIG)

add_executable(test_duo test_duo.c)
target_link_libraries(test_duo duo-unix::duo-unix)
