cmake_minimum_required(VERSION 3.15)
project(test_wslay C)

find_package(wslay CONFIG REQUIRED)

add_executable(test_wslay test.c)
target_link_libraries(test_wslay PRIVATE wslay::wslay)
