cmake_minimum_required(VERSION 3.15)
project(test_libgarmin C)

find_package(libgarmin CONFIG REQUIRED)

add_executable(test_libgarmin test.c)
target_link_libraries(test_libgarmin PRIVATE libgarmin::libgarmin)
