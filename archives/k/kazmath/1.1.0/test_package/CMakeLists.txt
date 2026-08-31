cmake_minimum_required(VERSION 3.15)
project(test_kazmath C)

find_package(kazmath REQUIRED)
add_executable(test_kazmath test.c)
target_link_libraries(test_kazmath kazmath::kazmath)
enable_testing()
add_test(NAME test_kazmath COMMAND test_kazmath)
