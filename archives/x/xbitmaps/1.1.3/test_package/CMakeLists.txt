cmake_minimum_required(VERSION 3.15)
project(test_xbitmaps C)

find_package(xbitmaps REQUIRED)

add_executable(test_xbitmaps test_xbitmaps.c)
target_link_libraries(test_xbitmaps PRIVATE xbitmaps::xbitmaps)

enable_testing()
add_test(NAME test_xbitmaps COMMAND test_xbitmaps)
