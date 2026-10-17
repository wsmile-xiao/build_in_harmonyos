cmake_minimum_required(VERSION 3.15)
project(test_unixcw C)

find_package(unixcw REQUIRED)

add_executable(test_unixcw test.c)
target_link_libraries(test_unixcw unixcw::unixcw)

enable_testing()
add_test(NAME test_unixcw COMMAND test_unixcw)
