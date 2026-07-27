cmake_minimum_required(VERSION 3.15)
project(test_sqlite C)

find_package(sqlite REQUIRED)

add_executable(test_sqlite test.c)
target_link_libraries(test_sqlite sqlite::sqlite)

enable_testing()
add_test(NAME sqlite_test COMMAND test_sqlite)
