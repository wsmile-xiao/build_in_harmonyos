cmake_minimum_required(VERSION 3.15)
project(test_devil C)

find_package(devil REQUIRED)

add_executable(test_devil test.c)
target_link_libraries(test_devil devil::devil)
