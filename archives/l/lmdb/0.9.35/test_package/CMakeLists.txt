cmake_minimum_required(VERSION 3.15)
project(test_lmdb C)

find_package(lmdb REQUIRED)

add_executable(test_lmdb test.c)
target_link_libraries(test_lmdb lmdb::lmdb)

enable_testing()
add_test(NAME test_lmdb COMMAND test_lmdb)