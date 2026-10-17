cmake_minimum_required(VERSION 3.15)
project(test_mapcode C)

find_package(mapcode REQUIRED)

add_executable(test_mapcode test_mapcode.c)
target_link_libraries(test_mapcode mapcode::mapcode)

enable_testing()
add_test(NAME test_mapcode COMMAND test_mapcode)
