cmake_minimum_required(VERSION 3.15)
project(test_mhash C)

find_package(mhash REQUIRED CONFIG)

add_executable(test_mhash test_mhash.c)
target_link_libraries(test_mhash PRIVATE mhash::mhash)
