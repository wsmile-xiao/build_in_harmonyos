cmake_minimum_required(VERSION 3.15)
project(libsmacker_test LANGUAGES C)

find_package(libsmacker CONFIG REQUIRED)

add_executable(libsmacker_test test_libsmacker.c)
target_link_libraries(libsmacker_test PRIVATE libsmacker::libsmacker)
