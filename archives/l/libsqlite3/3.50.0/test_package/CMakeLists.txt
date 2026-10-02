cmake_minimum_required(VERSION 3.15)
project(test_sqlite3 C)

find_package(sqlite3 CONFIG REQUIRED)

add_executable(test_sqlite3 test.c)
target_link_libraries(test_sqlite3 PRIVATE sqlite3::sqlite3)

enable_testing()
add_test(NAME test_sqlite3 COMMAND test_sqlite3)
