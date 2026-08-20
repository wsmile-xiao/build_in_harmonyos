cmake_minimum_required(VERSION 3.15)
project(test_mariadb_connector_c C)

find_package(mariadb-connector-c REQUIRED)

add_executable(test_mariadb test_mariadb.c)
target_link_libraries(test_mariadb mariadb-connector-c::mariadb-connector-c)
