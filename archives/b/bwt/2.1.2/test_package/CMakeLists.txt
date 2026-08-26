cmake_minimum_required(VERSION 3.15)
project(test_bwt C)

find_package(bwt REQUIRED CONFIG)

add_executable(test_bwt test.c)
target_link_libraries(test_bwt PRIVATE bwt::bwt)