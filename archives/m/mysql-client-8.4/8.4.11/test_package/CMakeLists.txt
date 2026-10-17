cmake_minimum_required(VERSION 3.15)
project(test_mysql_client C)

find_package(mysqlclient REQUIRED)

add_executable(test_mysql_client test.c)
target_link_libraries(test_mysql_client PRIVATE mysqlclient::mysqlclient)
