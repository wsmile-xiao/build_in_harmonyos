cmake_minimum_required(VERSION 3.15)
project(test_ftdi C)

find_package(libftdi1 REQUIRED)

add_executable(test_ftdi test_ftdi.c)
target_link_libraries(test_ftdi PRIVATE libftdi1::libftdi1)
