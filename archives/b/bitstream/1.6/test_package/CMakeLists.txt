cmake_minimum_required(VERSION 3.15)
project(test_bitstream C)

find_package(bitstream REQUIRED)

add_executable(test_bitstream test_bitstream.c)
target_link_libraries(test_bitstream PRIVATE bitstream::bitstream)

enable_testing()
add_test(NAME test_bitstream COMMAND test_bitstream)
