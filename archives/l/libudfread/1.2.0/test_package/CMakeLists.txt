cmake_minimum_required(VERSION 3.15)
project(test_libudfread LANGUAGES C)

find_package(libudfread CONFIG REQUIRED)

add_executable(test_libudfread test_libudfread.c)
target_link_libraries(test_libudfread PRIVATE libudfread::libudfread)
