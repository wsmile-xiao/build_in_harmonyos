cmake_minimum_required(VERSION 3.15)
project(cnats_consumer C)

find_package(cnats REQUIRED)

add_executable(consumer test_package.c)
target_link_libraries(consumer PRIVATE cnats::cnats)
