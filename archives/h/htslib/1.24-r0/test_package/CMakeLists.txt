cmake_minimum_required(VERSION 3.15)
project(test_htslib C)

find_package(htslib REQUIRED)

add_executable(test_htslib test_htslib.c)
target_link_libraries(test_htslib htslib::htslib)
