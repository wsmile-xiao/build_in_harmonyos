cmake_minimum_required(VERSION 3.15)
project(test_package)

find_package(chaos-marmosets REQUIRED)

add_executable(test test.c)
target_link_libraries(test chaos-marmosets::chaos-marmosets)
