cmake_minimum_required(VERSION 3.15)
project(genann_test_package C)

find_package(genann REQUIRED CONFIG)

add_executable(consumer_test consumer_test.c)
target_link_libraries(consumer_test PRIVATE genann::genann)