cmake_minimum_required(VERSION 3.15)
project(test_elk C)

find_package(elk CONFIG REQUIRED)

add_executable(test_elk test_elk.c)
target_link_libraries(test_elk PRIVATE elk::elk)
set_target_properties(test_elk PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
