cmake_minimum_required(VERSION 3.15)
project(test_sofa C)

find_package(sofa REQUIRED CONFIG)

add_executable(test_sofa test_sofa.c)
target_link_libraries(test_sofa PRIVATE sofa::sofa)
