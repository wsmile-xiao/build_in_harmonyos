cmake_minimum_required(VERSION 3.15)
project(test_wtmpdb C)

find_package(wtmpdb REQUIRED)
add_executable(test_wtmpdb test.c)
target_link_libraries(test_wtmpdb PRIVATE wtmpdb::wtmpdb)
