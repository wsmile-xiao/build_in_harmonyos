cmake_minimum_required(VERSION 3.15)
project(test_libdvdread LANGUAGES C)

find_package(dvdread CONFIG REQUIRED)

add_executable(test_libdvdread test_libdvdread.c)
target_link_libraries(test_libdvdread PRIVATE dvdread::dvdread)
