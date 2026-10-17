cmake_minimum_required(VERSION 3.15)
project(test_jimtcl C)

find_package(jimtcl REQUIRED)

add_executable(test_jimtcl test.c)
target_link_libraries(test_jimtcl jimtcl::jimtcl)
