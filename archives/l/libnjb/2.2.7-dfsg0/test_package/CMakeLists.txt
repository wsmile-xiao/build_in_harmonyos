cmake_minimum_required(VERSION 3.15)
project(libnjb_consumer C)

enable_testing()

find_package(libnjb CONFIG REQUIRED)

add_executable(libnjb_consumer test_libnjb.c)
target_link_libraries(libnjb_consumer PRIVATE libnjb::libnjb)

add_test(NAME consumer_assertions COMMAND libnjb_consumer)
