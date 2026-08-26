cmake_minimum_required(VERSION 3.15)
project(test_mjson C)

find_package(mjson REQUIRED CONFIG)

add_executable(test_mjson test_mjson.c)
target_link_libraries(test_mjson PRIVATE mjson::mjson)
