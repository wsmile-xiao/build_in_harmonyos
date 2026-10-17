cmake_minimum_required(VERSION 3.15)
project(test_uthash C)

find_package(uthash REQUIRED)

add_executable(test_uthash test.c)
target_link_libraries(test_uthash PRIVATE uthash::uthash)

enable_testing()
add_test(NAME uthash_test COMMAND test_uthash)
