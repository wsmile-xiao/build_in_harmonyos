cmake_minimum_required(VERSION 3.15)
project(libftdi_consumer C)

enable_testing()

find_package(libftdi CONFIG REQUIRED)

add_executable(libftdi_consumer test.c)
target_link_libraries(libftdi_consumer PRIVATE libftdi::libftdi)

add_test(NAME consumer_assertions COMMAND libftdi_consumer)
