cmake_minimum_required(VERSION 3.15)
project(libogg_consumer C)

find_package(Ogg CONFIG REQUIRED)

add_executable(libogg_consumer test_package.c)
target_link_libraries(libogg_consumer PRIVATE Ogg::ogg)
