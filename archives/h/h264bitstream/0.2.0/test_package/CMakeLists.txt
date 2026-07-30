cmake_minimum_required(VERSION 3.15)
project(test_h264bitstream C)

find_package(h264bitstream REQUIRED)

add_executable(test_h264bitstream test.c)
target_link_libraries(test_h264bitstream h264bitstream::h264bitstream)

enable_testing()
add_test(NAME test_h264bitstream COMMAND test_h264bitstream)
