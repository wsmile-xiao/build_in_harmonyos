cmake_minimum_required(VERSION 3.15)
project(test_skiplist C)

find_package(skiplist CONFIG REQUIRED)
add_executable(test_skiplist test.c)
target_link_libraries(test_skiplist PRIVATE skiplist::skiplist)

enable_testing()
add_test(NAME test_skiplist COMMAND test_skiplist)
