cmake_minimum_required(VERSION 3.15)
project(test_dcap C)

find_package(dcap CONFIG REQUIRED)

add_executable(test_dcap test.c)
target_link_libraries(test_dcap PRIVATE dcap::dcap)
