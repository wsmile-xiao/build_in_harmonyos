cmake_minimum_required(VERSION 3.15)
project(test_libdvdcss LANGUAGES C)

find_package(libdvdcss CONFIG REQUIRED)

add_executable(test_libdvdcss test_libdvdcss.c)
target_link_libraries(test_libdvdcss PRIVATE dvdcss::dvdcss)
