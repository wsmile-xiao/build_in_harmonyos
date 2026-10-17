cmake_minimum_required(VERSION 3.15)
project(mtfmt_consumer_test C)

find_package(mtfmt CONFIG REQUIRED)

add_executable(mtfmt_consumer_test test.c)
target_link_libraries(mtfmt_consumer_test PRIVATE mtfmt::mtfmt)
