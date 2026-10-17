cmake_minimum_required(VERSION 3.15)
project(libtracecmd_consumer_test C)

find_package(libtracecmd CONFIG REQUIRED)

add_executable(libtracecmd_consumer_test test.c)
target_link_libraries(libtracecmd_consumer_test PRIVATE libtracecmd::libtracecmd)
