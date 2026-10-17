cmake_minimum_required(VERSION 3.15)
project(test_minilua C)

find_package(minilua CONFIG REQUIRED)

add_executable(test_minilua test.c)
target_link_libraries(test_minilua PRIVATE minilua)

enable_testing()
add_test(NAME test_minilua COMMAND test_minilua)
