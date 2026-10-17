cmake_minimum_required(VERSION 3.16)
project(test_x264 C)

find_package(x264 REQUIRED CONFIG)

add_executable(test_x264 test.c)
target_link_libraries(test_x264 PRIVATE x264::x264)

enable_testing()
add_test(NAME test_x264 COMMAND test_x264)
