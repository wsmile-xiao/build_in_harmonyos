cmake_minimum_required(VERSION 3.15)
project(test_avro_c C)

find_package(avro CONFIG REQUIRED)

add_executable(avro_version test_avro_c.c)
target_link_libraries(avro_version avro)
