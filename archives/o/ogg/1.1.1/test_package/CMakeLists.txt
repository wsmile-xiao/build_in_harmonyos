cmake_minimum_required(VERSION 3.15)
project(ogg_consumer C)

find_package(Ogg CONFIG REQUIRED)

add_executable(ogg_consumer test_package.c)
target_link_libraries(ogg_consumer PRIVATE Ogg::ogg)
