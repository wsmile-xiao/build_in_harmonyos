cmake_minimum_required(VERSION 3.16)
project(test_open_isns LANGUAGES C)

find_package(open-isns CONFIG REQUIRED)
add_executable(test_open_isns test_open_isns.c)
target_link_libraries(test_open_isns PRIVATE open-isns::open-isns)
