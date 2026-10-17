cmake_minimum_required(VERSION 3.15)
project(test_libpoly LANGUAGES C)

find_package(libpoly REQUIRED)

add_executable(test_libpoly test.c)
target_link_libraries(test_libpoly PRIVATE libpoly::libpoly)

enable_testing()
add_test(NAME test_libpoly COMMAND test_libpoly)
