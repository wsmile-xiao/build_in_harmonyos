cmake_minimum_required(VERSION 3.15)
project(tinyvdb_test C)

find_package(tinyvdb REQUIRED)

add_executable(test_tinyvdb_ops test_tinyvdb_ops.c)
target_link_libraries(test_tinyvdb_ops PRIVATE tinyvdb::tinyvdb)
set_property(TARGET test_tinyvdb_ops PROPERTY C_STANDARD 11)
