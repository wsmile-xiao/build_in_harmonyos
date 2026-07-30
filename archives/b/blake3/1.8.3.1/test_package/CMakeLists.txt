cmake_minimum_required(VERSION 3.15)
project(test_blake3 C)

find_package(blake3 REQUIRED)

add_executable(test_blake3 test_blake3.c)
target_link_libraries(test_blake3 blake3::blake3)
