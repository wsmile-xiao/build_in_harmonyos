cmake_minimum_required(VERSION 3.15)
project(db_c_consumer LANGUAGES C)

find_package(db-c CONFIG REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE db-c::db-c)

add_executable(harmony_db_test harmony_tests/harmony_db_test.c)
target_link_libraries(harmony_db_test PRIVATE db-c::db-c)
