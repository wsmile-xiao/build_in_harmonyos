cmake_minimum_required(VERSION 3.15)
project(test_minunit C)

find_package(minunit REQUIRED)

add_executable(test_minunit test_minunit.c)
target_link_libraries(test_minunit PRIVATE minunit::minunit)
