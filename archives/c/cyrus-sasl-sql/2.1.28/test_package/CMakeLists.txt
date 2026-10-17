cmake_minimum_required(VERSION 3.16)
project(test_cyrus_sasl_sql C)

find_package(cyrus-sasl-sql REQUIRED CONFIG)

add_executable(test_cyrus_sasl_sql test_cyrus_sasl_sql.c)
target_link_libraries(test_cyrus_sasl_sql PRIVATE cyrus-sasl-sql::cyrus-sasl-sql)

enable_testing()
add_test(NAME test_cyrus_sasl_sql COMMAND test_cyrus_sasl_sql)
