cmake_minimum_required(VERSION 3.20)
project(test_libhdf4 LANGUAGES C)

find_package(HDF4 CONFIG REQUIRED)

add_executable(test_libhdf4 test.c)
target_link_libraries(test_libhdf4 PRIVATE HDF4::HDF4)
