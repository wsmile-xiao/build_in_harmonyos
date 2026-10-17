cmake_minimum_required(VERSION 3.15)
project(test_hydrogen C)

find_package(hydrogen REQUIRED)

add_executable(test_hydrogen test_hydrogen.c)
target_link_libraries(test_hydrogen PRIVATE hydrogen::hydrogen)
