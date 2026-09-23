cmake_minimum_required(VERSION 3.15)
project(test_adns C)

find_package(adns REQUIRED CONFIG)

add_executable(test_adns test_adns.c)
target_link_libraries(test_adns PRIVATE adns::adns)
