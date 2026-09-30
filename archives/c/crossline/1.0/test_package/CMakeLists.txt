cmake_minimum_required(VERSION 3.15)
project(crossline_consumer C)

find_package(crossline CONFIG REQUIRED)

add_executable(crossline_consumer consumer.c)
target_link_libraries(crossline_consumer PRIVATE crossline::crossline)