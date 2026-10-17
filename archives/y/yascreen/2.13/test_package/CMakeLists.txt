cmake_minimum_required(VERSION 3.15)
project(test_yascreen C)

find_package(yascreen CONFIG REQUIRED)

add_executable(test_yascreen test.c)
target_link_libraries(test_yascreen PRIVATE yascreen::yascreen)
