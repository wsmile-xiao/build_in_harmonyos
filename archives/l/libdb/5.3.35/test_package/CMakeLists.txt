cmake_minimum_required(VERSION 3.15)
project(test_libdb C)

find_package(libdb REQUIRED)

add_executable(test_libdb test_libdb.c)
target_link_libraries(test_libdb libdb::libdb)

enable_testing()
add_test(NAME test_libdb COMMAND test_libdb)
