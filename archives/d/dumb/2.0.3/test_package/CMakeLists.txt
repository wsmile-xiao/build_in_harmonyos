cmake_minimum_required(VERSION 3.15)
project(test_dumb C)

find_package(dumb REQUIRED)

add_executable(test_dumb test_dumb.c)
target_link_libraries(test_dumb PRIVATE dumb::dumb)
set_target_properties(test_dumb PROPERTIES C_STANDARD 99)
