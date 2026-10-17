cmake_minimum_required(VERSION 3.15)
project(libart_lgpl_consumer C)

enable_testing()

find_package(libart-lgpl CONFIG REQUIRED)

add_executable(libart_lgpl_consumer test.c)
target_link_libraries(libart_lgpl_consumer PRIVATE libart-lgpl::libart-lgpl)

add_test(NAME consumer_assertions COMMAND libart_lgpl_consumer)
