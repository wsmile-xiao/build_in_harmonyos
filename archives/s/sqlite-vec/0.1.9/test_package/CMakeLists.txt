cmake_minimum_required(VERSION 3.15)
project(test_sqlite_vec C)

find_package(sqlite-vec REQUIRED)
find_package(sqlite3 REQUIRED)

add_executable(test_sqlite_vec test.c)

target_compile_definitions(test_sqlite_vec PRIVATE SQLITE_CORE)

target_link_libraries(test_sqlite_vec PRIVATE
    sqlite-vec::sqlite-vec
    sqlite3::sqlite3
    m
)
