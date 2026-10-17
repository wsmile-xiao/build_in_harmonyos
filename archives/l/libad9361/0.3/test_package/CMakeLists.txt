cmake_minimum_required(VERSION 3.15)
project(libad9361_consumer C)

enable_testing()

find_package(ad9361 CONFIG REQUIRED)

add_executable(libad9361_consumer test_libad9361.c)
target_link_libraries(libad9361_consumer PRIVATE ad9361::ad9361 m)

add_test(NAME consumer_assertions COMMAND libad9361_consumer)
