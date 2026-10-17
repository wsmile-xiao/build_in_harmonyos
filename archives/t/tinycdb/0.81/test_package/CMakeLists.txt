cmake_minimum_required(VERSION 3.15)
project(test_tinycdb C)

find_package(tinycdb REQUIRED)

add_executable(test_tinycdb test.c)
target_link_libraries(test_tinycdb tinycdb::tinycdb)

enable_testing()
add_test(NAME test_tinycdb COMMAND test_tinycdb)
