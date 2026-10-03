cmake_minimum_required(VERSION 3.15)
project(volpack_consumer C)

find_package(volpack CONFIG REQUIRED)
add_executable(test_volpack test.c)
target_link_libraries(test_volpack PRIVATE volpack::volpack)
