cmake_minimum_required(VERSION 3.15)
project(test_cdb C)

find_package(cdb REQUIRED)

add_executable(test_cdb test.c)
target_link_libraries(test_cdb cdb::cdb)

add_executable(test_cdb64 test64.c)
target_link_libraries(test_cdb64 cdb::cdb)

enable_testing()
add_test(NAME test_cdb COMMAND test_cdb)
add_test(NAME test_cdb64 COMMAND test_cdb64)
