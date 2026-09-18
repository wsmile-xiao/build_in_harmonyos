cmake_minimum_required(VERSION 3.15)
project(test_tdb C)

find_package(tdb REQUIRED)

add_executable(test_tdb test_tdb.c)
target_link_libraries(test_tdb tdb::tdb)
