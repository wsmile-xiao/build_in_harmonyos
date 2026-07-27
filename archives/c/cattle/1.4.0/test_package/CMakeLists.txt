cmake_minimum_required(VERSION 3.15)
project(test_cattle C)

find_package(cattle REQUIRED CONFIG)

add_executable(test_cattle test_cattle.c)
target_link_libraries(test_cattle PRIVATE cattle::cattle)
