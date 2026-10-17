cmake_minimum_required(VERSION 3.15)
project(test_cbflib C)

find_package(cbflib REQUIRED)

add_executable(consumer consumer.c)
target_link_libraries(consumer PRIVATE cbflib::cbflib)
