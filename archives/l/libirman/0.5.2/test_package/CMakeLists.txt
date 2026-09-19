cmake_minimum_required(VERSION 3.15)
project(libirman_consumer C)

enable_testing()

find_package(libirman CONFIG REQUIRED)

add_executable(libirman_consumer test_irman.c)
target_link_libraries(libirman_consumer PRIVATE libirman::libirman)

add_test(NAME consumer_assertions COMMAND libirman_consumer)
