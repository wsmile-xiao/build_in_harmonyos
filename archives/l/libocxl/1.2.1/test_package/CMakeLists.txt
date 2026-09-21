cmake_minimum_required(VERSION 3.15)
project(libocxl_consumer C)

enable_testing()

find_package(ocxl CONFIG REQUIRED)

add_executable(libocxl_consumer test_libocxl.c)
target_link_libraries(libocxl_consumer PRIVATE ocxl::ocxl)

add_test(NAME consumer_assertions COMMAND libocxl_consumer)
