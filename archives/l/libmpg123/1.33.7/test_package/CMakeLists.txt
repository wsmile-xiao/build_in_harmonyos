cmake_minimum_required(VERSION 3.15)
project(test_libmpg123 C)

find_package(libmpg123 REQUIRED)

add_executable(test_libmpg123 test.c)
target_link_libraries(test_libmpg123 libmpg123::libmpg123)

enable_testing()
add_test(NAME libmpg123_api_test COMMAND test_libmpg123)
