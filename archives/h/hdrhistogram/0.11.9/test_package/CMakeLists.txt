cmake_minimum_required(VERSION 3.15)
project(test_hdrhistogram C)

find_package(hdr_histogram REQUIRED)

add_executable(test_hdrhistogram test.c)
target_link_libraries(test_hdrhistogram hdr_histogram::hdr_histogram)

enable_testing()
add_test(NAME test_hdrhistogram COMMAND test_hdrhistogram)
