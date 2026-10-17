cmake_minimum_required(VERSION 3.15)
project(test_minifb C)

find_package(minifb REQUIRED)

add_executable(test_minifb test_minifb.c)
target_link_libraries(test_minifb PRIVATE minifb::minifb)
set_target_properties(test_minifb PROPERTIES C_STANDARD 11)
