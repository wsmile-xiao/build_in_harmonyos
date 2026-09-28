cmake_minimum_required(VERSION 3.15)
project(utmps_consumer_test C)

find_package(utmps CONFIG REQUIRED)

add_executable(test_utmps test.c)
target_link_libraries(test_utmps PRIVATE utmps::utmps)
