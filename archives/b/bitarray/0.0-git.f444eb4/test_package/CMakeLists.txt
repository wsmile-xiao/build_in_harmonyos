cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(bitarray CONFIG REQUIRED)

add_executable(test_bitarray test_bitarray.c)
target_link_libraries(test_bitarray PRIVATE bitarray::bitarray)
target_compile_features(test_bitarray PRIVATE c_std_99)
